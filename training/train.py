from pathlib import Path
import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

FEATURE_COLUMNS = ["assignment", "attendance", "lms", "marks", "risk_score"]

DATASET_PATH = Path(os.getenv("DATASET_PATH", "datasets/TS-PS12.csv"))
MODEL_DIR = Path(os.getenv("MODEL_DIR", "services/ml_api/models"))


def select_model():
    try:
        from xgboost import XGBClassifier

        return XGBClassifier(
            objective="multi:softprob",
            n_estimators=300,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            n_jobs=-1,
            eval_metric="mlogloss",
            tree_method="hist",
        )
    except Exception as exc:
        print(f"XGBoost not available, using RandomForest: {exc}")
        return RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced",
        )


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    if "student_id" in df.columns:
        df = df.drop(columns=["student_id"])

    le = LabelEncoder()
    y = le.fit_transform(df["risk_label"])
    X = df[FEATURE_COLUMNS]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y,
    )

    model = select_model()
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    print("Accuracy:", round(accuracy_score(y_test, preds), 4))
    print("Balanced accuracy:", round(balanced_accuracy_score(y_test, preds), 4))
    print("F1 macro:", round(f1_score(y_test, preds, average="macro"), 4))
    print("F1 weighted:", round(f1_score(y_test, preds, average="weighted"), 4))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_DIR / "model.pkl")
    joblib.dump(le, MODEL_DIR / "label_encoder.pkl")
    print(f"Saved model artifacts to {MODEL_DIR}")


if __name__ == "__main__":
    main()
