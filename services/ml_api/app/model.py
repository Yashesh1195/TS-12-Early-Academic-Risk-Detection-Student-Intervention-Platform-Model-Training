from pathlib import Path
import os

import joblib
import numpy as np

FEATURE_COLUMNS = ["assignment", "attendance", "lms", "marks", "risk_score"]


class ModelStore:
    def __init__(self, model_path: Path, encoder_path: Path) -> None:
        self.model_path = Path(model_path)
        self.encoder_path = Path(encoder_path)
        self.model = None
        self.encoder = None

    def load(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {self.model_path}. Run training/train.py first."
            )
        self.model = joblib.load(self.model_path)
        if self.encoder_path.exists():
            self.encoder = joblib.load(self.encoder_path)

    def predict(self, features: list[float]) -> tuple[str, int, dict | None]:
        if self.model is None:
            self.load()
        arr = np.array([features], dtype=float)
        pred_id = int(self.model.predict(arr)[0])
        label = str(pred_id)
        if self.encoder is not None:
            try:
                label = self.encoder.inverse_transform([pred_id])[0]
            except Exception:
                label = str(pred_id)

        probs = None
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(arr)[0]
            if self.encoder is not None and hasattr(self.encoder, "classes_"):
                probs = {
                    str(cls): float(p)
                    for cls, p in zip(self.encoder.classes_, proba)
                }
            else:
                probs = {str(i): float(p) for i, p in enumerate(proba)}
        return label, pred_id, probs


def get_model_paths() -> tuple[Path, Path]:
    base = Path(__file__).resolve().parent.parent
    model_path = Path(os.getenv("MODEL_PATH", base / "models" / "model.pkl"))
    encoder_path = Path(
        os.getenv("LABEL_ENCODER_PATH", base / "models" / "label_encoder.pkl")
    )
    return model_path, encoder_path


model_path, encoder_path = get_model_paths()
model_store = ModelStore(model_path, encoder_path)
