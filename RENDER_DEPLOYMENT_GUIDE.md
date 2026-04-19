# Render Deployment Guide (Vercel Integration)

This guide explains how to deploy the monorepo to Render and integrate it with a Vercel-hosted frontend.

## 1) Final goal

Your frontend or backend team hosts the main website on Vercel. The ML API runs as a persistent Python service, and the Core API acts as the gateway that Vercel calls over HTTPS.

Recommended architecture:

- Website and Node layer: Vercel
- Core API (FastAPI gateway): Render (recommended) or Railway
- ML inference API (FastAPI + model files): Render (recommended) or Railway
- Data storage: managed by your full-stack team

Why this split:

- FastAPI with heavy ML libraries is not ideal on Vercel serverless for stable low-latency inference
- Render or Railway provides a long-running Python web process better suited for model serving
- Core API can apply business logic and guardrails without exposing the ML service directly

## 2) API endpoints (current)

Core API (recommended for frontend use):

- GET /health
- POST /predict
- POST /predict_batch
- POST /intervention
- POST /interventions
- GET /interventions
- POST /performance
- GET /performance
- POST /alerts/high-risk
- GET /dashboard/at_risk

ML API (internal or direct inference use):

- GET /health
- POST /predict
- POST /predict_batch

Notes:

- Vercel should call the Core API for end-to-end workflows (interventions, alerts, dashboard).
- The Core API calls the ML API internally for inference.

## 3) Files you must have before deploy

Ensure these exist for the ML API:

- services/ml_api/app/main.py
- services/ml_api/app/model.py
- services/ml_api/requirements.txt
- services/ml_api/models/model.pkl
- services/ml_api/models/model_regression.pkl
- services/ml_api/models/label_encoder.pkl
- services/ml_api/models/model_metadata.json

Generate artifacts locally:

```powershell
pip install -r training/requirements.txt
python training/train.py
```

## 4) Local validation before deployment

Start ML API:

```powershell
.venv\Scripts\activate
pip install -r services/ml_api/requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --app-dir services/ml_api
```

Start Core API:

```powershell
.venv\Scripts\activate
pip install -r services/core_api/requirements.txt
set ML_API_BASE_URL=http://localhost:8001
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir services/core_api
```

Test locally:

- http://127.0.0.1:8001/health
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

Confirm:

- API starts without model loading errors
- /predict works with a sample student payload

## 4.1) Local frontend integration (Vercel app on localhost)

If your Vercel app is still in local development (for example Next.js on localhost), set the base URL in your frontend:

```bash
# .env.local (frontend)
FASTAPI_BASE_URL=http://127.0.0.1:8000
# or, if you call from the browser
NEXT_PUBLIC_FASTAPI_BASE_URL=http://127.0.0.1:8000
```

If the frontend runs on a different laptop, use a LAN URL:

- http://YOUR_LOCAL_IP:8000

If LAN access fails, allow inbound firewall for 8000:

