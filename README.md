# Early Academic Risk Detection & Student Intervention Platform (Monorepo)

This repo separates ML inference from the core API so you can deploy the ML service independently and reduce rate-limit pressure on the main app.

## Structure
- services/ml_api: FastAPI service for model inference
- services/core_api: FastAPI gateway + intervention endpoint (calls ml_api)
- training: training pipeline that produces model artifacts
- datasets: dataset files used for training
- Early_Academic_Risk_Detection_Student_Intervention_Platform.ipynb: exploration notebook

## Prerequisites
- Python 3.10+ installed
- pip available
- (Optional) Git and Docker

## Step-by-step setup (Windows cmd)

0) Open a terminal in this folder
- Use Windows cmd and set your working directory to this repo root.
- You should see these folders: datasets, services, training.

1) Create and activate a virtual environment (recommended)
- python -m venv .venv
- .venv\Scripts\activate
- Confirm: where python

2) Install notebook requirements (optional, for the .ipynb)
- pip install -r requirements.txt

3) Train and export the model
- pip install -r training/requirements.txt
- python training/train.py

This writes model artifacts to:
- services/ml_api/models/model.pkl
- services/ml_api/models/label_encoder.pkl

If these files are missing after training:
- Confirm datasets/TS-PS12.csv exists
- Re-run: python training/train.py

4) Run the ML API (in a new terminal)
- Open a new cmd window in the same repo root
- Activate the same venv: .venv\Scripts\activate
- pip install -r services/ml_api/requirements.txt
- uvicorn app.main:app --reload --port 8001 --app-dir services/ml_api

Verify ML API is running:
- Health: http://localhost:8001/health
- Docs: http://localhost:8001/docs
- Note: http://localhost:8001/ shows {"detail":"Not Found"} because no root route is defined.

5) Run the Core API (in a new terminal)
- Open another cmd window in the repo root
- Activate the same venv: .venv\Scripts\activate
- pip install -r services/core_api/requirements.txt
- set ML_API_URL=http://localhost:8001/predict
- uvicorn app.main:app --reload --port 8000 --app-dir services/core_api

Verify Core API is running:
- Health: http://localhost:8000/health
- Docs: http://localhost:8000/docs

6) Test the Core API (predict)
- Make sure both services are running:
	- ML API: http://localhost:8001/health should return {"status":"ok"}
	- Core API: http://localhost:8000/health should return {"status":"ok"}
- Send a prediction request (Windows cmd):
	- curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "{\"assignment\":65,\"attendance\":72,\"lms\":55,\"marks\":68,\"risk_score\":33}"
- Expected response shape:
	- {"risk_label":"Medium","risk_label_id":1,"probabilities":{...}}
- If you get 500, confirm model files exist in services/ml_api/models

7) Try the intervention endpoint
- This endpoint calls the ML API and adds recommended actions.
- Run in Windows cmd:
	- curl -X POST http://localhost:8000/intervention -H "Content-Type: application/json" -d "{\"assignment\":65,\"attendance\":72,\"lms\":55,\"marks\":68,\"risk_score\":33}"
- Expected response shape:
	- {"risk_label":"Medium","recommendations":["..."],"model":{...}}
- If you see a timeout, ensure ML_API_URL is set correctly and ML API is running

## Notebook usage
- Open Early_Academic_Risk_Detection_Student_Intervention_Platform.ipynb
- Run cells top-to-bottom to reproduce dataset analysis, model comparison, and export
- The export cell also writes best_model.pkl and label_encoder.pkl in the notebook folder

If you want the notebook to populate the ML API models folder:
- Copy best_model.pkl to services/ml_api/models/model.pkl
- Copy label_encoder.pkl to services/ml_api/models/label_encoder.pkl

## Environment variables

ML API (.env.example in services/ml_api):
- MODEL_PATH=models/model.pkl
- LABEL_ENCODER_PATH=models/label_encoder.pkl
- RATE_LIMIT=60/minute
- PREDICT_RATE_LIMIT=30/minute

Core API (.env.example in services/core_api):
- ML_API_URL=http://localhost:8001/predict
- ML_API_TIMEOUT=10
- RATE_LIMIT=120/minute
- PREDICT_RATE_LIMIT=60/minute
- INTERVENTION_RATE_LIMIT=30/minute

## Deployment to Render

This repo includes render.yaml with two services (ml_api and core_api). Deploy them as separate services so the ML service can scale or rate-limit independently.

Recommended steps:
1) Push this repo to GitHub
2) In Render, create a new Blueprint from render.yaml
3) After ML API deploys, update ML_API_URL in core_api to the ML API URL
4) Redeploy core_api

## Docker (optional)

ML API:
- cd services\ml_api
- docker build -t tark-ml-api .
- docker run -p 8001:8000 tark-ml-api

Core API:
- cd services\core_api
- docker build -t tark-core-api .
- docker run -p 8000:8000 -e ML_API_URL=http://host.docker.internal:8001/predict tark-core-api

## Rate-limit mitigation
- ML API and Core API both include IP-based rate limiting.
- You can tune limits via env vars in each service's .env.example.
- If you integrate a third-party LLM later, keep that call in core_api and limit it separately.

## Troubleshooting
- If ML API returns 500, verify model files exist in services/ml_api/models
- If core_api cannot reach ML API, confirm ML_API_URL and that ML API is running
- If you see import errors, re-check the requirements for that service
- If you see {"detail":"Not Found"} at http://localhost:8001/, use /health or /docs
- If prediction fails, confirm all 5 features are sent in the JSON body
