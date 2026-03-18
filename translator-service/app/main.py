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
        "region": "westeurope",
        "resource_group": "app-prod",
        "resource_name": "stappfiles001",
        "sku": "Standard_LRS",
        "environment": "prod"
    }


@app.post("/translate")
def translate(request_body: dict):
    if "request" not in request_body:
        raise HTTPException(status_code=400, detail="Missing 'request' in body")
    
    user_request = request_body["request"]

    extracted_data = extract_intent_from_ai(user_request)

    errors = validate_extracted_data(extracted_data)

    yaml_output = None

    if len(errors) == 0:
        yaml_output = generate_yaml(extracted_data)

    return {
        "user_request": user_request,
        "extracted_data": extracted_data,
        "errors": errors,
        "yaml": yaml_output
    }

def validate_extracted_data(extracted_data):
    errors = []

    required_fields = ["resource_type", "region", "resource_group", "resource_name"]

    for field_name in required_fields:
        if field_name not in extracted_data or not extracted_data[field_name]:
            errors.append(f"Missing {field_name}")

    if len(errors) > 0:
        return errors
    
    extracted_data["region"] = extracted_data["region"].lower().replace(" ", "")

    if extracted_data["resource_type"] not in ALLOWED_RESOURCE_TYPES:
        errors.append("Unsupported resource type")

    if extracted_data["region"] not in ALLOWED_REGIONS:
        errors.append("Unsupported region")

    if not extracted_data["resource_group"].startswith("rg-"):
        errors.append("resource group must start with rg-")

    return errors
    

def generate_yaml(extracted_data):
    yaml_text = f"""apiVersion: storage.aceplatform.org/v1alpha1
kind: XStorageAccount
metadata:
  name: {extracted_data["resource_name"]}
  namespace: default
  annotations:
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true
spec:
  parameters:
    storageAccountName: {extracted_data["resource_name"]}
    resourceGroupName: {extracted_data["resource_group"]}
    location: {extracted_data["region"]}
    sku: {extracted_data["sku"]}
"""
    return yaml_text
    