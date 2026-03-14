import os
import json
import re

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from openai import OpenAI

# Load values from .env file
load_dotenv()

# Read Azure OpenAI settings from environment variables
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")

# Create FastAPI app
app = FastAPI()

# Create Azure OpenAI client
client = OpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    base_url=f"{AZURE_OPENAI_ENDPOINT}/openai/v1/"
)

# Allowed values for validation
ALLOWED_REGIONS = [
    "westeurope",
    "northeurope",
    "uksouth",
    "ukwest",
    "eastus",
    "eastus2"
]

ALLOWED_RESOURCE_TYPES = [
    "storage_account"
]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/translate")
def translate(request_body: dict):
    """
    Expected input:
    {
        "request": "Create a storage account in westeurope in rg-app-prod with name stappfiles001"
    }
    """

    # Check that the JSON body contains a "request" field
    if "request" not in request_body:
        raise HTTPException(status_code=400, detail="Missing 'request' field")

    user_request = request_body["request"]

    # Check that request is actually text
    if not isinstance(user_request, str):
        raise HTTPException(status_code=400, detail="'request' must be a string")

    # Step 1: send user's text to Azure OpenAI
    extracted_data = extract_intent_from_ai(user_request)

    # Step 2: validate the AI output
    errors = validate_extracted_data(extracted_data)

    # Step 3: only generate YAML if validation passed
    yaml_output = None
    is_valid = len(errors) == 0

    if is_valid:
        yaml_output = generate_yaml(extracted_data)

    # Step 4: return final response
    return {
        "intent": extracted_data,
        "validated": is_valid,
        "errors": errors,
        "yaml": yaml_output
    }


def extract_intent_from_ai(user_request):
    """
    Send the user's plain-English request to Azure OpenAI
    and ask it to return strict JSON.
    """

    system_prompt = """
You are an infrastructure request parser.

Return JSON only.

Required JSON format:
{
  "resource_type": "string",
  "region": "string",
  "resource_group": "string",
  "resource_name": "string",
  "sku": "string or null",
  "environment": "string or null"
}

Rules:
- If the user asks for a storage account, set "resource_type" to "storage_account".
- Do not return markdown.
- Do not return explanation text.
- Return JSON only.
"""

    response = client.responses.create(
        model=AZURE_OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request}
        ]
    )

    # This is the text returned by the model
    ai_text = response.output_text

    # Convert JSON text into Python dictionary
    data = json.loads(ai_text)

    return data


def validate_extracted_data(data):
    """
    Check whether the AI output follows our rules.
    Return a list of errors.
    """

    errors = []

    # Normalize region: "West Europe" -> "westeurope"
    if "region" in data and data["region"]:
        data["region"] = data["region"].lower().replace(" ", "")

    # Required fields
    required_fields = [
        "resource_type",
        "region",
        "resource_group",
        "resource_name"
    ]

    for field_name in required_fields:
        if field_name not in data or not data[field_name]:
            errors.append(f"Missing required field: {field_name}")

    # If required fields are missing, stop here
    if len(errors) > 0:
        return errors

    # Check resource type
    if data["resource_type"] not in ALLOWED_RESOURCE_TYPES:
        errors.append(f"Unsupported resource type: {data['resource_type']}")

    # Check region
    if data["region"] not in ALLOWED_REGIONS:
        errors.append(f"Unsupported region: {data['region']}")

    # Check resource group rule
    if not data["resource_group"].startswith("rg-"):
        errors.append("resource_group must start with 'rg-'")

    # Check storage account name
    if data["resource_type"] == "storage_account":
        storage_account_name = data["resource_name"]

        # Azure storage account name rule:
        # 3-24 chars, lowercase letters and numbers only
        if not re.fullmatch(r"[a-z0-9]{3,24}", storage_account_name):
            errors.append(
                "Invalid storage account name. Use 3-24 lowercase letters and numbers only."
            )

    return errors


def generate_yaml(data):
    """
    Build YAML text from validated data.
    """

    sku = data.get("sku")

    # If AI did not return sku, use default
    if not sku:
        sku = "Standard_LRS"

    yaml_text = f"""apiVersion: example.platform.io/v1alpha1
kind: StorageAccountClaim
metadata:
  name: {data["resource_name"]}
spec:
  resourceGroup: {data["resource_group"]}
  region: {data["region"]}
  name: {data["resource_name"]}
  sku: {sku}
"""

    return yaml_text
