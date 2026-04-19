# Risk Evaluation Metrics

This document summarizes how risk score and risk label are evaluated in this project, and how low/medium/high ranges are interpreted.

## 1) Inputs (common to both models)

The same four features drive both risk score and risk label:

- assignment
- attendance
- lms
- marks

All are expected in the 0-100 range.

## 2) Risk score (0-100)

Two values are produced:

- risk_score_predicted: from the regression model.
- risk_score_calculated: from a weighted formula.

### 2.1 Weighted calculation

Formula (explicit):

risk_score = (1 - ((0.35*(attendance/100) + 0.30*(marks/100) + 0.20*(assignment/100) + 0.15*(lms/100)) / (0.35 + 0.30 + 0.20 + 0.15))) * 100

General form:

risk_score = (1 - (sum(w_i * (x_i / 100)) / sum(w_i))) * 100

Weights:

- attendance: 0.35
- marks: 0.30
- assignment: 0.20
- lms: 0.15

Interpretation:

- Higher score means higher risk.
- Lower score means lower risk.

### 2.2 Operational ranges (used in suggestions and alerts)

- High risk: >= 70
- Medium risk: 40 to 69
- Low risk: < 40

These thresholds are used in the ML API suggestion logic and the Core API alerts.

## 3) Risk label (Low / Medium / High)

Risk label is predicted by the classification model. It is not derived from the score thresholds at runtime.

- The model learns boundaries from training data.
- The label encoder maps the model output to Low / Medium / High.

This means:

- risk_label is a model prediction.
- risk_score ranges are a rule-based interpretation for operational use.

## 4) Reasons used for explainability

Reasons are created from feature percentiles stored in the metadata:

- A feature reason is added if value is below the 25th percentile (p25).
- A risk_score reason is added if risk_score is above the 75th percentile (p75).

## 5) Suggestions based on risk score and reasons

Suggestions are generated using:

- The risk score thresholds (High/Medium/Low), and
- The specific reasons (e.g., low attendance, low marks, low LMS, low assignments).

This gives targeted actions tied to the most likely drivers of risk.

## 6) LMS score method and formulation

In this project, the LMS score is treated as a direct input feature on a 0-100 scale. It is read from the dataset or provided by your LMS pipeline; there is no LMS formula implemented in code.

If you need to derive LMS score from raw LMS activity logs, use a normalized weighted formula. Example criteria (adjust weights to your context):

- Login frequency (per week)
- Time on platform (minutes per week)
- Content views or module completion
- Assignment submission rate
- Quiz or practice attempts
- Forum or discussion participation

Example formulation (all sub-scores normalized to 0-100):

LMS_score = 0.30 * login_score + 0.25 * time_score + 0.20 * submission_score + 0.15 * content_score + 0.10 * forum_score

Notes:

- Normalize each component to 0-100 before applying weights.
- Keep the same scale (0-100) so it matches model expectations.
- Low LMS scores (e.g., below the 25th percentile) are used in the explainability reasons.
