# TS-12 FastAPI Deployment Guide for Vercel Team Integration

## 1) Final Goal

Your frontend or backend team will host the main website on Vercel.
Your ML API should run separately as a persistent Python service, and Vercel will call it over HTTPS.

Recommended architecture:

- Website and Node layer: Vercel
- ML inference API (FastAPI + model files): Render (recommended) or Railway
- Data storage: managed by your full-stack team

Why this split:

- FastAPI with heavy ML libraries is not ideal on Vercel serverless for stable low-latency inference
- Render or Railway gives a long-running Python web process better suited for model serving

## 2) API Endpoints (Current)

The API now exposes these endpoint groups:

- GET /health
- POST /predict
- POST /dashboard/class
- POST /intervention/compare
- POST /alerts/screen
- GET /model/info

Note:

- POST /predict/batch has been removed from the API.

## 3) Files You Must Have Before Deploy

Ensure these exist in the repo root:

- main.py
- requirements.txt
- runtime.txt
- saved_models/risk_classifier.pkl
- saved_models/risk_regressor.pkl
- saved_models/label_encoder.pkl
- saved_models/shap_explainer.pkl
- saved_models/config.json

Optional but useful:

- saved_models/feature_engineer.pkl (not required at runtime now)

## 4) Local Validation Before Deployment

Run these commands in project root:

```powershell
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Test locally:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

Confirm:

- API starts without model loading errors
- /predict works with a sample student payload

## 4.1) Your Current Situation (Frontend on Localhost, ML Ready)

If your Vercel app is still in local development (for example Next.js running on localhost), use this flow now:

1. Start FastAPI with explicit local CORS:

```powershell
$env:ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

2. In your frontend project (local), set API base URL:

```bash
# .env.local (frontend)
FASTAPI_BASE_URL=http://127.0.0.1:8000
```

If frontend code calls API directly from browser, you can also use:

```bash
NEXT_PUBLIC_FASTAPI_BASE_URL=http://127.0.0.1:8000
```

3. Restart frontend dev server after env change.

4. Test end-to-end from frontend UI:

- Predict flow should call POST /predict
- Dashboard flow should call POST /dashboard/class
- Alerts flow should call POST /alerts/screen

5. If frontend runs on teammate's laptop and FastAPI runs on your laptop, use LAN URL:

- FastAPI URL format: http://YOUR_LOCAL_IP:8000
- Example: http://192.168.1.29:8000

6. If LAN access fails, allow inbound firewall for 8000:

```powershell
New-NetFirewallRule -DisplayName "FastAPI 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

## 5) Deploy FastAPI to Render (Recommended)

### Step 1: Push code to GitHub

Push your latest main branch with:

- main.py
- requirements.txt
- runtime.txt
- saved_models folder

### Step 2: Create web service on Render

1. Login to Render
2. New + -> Web Service
3. Connect your GitHub repository
4. Use these settings:
   - Runtime: Python
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

### Step 3: Add environment variables

Set these in Render:

- ALLOWED_ORIGINS = https://your-vercel-app.vercel.app

If you have more than one frontend origin:

- ALLOWED_ORIGINS = https://your-vercel-app.vercel.app,https://www.yourdomain.com

### Step 4: Health check

Use:

- /health

### Step 5: Deploy and verify

After deploy, verify:

- https://your-render-service.onrender.com/health
- https://your-render-service.onrender.com/docs

## 6) What To Share With Your Vercel Team

Share only these items:

- Base URL, for example: https://your-render-service.onrender.com
- Endpoint list and request schema
- Expected response fields for each endpoint

Required frontend environment variable on Vercel:

- FASTAPI_BASE_URL = https://your-render-service.onrender.com

## 6.1) Local-to-Production Handoff (What You Change Later)

When your website moves from localhost to deployed Vercel, do exactly this:

1. Keep FastAPI deployed on Render/Railway (not on Vercel serverless for this ML workload).
2. Set backend CORS origin in FastAPI host:
   - ALLOWED_ORIGINS = https://your-vercel-app.vercel.app
3. Update frontend env on Vercel project settings:
   - FASTAPI_BASE_URL = https://your-render-service.onrender.com
4. Redeploy frontend on Vercel.
5. Verify from deployed app:
   - Prediction request works from website
   - No browser CORS errors
   - /health of FastAPI is reachable publicly

If you have preview + production Vercel URLs, allow both origins:

- ALLOWED_ORIGINS = https://your-vercel-app.vercel.app,https://your-vercel-preview-url.vercel.app

## 7) Vercel Integration Pattern (Recommended)

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

## 8) CORS Rules

Your API now supports ALLOWED_ORIGINS from environment variable.

For production:

- Do not keep wildcard origins unless needed
- Set only your Vercel domains

Example:

- ALLOWED_ORIGINS = https://your-vercel-app.vercel.app

## 9) Production Checklist

Before handing off to website team:

- API URL is HTTPS and publicly reachable
- /health returns healthy
- /docs is visible
- /predict returns expected fields
- CORS is restricted to Vercel domain
- Model files are present in deployment
- Response time is acceptable for expected traffic

## 10) Updating Models Later (Without Breaking Team)

When you retrain:

1. Replace files in saved_models
2. Commit and push
3. Trigger redeploy on Render
4. Re-test /health and /predict
5. Inform frontend team only if response schema changed

Best practice:

- Keep response schema stable
- Add version info in /model/info if needed

## 11) Quick Local Sharing (Same Wi-Fi Only)

If teammate is on same LAN:

1. Run:
   - uvicorn main:app --host 0.0.0.0 --port 8000 --reload
2. Share:
   - http://YOUR_LOCAL_IP:8000/docs
3. Allow firewall inbound on port 8000 if needed

This is only for temporary local testing, not production.

## 12) If You Need Public Temporary Demo Link

Use one of these:

- ngrok
- cloudflared tunnel

This is useful for hackathon demos before full deployment.

---

If you follow this guide exactly, your Vercel team can consume your FastAPI endpoints reliably while you keep model deployment independent and easy to update.
