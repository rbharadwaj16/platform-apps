from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/translate")
def translate(request_body: dict):
    if "request" not in request_body:
        raise HTTPException (status_code=400, detail="Missing 'request' field")
    
    user_request = request_body["request"]

    return {
        "user_request": user_request
    }