from typing import List, Optional
import os

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .model import FEATURE_COLUMNS, model_store

app = FastAPI(title="TarkShashtra ML API", version="1.0.0")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[os.getenv("RATE_LIMIT", "60/minute")],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class PredictionRequest(BaseModel):
    assignment: float = Field(..., ge=0, le=100)
    attendance: float = Field(..., ge=0, le=100)
    lms: float = Field(..., ge=0, le=100)
    marks: float = Field(..., ge=0, le=100)
    risk_score: float = Field(..., ge=0)


class BatchPredictionRequest(BaseModel):
    items: List[PredictionRequest]


class PredictionResponse(BaseModel):
    risk_label: str
    risk_label_id: int
    probabilities: Optional[dict]


class BatchPredictionResponse(BaseModel):
    items: List[PredictionResponse]


def to_feature_vector(payload: PredictionRequest) -> list[float]:
    feature_map = {
        "assignment": payload.assignment,
        "attendance": payload.attendance,
        "lms": payload.lms,
        "marks": payload.marks,
        "risk_score": payload.risk_score,
    }
    return [feature_map[name] for name in FEATURE_COLUMNS]


@app.on_event("startup")
def load_model() -> None:
    model_store.load()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": model_store.model is not None}


@app.post("/predict", response_model=PredictionResponse)
@limiter.limit(os.getenv("PREDICT_RATE_LIMIT", "30/minute"))
def predict(request: Request, payload: PredictionRequest) -> PredictionResponse:
    try:
        label, label_id, probs = model_store.predict(to_feature_vector(payload))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return PredictionResponse(
        risk_label=str(label),
        risk_label_id=int(label_id),
        probabilities=probs,
    )


@app.post("/predict_batch", response_model=BatchPredictionResponse)
@limiter.limit(os.getenv("PREDICT_RATE_LIMIT", "30/minute"))
def predict_batch(
    request: Request, payload: BatchPredictionRequest
) -> BatchPredictionResponse:
    items: List[PredictionResponse] = []
    for item in payload.items:
        label, label_id, probs = model_store.predict(to_feature_vector(item))
        items.append(
            PredictionResponse(
                risk_label=str(label),
                risk_label_id=int(label_id),
                probabilities=probs,
            )
        )
    return BatchPredictionResponse(items=items)
