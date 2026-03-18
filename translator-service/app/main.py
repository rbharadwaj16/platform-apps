from fastapi import FastAPI, HTTPException

app = FastAPI()

ALLOWED_REGIONS = ["westeurope", "northeurope", "uksouth", "eastus"]
ALLOWED_RESOURCE_TYPES = ["storage_account"]


@app.get("/health")
def health():
    return {"status": "ok"}


def extract_intent_from_ai(user_request):
    return {
        "resource_type": "storage_account",
        "parameters": {
            "storageAccountName": "stappfiles001",
            "resourceGroupName": "myapp-rg",
            "location": "eastus",
            "sku": "Standard_LRS"
        }
    }


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


def build_translation_response(extracted_data):
    parameters = extracted_data["parameters"]

    missing_fields = []

    required_fields = ["storageAccountName", "resourceGroupName", "location"]

    for field_name in required_fields:
        if field_name not in parameters or not parameters[field_name]:
            missing_fields.append(field_name)

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