from fastapi import FastAPI, HTTPException

app = FastAPI()

ALLOWED_REGIONS = ["westeurope", "northeurope", "uksouth"]
ALLOWED_RESOURCE_TYPES = ["storage_account"]

@app.get("/health")
def health():
    return {"status": "ok"}

def extract_intent_from_ai(user_request):
    return {
        "resource_type": "storage_account",
        "region": "westeurope",
        "resource_group": "rg-app-prod",
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

    return {
        "user_request": user_request,
        "extracted_data": extracted_data
    }

def validate_extracted_data(extracted_data):
    errors = []

    required_fields = ["resource_type", "region", "resource_group", "resource_name"]

    for field_name in required_fields:
        if field_name not in extracted_data or not extracted_data(field_name):
            errors.append(f"Missing {field_name}")

    if len(errors) > 0:
        return errors
    