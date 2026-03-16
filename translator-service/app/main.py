from fastapi import FastAPI, HTTPException

app = FastAPI()

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
