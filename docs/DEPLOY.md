# Deploying TenderFender to AWS (Free Tier — Lambda-Only Hosting)

## Architecture

Due to an initial AWS account restriction (CloudFront distributions require account verification with AWS Support before creation), TenderFender uses a **single Lambda Function URL** to serve both the FastAPI backend and the built React UI.

```
browser ── https ──> Lambda Function URL (AuthType NONE)
                     ├─ /api/*          → FastAPI API (Mangum handler, python3.14, x86_64, 1024 MB, 60 s)
                     └─ /* / /assets/*  → Built React UI static files from ui_dist (with GZip compression, immutable cache for assets, no-cache for index.html)
```

- **Cognito User Pool:** Sign-in with email/password and optional Google OAuth 2.0. Uses the authorization code grant with PKCE (public app client, no client secret) with scopes `openid email profile`. Managed login page hosted at `<AuthDomainPrefix>.auth.<region>.amazoncognito.com`. Callback and logout URLs configured for the Function URL and local dev (`http://localhost:5173/auth/callback`).
- **DynamoDB Users Table:** `${Stack}-users` provisioned at 10 RCU / 10 WCU (within the 25/25 always-free tier), partition key `pk` (`USER#<sub>`), sort key `sk`. TTL on `expires_at` cleans up 3-day daily usage counters. Uses default AWS-owned encryption (no KMS customer key charges).
- **Cost Guard Budgets:** Three $100 monthly COST budgets with 15 absolute-value email alerts ($10, $20, $30, $40, $50, $55, $60, $65, $70, $75, $80, $85, $90, $95, $100) created when `BUDGET_EMAIL` is set.
- **Keep-Warm Schedule:** An EventBridge rule (`AWS::Events::Rule`) with a `rate(5 minutes)` expression invokes the Lambda function periodically (`KeepWarm` parameter, default `true`), eliminating cold-start latency for demo use.
- **Function URL AuthType:** `AuthType NONE`. Both `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` permissions are granted.
- **Sizing:** 1024 MB RAM provides optimal CPU allocation under AWS Lambda's proportional CPU-to-memory scaling model. Timeout is set to 60 seconds (with a 50 s upstream LLM deadline) to enforce strict cost guardrails.
- **Site AI on Amazon Bedrock (Disabled by Default):**
  - **Default False:** `SITE_AI_ENABLED` defaults to `false` in `infra/template.yaml` (parameter `SiteAiEnabled`), `scripts/deploy_aws.sh`, and `api/llm_routes.py`. The app runs in BYOK OpenRouter mode.
  - **Execution Role Access:** Lambda execution role `ApiRole` includes `bedrock:InvokeModel` scoped strictly to `arn:aws:bedrock:${AWS::Region}::foundation-model/openai.gpt-oss-120b-1:0`.
  - **Spend Guard ($10/month cap):** When explicitly enabled (`SITE_AI_ENABLED=true`), calls without an `X-LLM-Key` header run via Bedrock. A hard spend cap of $10 (`SITE_AI_MONTHLY_CAP_USD`) is tracked in integer micro-dollars in DynamoDB (`pk="GLOBAL", sk="SPEND#YYYY-MM"`). If the cap is reached, requests return 503 `site_ai_budget_exhausted`.
  - **Bedrock Budget & Automated Action:** An AWS Budget for Amazon Bedrock ($10/month) monitors Bedrock spend with email notifications at 50% and 100% when `BUDGET_EMAIL` is set. An `AWS::Budgets::BudgetsAction` automatically attaches a deny policy (`bedrock:InvokeModel*`) to the Lambda role at 100% actual spend as a backstop.
  - **Estimated Pricing:** Standard on-demand pricing for `openai.gpt-oss-120b-1:0` in `ap-south-1` is estimated at $0.18 per million input tokens (`BEDROCK_PRICE_IN_PER_MTOK`) and $0.71 per million output tokens (`BEDROCK_PRICE_OUT_PER_MTOK`), env-overridable. Marked as estimates.
  - **Account Verification:** Live Bedrock calls currently return `AccessDeniedException: Your account is currently being verified`. All test suites use mocked Bedrock calls; Site AI remains disabled by default until AWS account verification completes.
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

## Google OAuth Setup Steps

To enable Google sign-in alongside Cognito email/password:

1. **Open Google Cloud Console:**
   Navigate to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials).
2. **Configure OAuth Consent Screen:**
   - Select **User Type: External**.
   - Fill in App Name (`TenderFender`), User support email, and Developer contact email.
   - Add scopes: `openid`, `.../auth/userinfo.email`, and `.../auth/userinfo.profile`.
3. **Create OAuth 2.0 Client ID:**
   - Click **Create Credentials > OAuth client ID**.
   - Application type: **Web application**.
   - Name: `TenderFender Cognito Client`.
   - **Authorized redirect URIs:** enter the Cognito managed-login domain callback:
     ```text
     https://<AuthDomainPrefix>.auth.<region>.amazoncognito.com/oauth2/idpresponse
     ```
     *(Example for region `ap-south-1` and domain prefix `tenderfender-123456789012`: `https://tenderfender-123456789012.auth.ap-south-1.amazoncognito.com/oauth2/idpresponse`)*.
4. **Obtain Credentials:**
   Copy the generated **Client ID** (`...apps.googleusercontent.com`) and **Client Secret**.
