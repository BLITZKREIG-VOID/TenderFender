# Deploying TenderFender to AWS (Free Tier)

One CloudFront distribution fronts everything:

```
browser ── https ──> CloudFront ─┬─ /api/*  → Lambda Function URL (FastAPI via Mangum, python3.14, x86_64, 512 MB, 15 s)
                                 └─ default → private S3 bucket (built UI, Origin Access Control)
                                              + CloudFront Function: extension-less paths → /index.html (SPA routing)
```

- `/api/*` uses `CachingDisabled` + `AllViewerExceptHostHeader` and allows GET/HEAD/OPTIONS/PUT/POST/PATCH/DELETE.
- SPA routing is done by a CloudFront Function on the default behavior only; there are **no** distribution-wide custom error
  responses, so API 404s are returned unchanged.
- The Function URL uses `AuthType NONE` (the confirm `POST` makes SigV4/OAC impractical). The template grants both
  `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` (the latter with `lambda:InvokedViaFunctionUrl=true`);
  both are required, otherwise the URL returns 403 ([Function URL auth](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html)).
  The raw Function URL is therefore publicly callable; CloudFront is the intended entry point. The API is read-only apart
  from an in-memory "confirm" tick.
- Runtime `python3.14` is listed as supported on [Lambda runtimes](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html)
  (Amazon Linux 2023, deprecation Jun 2029). To use another runtime, change both `Runtime:` in `infra/template.yaml` and `LAMBDA_PYTHON` (e.g. `LAMBDA_PYTHON=3.13`).
- The package holds `api/`, `artifacts/{rules,graph,fused}`, `kb/passages`, `data/tenders` and `fastapi`, `pydantic`, `mangum`
  (`api/requirements-lambda.txt`). No torch / sentence-transformers / z3.

## Prerequisites

- AWS CLI v2, `uv`, Node.js + npm, `make`, and the repo's Python env (`make setup`) for the gates.
- Credentials: `aws login` (or `aws sso login --profile <name>` then `export AWS_PROFILE=<name>`). Check with `aws sts get-caller-identity`.
- Region: `export AWS_REGION=ap-south-1` (default). CloudFront and Budgets are global; Lambda/S3 live in this region.
- Generated artifacts: `HF_HUB_OFFLINE=1 make pipeline` (creates `artifacts/`).
- Permissions: CloudFormation, S3, Lambda, IAM (role creation), CloudFront, Logs, Budgets (only if `BUDGET_EMAIL` is used).

## Commands

```bash
make deploy                                   # gates → UI build → package → stack → UI sync → invalidation → smoke test
BUDGET_EMAIL=you@example.com make deploy      # also create the $1/month budget with an 80% email alert
AWS_REGION=us-east-1 STACK_NAME=tf-demo make deploy
SKIP_GATES=1 make deploy                      # skip artifact / `make acceptance` / `make demo-guard` checks (loud warning)
make package-lambda                           # just build build/lambda.zip
make build-ui                                 # npm ci + VITE_API_BASE=/api build into ui/dist
```

`deploy_aws.sh` steps: STS preflight → gates → UI build (`VITE_API_BASE=/api`) → Lambda zip → create/secure the versioned
bucket `tenderfender-deploy-<account>-<region>` → upload zip under `lambda/tenderfender-<content-hash>.zip` (skipped if it
exists) → `aws cloudformation deploy` → `aws s3 sync ui/dist --delete` (hashed assets first, `index.html` last) →
CloudFront invalidation `/*` → prints the URL → `curl` of `/api/health` and `/api/tenders`. Re-running with no changes
is a no-op apart from the UI sync and invalidation. The first deploy takes about 5 minutes (CloudFront propagation).

The UI must be built with a relative API base. If `ui/src/api/client.ts` still hardcodes `http://localhost:8000/api`, the
deployed UI will call the visitor's localhost; make sure the P4 fix (reads `VITE_API_BASE`) is merged first.

## What is free

Always-free / free-tier allowances (confirm current numbers; they change):

| Service | Allowance | Page |
|---|---|---|
| Lambda | 1M requests and 400,000 GB-seconds per month, always free | <https://aws.amazon.com/lambda/pricing/> |
| CloudFront | 1 TB data transfer out and 10M HTTP/S requests per month, always free; 1M function invocations (CloudFront Functions) | <https://aws.amazon.com/cloudfront/pricing/> |
| S3 | UI is under 1 MB; the Free Tier S3 allowance covers storage and requests at this scale | <https://aws.amazon.com/s3/pricing/> |
| CloudWatch Logs | 5 GB ingestion/storage free; retention here is 7 days | <https://aws.amazon.com/cloudwatch/pricing/> |
| AWS Budgets | first 2 budgets free | <https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/> |
| Overall plan | New accounts: Free plan with up to $200 credits for 6 months ("select services only"; check CloudFront, Lambda and Budgets are available on your plan) | <https://aws.amazon.com/free/> |

Hackathon traffic (thousands of requests) is far below every limit. Things that are **not** free: CloudFront invalidations
beyond 1,000 paths/month (each deploy uses 1 path), Lambda GB-seconds beyond the allowance, and data-transfer-out from
S3/Lambda to anything other than CloudFront. The Lambda has no reserved concurrency (new accounts may have a low
account concurrency limit that forbids reserving), and a public Function URL has no built-in rate limiting; set the
`BUDGET_EMAIL` alert as the safety net.

## Teardown

```bash
make destroy              # prompts; YES=1 make destroy to skip the prompt
```

Empties the UI bucket, deletes the CloudFormation stack (distribution, Lambda, log group, role, budget), then empties
(all versions) and deletes the deploy bucket. Same `AWS_REGION` / `STACK_NAME` as deploy.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `aws sts get-caller-identity failed` | Not logged in. `aws login` or `aws sso login`, check `AWS_PROFILE`. |
| Gate failure in `make acceptance`/`demo-guard` | Fix the pipeline output; or `SKIP_GATES=1` only for a throwaway test. |
| `/api/*` returns 403 `{"Message":"Forbidden"}` | Function URL permissions missing: both `ApiUrlInvokePermission` and `ApiInvokeViaUrlPermission` must exist. |
| `/api/*` returns 502/504 | `aws logs tail /aws/lambda/<stack>-api --follow`; cold start import errors, or a timeout (15 s). |
| `/api/tenders` is `[]` | The zip has no `artifacts/fused`; run `make pipeline`, redeploy (`package_lambda.sh` warns when directories are missing). |
| UI loads but data calls fail | UI was built without `VITE_API_BASE=/api` or calls localhost. |
| Stale UI after deploy | Invalidation takes up to a minute; `index.html` is served with `no-cache`. |
| `Runtime ... not supported` in a region | Set `Runtime` and `LAMBDA_PYTHON` to an older supported version (e.g. 3.13). |
| `BucketAlreadyOwnedByYou`/`AccessDenied` on deploy bucket | Name is `tenderfender-deploy-<account>-<region>`; check you are in the right account/region. |
| Stack stuck in `ROLLBACK_COMPLETE` | `make destroy`, then deploy again. |