```powershell
New-NetFirewallRule -DisplayName "FastAPI 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

## 5) Deploy to Render (free tier)

Deploy them as two separate Render Web Services (that is the normal setup on Render Free). Each service gets its own URL.

Free tier behavior you should expect:

- Each free service can sleep when idle, so the first request is slower.
- If core_api calls ml_api and ml_api is asleep, the first request may take longer (cold start). Consider retries/timeouts.

### Option A: Blueprint with render.yaml (recommended)

1) Log in to Render.
2) New + -> Blueprint.
3) Connect your GitHub repository and select this repo.
4) Render detects render.yaml and shows two services.
5) Choose the **Free** instance type for both services.
6) Click Apply to create the services.

### Option B: Manual setup (two Web Services)

#### 1) Create the ml_api service (Web Service #1)

Render Dashboard -> New + -> Web Service

Select repo: Yashesh1195/TS-12-Early-Academic-Risk-Detection-Student-Intervention-Platform-Model-Training

Configure:

- Name: ml-api (any name)
- Instance Type: Free
- Root Directory: services/ml_api

Choose one deployment style:

A) Docker (if Dockerfile works)

- Runtime: Docker
- Render auto-detects the Dockerfile in the root directory you set

B) Python runtime

- Runtime: Python
- Build Command: pip install -r requirements.txt
- Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT

Click Create Web Service. After deploy, note the URL:

- https://ml-api-xxxxx.onrender.com (example)

#### 2) Create the core_api service (Web Service #2)

Repeat the same process:

Render Dashboard -> New + -> Web Service

Same GitHub repo

Configure:

- Name: core-api
- Instance Type: Free
- Root Directory: services/core_api
- Runtime: Docker (if it has a Dockerfile) OR Python runtime

If Python runtime:

- Build Command: pip install -r requirements.txt
- Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT

If core_api's file is different, adjust the import path accordingly.

Click Create Web Service. Note the URL:

- https://core-api-xxxxx.onrender.com (example)

### 3) Make core_api call ml_api (service-to-service)

Since they have different URLs, configure core_api with an env var pointing to ml_api.

Render -> open core-api service -> Environment

Add:

- ML_API_BASE_URL = https://ml-api-xxxxx.onrender.com

The core_api code calls:

- ${ML_API_BASE_URL}/predict
- ${ML_API_BASE_URL}/predict_batch

If you already use ML_API_URL in your env, you can set that directly instead.

### 4) Handle CORS (for browser clients)

If your frontend calls these APIs from a browser, enable CORS and allow your frontend origin (or * for testing).

### 5) Set environment variables

ML API:

- MODEL_PATH=models/model.pkl
- REGRESSION_MODEL_PATH=models/model_regression.pkl
- LABEL_ENCODER_PATH=models/label_encoder.pkl
- MODEL_METADATA_PATH=models/model_metadata.json

Core API:

- ML_API_BASE_URL=https://<your-ml-api>.onrender.com
- ML_API_FALLBACK_URL=http://localhost:8001 (optional local fallback)
- ML_API_TIMEOUT=10
- ALERT_SCORE_THRESHOLD=70

## 6) Deploy and verify

After Render finishes deploying:

- ML API health: https://<your-ml-api>.onrender.com/health
- Core API health: https://<your-core-api>.onrender.com/health
- Core API docs: https://<your-core-api>.onrender.com/docs

## 7) Test endpoints

Predict:

- curl -X POST https://<your-core-api>.onrender.com/predict -H "Content-Type: application/json" -d "{\"assignment\":65,\"attendance\":72,\"lms\":55,\"marks\":68}"

Intervention:

- curl -X POST https://<your-core-api>.onrender.com/intervention -H "Content-Type: application/json" -d "{\"assignment\":65,\"attendance\":72,\"lms\":55,\"marks\":68}"

Batch predict:

- curl -X POST https://<your-core-api>.onrender.com/predict_batch -H "Content-Type: application/json" -d "{\"items\":[{\"student_id\":\"S-001\",\"class_id\":\"CS-A\",\"subject\":\"Math\",\"assignment\":40,\"attendance\":45,\"lms\":30,\"marks\":42},{\"student_id\":\"S-002\",\"class_id\":\"CS-A\",\"subject\":\"Math\",\"assignment\":82,\"attendance\":88,\"lms\":75,\"marks\":85}]}"

## 8) What to share with your Vercel team

Share only these items:

- Core API base URL, for example: https://<your-core-api>.onrender.com
- Endpoint list and request schema
- Expected response fields for each endpoint

Required frontend environment variable on Vercel:

- FASTAPI_BASE_URL=https://<your-core-api>.onrender.com

## 9) Vercel integration pattern (recommended)

Use server-side calls from Next.js API routes or server actions instead of direct browser calls when possible.

Example server-side fetch pattern:

```ts
const apiBase = process.env.FASTAPI_BASE_URL;

const response = await fetch(`${apiBase}/predict`, {
	method: "POST",
	headers: { "Content-Type": "application/json" },
	body: JSON.stringify({
		student_id: "STU001",
		attendance: 62,
		marks: 48,
		assignment: 55,
		lms: 44,
	}),
});

const result = await response.json();
```

Benefits:

- Keeps API base URL and operational logic centralized
- Easier auth/rate-limit wrapping later
- Better control over retries and error handling

## 10) CORS rules (only if browser calls the API directly)

If the browser calls the Core API directly, add CORS middleware in services/core_api/app/main.py and allow only your Vercel domains.

Example snippet:

```python
from fastapi.middleware.cors import CORSMiddleware

allowed = ["https://your-vercel-app.vercel.app"]
app.add_middleware(
		CORSMiddleware,
		allow_origins=allowed,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
)
```

## 11) Production checklist

Before handing off to the website team:

- API URL is HTTPS and publicly reachable
- /health returns healthy
- /docs is visible
- /predict returns expected fields
- Model files are present in deployment
- Response time is acceptable for expected traffic

## 12) Updating models later (without breaking the team)

When you retrain:

1. Replace files in services/ml_api/models
2. Commit and push
3. Trigger redeploy on Render
4. Re-test /health and /predict
5. Inform frontend team only if response schema changed

Best practice:

- Keep response schema stable
- Add version info later if needed

## 13) Quick local sharing (same Wi-Fi only)

If a teammate is on the same LAN:

1. Run:
	 - uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir services/core_api
2. Share:
	 - http://YOUR_LOCAL_IP:8000/docs
3. Allow firewall inbound on port 8000 if needed

This is only for temporary local testing, not production.

## 14) If you need a public temporary demo link

Use one of these:

- ngrok
- cloudflared tunnel

This is useful for hackathon demos before full deployment.

## 15) Troubleshooting

- If you see {"detail":"Not Found"} at /, use /health or /docs.
- If ML API returns 500, confirm the model files exist on the server.
- If core_api cannot reach ML API, confirm ML_API_BASE_URL or ML_API_URL is correct.
- If deployments fail, check the Render logs for build errors and missing packages.
