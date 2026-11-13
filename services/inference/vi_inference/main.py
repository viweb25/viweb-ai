from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="VI WebSync Inference", version="0.1.0")


@app.get("/health/live")
def live():
    return {"status": "ok", "service": "inference", "loaded_packages": 0}


@app.post("/v1/predict", status_code=503)
def predict():
    """No model is shipped with the skeleton. Never fabricate a successful inspection."""
    return JSONResponse(
        status_code=503,
        content={
            "error": {"code": "model_not_loaded", "message": "No approved function package loaded"}
        },
    )
