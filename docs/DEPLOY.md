# Deploying TenderFender to AWS (Free Tier — Lambda-Only Hosting)

## Architecture

Due to an initial AWS account restriction (CloudFront distributions require account verification with AWS Support before creation), TenderFender uses a **single Lambda Function URL** to serve both the FastAPI backend and the built React UI.

```
browser ── https ──> Lambda Function URL (AuthType NONE)
                     ├─ /api/*          → FastAPI API (Mangum handler, python3.14, x86_64, 1024 MB, 15 s)
                     └─ /* / /assets/*  → Built React UI static files from ui_dist (with GZip compression, immutable cache for assets, no-cache for index.html)
```

- **Keep-Warm Schedule:** An EventBridge rule (`AWS::Events::Rule`) with a `rate(5 minutes)` expression invokes the Lambda function periodically (`KeepWarm` parameter, default `true`), eliminating cold-start latency for demo use.
- **Function URL AuthType:** `AuthType NONE`. Both `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` permissions are granted.
- **Sizing:** 1024 MB RAM provides optimal CPU allocation under AWS Lambda's proportional CPU-to-memory scaling model, ensuring fast static file serving and quick JSON artifact loading within the 15-second timeout.

---

## Why CloudFront Was Removed & How to Add It Back Later

### Why CloudFront Was Removed
New AWS accounts are restricted from creating CloudFront distributions until AWS Support verifies the account (returning error code 403: *"Your account must be verified before you can add new CloudFront resources"*). 

### How to Add CloudFront Back (Post-Verification)
Once AWS Support verifies your account, you can re-enable CloudFront by:
1. Restoring `infra/template.yaml` to include an `AWS::CloudFront::Distribution`, an S3 `SiteBucket` with Origin Access Control (OAC), and a CloudFront Function for SPA routing.
2. Restoring `scripts/deploy_aws.sh` to sync `ui/dist` directly to the S3 site bucket and create a CloudFront invalidation.
3. Updating `api/main.py` to remove static file serving (leaving FastAPI purely as the backend API serving `/api/*`).

---

## Prerequisites

- AWS CLI v2, `uv`, Node.js + npm, `make`, and the repo's Python env (`make setup`) for gates.
- Credentials: `aws login` (or `aws sso login --profile <name>` then `export AWS_PROFILE=<name>`). Check with `aws sts get-caller-identity`.
- Region: `export AWS_REGION=ap-south-1` (default). Lambda and Budgets live in this region.
- Generated artifacts: `HF_HUB_OFFLINE=1 make pipeline` (creates `artifacts/`).
- Decision mode: `make pipeline` defaults to `DECISION_MODE=auto` (SoT §13 D29), so the committed saved decisions for T-001/T-002 are served as `decision_source: cache` with no API key; T-003 (no evidence) uses the template. `DECISION_MODE=template` is explicit opt-in.

---

## Commands

```bash
make deploy                                   # gates → UI build → lambda package → cloudformation stack → smoke test
BUDGET_EMAIL=you@example.com make deploy      # also create $1/month budget with 80% email alert
KEEP_WARM=false make deploy                   # deploy without the 5-minute EventBridge keep-warm rule
SKIP_GATES=1 make deploy                      # skip artifact / `make acceptance` / `make demo-guard` checks
make package-lambda                           # build build/lambda.zip
make build-ui                                 # npm ci + VITE_API_BASE=/api build into ui/dist
```

---

## Free-Tier & Cost Math

### Free-Tier Allowances (Always Free / Monthly)
- **AWS Lambda:** 1,000,000 requests and 400,000 GB-seconds per month [Pricing](https://aws.amazon.com/lambda/pricing/).
- **Amazon EventBridge:** 1,000,000 events per month free (Keep-warm uses 8,640 invocations/month).
- **S3 (Deploy Bucket):** Storage and requests for deployment zips are negligible; lifecycle policies expire old versions after 30 days.

### Keep-Warm Calculation
- **Invocations:** Every 5 minutes = 12 times/hour × 24 hours × 30 days = **8,640 invocations/month**.
- **GB-Seconds (at 1024 MB = 1 GB):** Assuming average keep-warm execution takes 0.2 seconds: 8,640 × 1 GB × 0.2 s = **1,728 GB-seconds/month** (well within the 400,000 GB-s free tier).

---

## Teardown

```bash
make destroy              # prompts; YES=1 make destroy to skip prompt
```

Deletes the CloudFormation stack (Lambda, Function URL, log group, IAM role, EventBridge keep-warm rule, budget) and empties/deletes the deployment S3 bucket.

---

## Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `aws sts get-caller-identity failed` | Not logged in. Run `aws login` or `aws sso login`. |
| Gate failure in `make acceptance`/`demo-guard` | Run `make pipeline` first. |
| Function URL returns 403 | Permissions missing: ensure both `ApiUrlInvokePermission` and `ApiInvokeViaUrlPermission` exist in template. |
| `/api/tenders` is `[]` | Artifacts missing in package; run `make pipeline`, then redeploy. |
| Stale UI after deploy | Function URL responses are dynamic from zip; trigger a new package build (`make package-lambda`) and redeploy. |
