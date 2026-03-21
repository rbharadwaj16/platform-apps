import os
import json

from fastapi import FastAPI, HTTPException
from openai import OpenAI

app = FastAPI()

ALLOWED_REGIONS = ["westeurope", "northeurope", "uksouth", "eastus"]
ALLOWED_RESOURCE_TYPES = ["storage_account"]

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")

if not AZURE_OPENAI_API_KEY:
    raise RuntimeError("AZURE_OPENAI_API_KEY is not set")

if not AZURE_OPENAI_ENDPOINT:
    raise RuntimeError("AZURE_OPENAI_ENDPOINT is not set")

if not AZURE_OPENAI_MODEL:
    raise RuntimeError("AZURE_OPENAI_MODEL is not set")

client = OpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    base_url=f"{AZURE_OPENAI_ENDPOINT}/openai/v1/"
)


@app.get("/health")
def health():
    return {"status": "ok"}


def extract_intent_from_ai(user_request):
    prompt_text = """
You are an infrastructure request parser.

Return JSON only.

Extract the user's request into this exact JSON structure:
{
  "resource_type": "storage_account",
  "parameters": {
    "storageAccountName": "string or null",
    "resourceGroupName": "string or null",
    "location": "string or null",
    "sku": "string or null"
  }
}

Rules:
- Return JSON only
- Do not return markdown
- Do not return explanation text
- If a value is missing, use null
- If the request is for a storage account, set resource_type to "storage_account"
- Map common phrasing where possible, but do not invent values
"""

    response = client.responses.create(
        model=AZURE_OPENAI_MODEL,
        input=[
            {"role": "developer", "content": prompt_text},
            {"role": "user", "content": user_request}
        ]
    )

    ai_text = response.output_text

    try:
        extracted_data = json.loads(ai_text)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Model did not return valid JSON"
        )

    return extracted_data


def validate_extracted_data(extracted_data):
    errors = []

    if "resource_type" not in extracted_data or not extracted_data["resource_type"]:
        errors.append("Missing resource_type")

    if "parameters" not in extracted_data or not extracted_data["parameters"]:
        errors.append("Missing parameters")
        return errors

    if extracted_data["resource_type"] not in ALLOWED_RESOURCE_TYPES:
        errors.append("Unsupported resource type")

    parameters = extracted_data["parameters"]

    required_fields = ["storageAccountName", "resourceGroupName", "location"]

    for field_name in required_fields:
        if field_name not in parameters or not parameters[field_name]:
            errors.append(f"Missing {field_name}")

    if len(errors) > 0:
        return errors

    parameters["location"] = parameters["location"].lower().replace(" ", "")

    if parameters["location"] not in ALLOWED_REGIONS:
        errors.append("Unsupported region")

    return errors


def normalize_sku(sku_value):
    if not sku_value:
        return "Standard_LRS"

    sku_value = sku_value.lower().strip()

    if sku_value == "standard_lrs":
        return "Standard_LRS"

    if sku_value == "standard_grs":
        return "Standard_GRS"

    if sku_value == "premium_lrs":
        return "Premium_LRS"

    return sku_value


def build_translation_response(extracted_data):
    parameters = extracted_data["parameters"]

    missing_fields = []

    required_fields = ["storageAccountName", "resourceGroupName", "location"]

    for field_name in required_fields:
        if field_name not in parameters or not parameters[field_name]:
            missing_fields.append(field_name)

    parameters["location"] = parameters["location"].lower().replace(" ", "")
    parameters["sku"] = normalize_sku(parameters.get("sku"))

    return {
        "resource_type": extracted_data["resource_type"],
        "parameters": parameters,
        "missing_fields": missing_fields,
        "needs_clarification": len(missing_fields) > 0
    }


@app.post("/translate")
def translate(request_body: dict):
    if "request" not in request_body:
        raise HTTPException(status_code=400, detail="Missing 'request' in body")

    user_request = request_body["request"]

    if not isinstance(user_request, str):
        raise HTTPException(status_code=400, detail="'request' must be a string")

    extracted_data = extract_intent_from_ai(user_request)

    errors = validate_extracted_data(extracted_data)

    translation_response = None

    if len(errors) == 0:
        translation_response = build_translation_response(extracted_data)

    return {
        "user_request": user_request,
        "extracted_data": extracted_data,
        "errors": errors,
        "translation": translation_response
    }