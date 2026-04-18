from typing import List
import os

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

app = FastAPI(title="TarkShashtra Core API", version="1.0.0")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[os.getenv("RATE_LIMIT", "120/minute")],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ML_API_URL = os.getenv("ML_API_URL", "http://localhost:8001/predict")
ML_API_TIMEOUT = float(os.getenv("ML_API_TIMEOUT", "10"))


class PredictionRequest(BaseModel):
    assignment: float = Field(..., ge=0, le=100)
    attendance: float = Field(..., ge=0, le=100)
    lms: float = Field(..., ge=0, le=100)
    marks: float = Field(..., ge=0, le=100)
    risk_score: float = Field(..., ge=0)


async def call_ml_api(payload: PredictionRequest) -> dict:
    payload_data = (
        payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    )
    async with httpx.AsyncClient(timeout=ML_API_TIMEOUT) as client:
        resp = await client.post(ML_API_URL, json=payload_data)
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


def intervention_rules(risk_label: str) -> List[str]:
    label = (risk_label or "").strip().lower()
    if label == "high":
        return [
            "Immediate advisor outreach",
            "Weekly progress check-ins",
            "Targeted academic support sessions",
        ]
    if label == "medium":
        return [
            "Bi-weekly progress review",
            "Study plan and attendance nudges",
            "Optional tutoring resources",
        ]
    if label == "low":
        return [
            "Maintain current progress",
            "Monthly performance monitoring",
        ]
    return ["Review manually - label not recognized"]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict")
@limiter.limit(os.getenv("PREDICT_RATE_LIMIT", "60/minute"))
async def predict(request: Request, payload: PredictionRequest) -> dict:
    return await call_ml_api(payload)


@app.post("/intervention")
@limiter.limit(os.getenv("INTERVENTION_RATE_LIMIT", "30/minute"))
async def intervention(request: Request, payload: PredictionRequest) -> dict:
    result = await call_ml_api(payload)
    label = str(result.get("risk_label", ""))
    return {
        "risk_label": label,
        "recommendations": intervention_rules(label),
        "model": result,
    }