5. **Deploy with Google Credentials:**
   Pass them as environment variables to `make deploy` or `deploy_aws.sh`:
   ```bash
   GOOGLE_CLIENT_ID="<client-id>.apps.googleusercontent.com" \
   GOOGLE_CLIENT_SECRET="<client-secret>" \
   BUDGET_EMAIL="you@example.com" \
   make deploy
   ```
   CloudFormation receives these via `NoEcho: true` parameters, ensuring credentials are never exposed in CloudFormation outputs, console logs, or Git commits.

---
## Prerequisites

- AWS CLI v2, `uv`, Node.js + npm, `make`, and the repo's Python env (`make setup`) for gates.
- Credentials: `aws login` (or `aws sso login --profile <name>` then `export AWS_PROFILE=<name>`). Check with `aws sts get-caller-identity`.
- Region: `export AWS_REGION=ap-south-1` (default). Lambda and Budgets live in this region.
- Generated artifacts: `HF_HUB_OFFLINE=1 make pipeline` (creates `artifacts/`).
- Decision mode: `make pipeline` defaults to `DECISION_MODE=auto` (SoT §13 D29), so the committed saved decisions for T-001/T-002 are served as `decision_source: cache` with no API key; T-003 (no evidence) uses the template. `DECISION_MODE=template` is explicit opt-in. Changing the default provider/model does not invalidate reviewed decisions in cache.
- LLM Provider: Env `LLM_PROVIDER` defaults to `bedrock` (using Bedrock Converse in `ap-south-1` with `openai.gpt-oss-120b-1:0`); set `LLM_PROVIDER=openrouter` to use OpenRouter.
---

## Commands

```bash
make deploy                                   # gates → UI build → lambda package → cloudformation stack → smoke test
BUDGET_EMAIL=you@example.com make deploy      # also create 3 budgets with 15 spend alerts ($10..$100)
GOOGLE_CLIENT_ID="id" GOOGLE_CLIENT_SECRET="sec" make deploy # enable Google sign-in
AUTH_DOMAIN_PREFIX=my-prefix make deploy      # customize Cognito domain prefix
KEEP_WARM=false make deploy                   # deploy without the 5-minute EventBridge keep-warm rule
SKIP_GATES=1 make deploy                      # skip artifact / `make acceptance` / `make demo-guard` checks
make package-lambda                           # build build/lambda.zip
make build-ui                                 # npm ci + VITE_API_BASE=/api build into ui/dist

---

## Free-Tier & Cost Math

### Free-Tier Allowances (Always Free / Monthly)
- **AWS Lambda:** 1,000,000 requests and 400,000 GB-seconds per month [Pricing](https://aws.amazon.com/lambda/pricing/). Sized at 1024 MB with 60 s timeout.
- **Amazon Cognito (Lite / Essentials Tier):**
  - **10,000 Monthly Active Users (MAU) free indefinitely** for users signing in directly or via social identity providers (Google). The free tier does not expire after 12 months.
  - Lite tier price is $0.0055/MAU thereafter (up to 100,000 MAUs); Essentials tier is $0.015/MAU thereafter.
  - Managed login domain format: `<prefix>.auth.<region>.amazoncognito.com`.
  - Verified on AWS Pricing page: [Amazon Cognito Pricing](https://aws.amazon.com/cognito/pricing/).
- **Amazon DynamoDB:**
- **25 RCU and 25 WCU provisioned capacity** are always free per account under the AWS Free Tier.
- The users table is sized at 10 RCU / 10 WCU provisioned, consuming only 40% of the free allowance.
- 25 GB of data storage is free.
  - Default AWS-owned encryption involves no AWS KMS customer key charges ($0/month).
  - Verified on AWS Pricing page: [Amazon DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/).
- **AWS Budgets:**
  - **Budget monitoring and email alert notifications are completely free of charge** (budgets without automated actions).
  - The first two action-enabled budgets are free; each subsequent action-enabled budget incurs $0.10/day. Our configuration uses notification-only alerts (no actions), which incur **$0.00**.
  - Verified on AWS Pricing page: [AWS Budgets Pricing](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/).
- **Amazon EventBridge:** 1,000,000 events per month free (Keep-warm uses 8,640 invocations/month).
- **S3 (Deploy Bucket):** Storage and requests for deployment zips are negligible; lifecycle policies expire old versions after 30 days.

### Keep-Warm Calculation
- **Invocations:** Every 5 minutes = 12 times/hour × 24 hours × 30 days = **8,640 invocations/month**.
- **GB-Seconds (at 1024 MB = 1 GB):** Assuming average keep-warm execution takes 0.2 seconds: 8,640 × 1 GB × 0.2 s = **1,728 GB-seconds/month** (well within the 400,000 GB-s free tier).

### Cost Guardrails & Global Caps
- **Per-user daily caps:** regen 10, compile 5, chat 30, detect 20.
- **Global daily caps:** `llm_total` (regen + compile + chat) 150/day, `detect_total` 300/day. Worst-case spending: 150 × 60 s × 1 GB = 9,000 GB-s/day ≈ 270,000 GB-s/month, well within the 400k GB-s/month free tier.

### Kill Switch
To disable LLM routes immediately (returning HTTP 503 `{"error": "...", "code": "llm_disabled"}`) while keeping the public demo, viewer, and rules engine online:
```bash
aws lambda update-function-configuration \
  --function-name tenderfender-api \
  --environment "Variables={MOCK=0,CONFIRMATIONS_PATH=/tmp/confirmations.json,USERS_TABLE=tenderfender-users,COGNITO_USER_POOL_ID=...,COGNITO_CLIENT_ID=...,COGNITO_DOMAIN=...,LLM_FEATURES_ENABLED=false}"
```
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
