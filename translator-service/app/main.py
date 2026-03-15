from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/translate")
def translate(request_body: dict):
    return {"message_received": request_body}