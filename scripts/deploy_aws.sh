#!/usr/bin/env bash
# Deploy TenderFender to AWS (Lambda Function URL serving API + built UI). Idempotent: re-run to update.
#
# Env: AWS_REGION (default ap-south-1), STACK_NAME (default tenderfender), BUDGET_EMAIL (optional $1/month alert),
#      KEEP_WARM (default true), SKIP_GATES=1 (skip artifact/acceptance/demo-guard checks), LAMBDA_PYTHON (default 3.14).
set -euo pipefail

cd "$(dirname "$0")/.."

export AWS_REGION="${AWS_REGION:-ap-south-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_PAGER=""
STACK_NAME="${STACK_NAME:-tenderfender}"
BUDGET_EMAIL="${BUDGET_EMAIL:-}"
KEEP_WARM="${KEEP_WARM:-true}"
SKIP_GATES="${SKIP_GATES:-0}"

log() { printf '\n==> %s\n' "$*"; }

# ── 1. Preflight ──────────────────────────────────────────────────────────────
log "Preflight (region $AWS_REGION)"
command -v aws >/dev/null || { echo "aws CLI not found; install AWS CLI v2." >&2; exit 1; }
if ! IDENTITY="$(aws sts get-caller-identity --query Account --output text 2>&1)"; then
  echo "ERROR: 'aws sts get-caller-identity' failed; no valid AWS credentials." >&2
  echo "       Run 'aws login' (or 'aws sso login --profile <name>' / 'aws configure') and re-run." >&2
  echo "       aws said: $IDENTITY" >&2
  exit 1
fi
ACCOUNT="$IDENTITY"
echo "AWS account $ACCOUNT"
DEPLOY_BUCKET="tenderfender-deploy-${ACCOUNT}-${AWS_REGION}"

# ── 2. Gates ──────────────────────────────────────────────────────────────────
if [ "$SKIP_GATES" = "1" ]; then
  echo "################################################################" >&2
  echo "# WARNING: SKIP_GATES=1, artifacts, 'make acceptance' and       #" >&2
  echo "# 'make demo-guard' are NOT being checked. Deploying anyway.    #" >&2
  echo "################################################################" >&2
else
  log "Gates"
  for p in artifacts/rules artifacts/graph/graph_output.json artifacts/fused; do
    [ -e "$p" ] || { echo "ERROR: $p missing. Run 'make pipeline' first (or SKIP_GATES=1)." >&2; exit 1; }
  done
  compgen -G "artifacts/fused/T-*.json" >/dev/null || { echo "ERROR: artifacts/fused has no T-*.json" >&2; exit 1; }
  make acceptance
  make demo-guard
fi

# ── 3. Build UI and Lambda package ────────────────────────────────────────────
log "Build UI (VITE_API_BASE=/api)"
npm --prefix ui ci
VITE_API_BASE=/api npm --prefix ui run build

log "Package Lambda"
bash scripts/package_lambda.sh
HASH="$(cat build/lambda.sha)"
CODE_KEY="lambda/tenderfender-${HASH}.zip"

# ── 4. Deploy bucket ──────────────────────────────────────────────────────────
log "Deploy bucket s3://$DEPLOY_BUCKET"
if aws s3api head-bucket --bucket "$DEPLOY_BUCKET" 2>/dev/null; then
  echo "exists"
else
  if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$DEPLOY_BUCKET" >/dev/null
  else
    aws s3api create-bucket --bucket "$DEPLOY_BUCKET" \
      --create-bucket-configuration "LocationConstraint=$AWS_REGION" >/dev/null
  fi
fi
aws s3api put-public-access-block --bucket "$DEPLOY_BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$DEPLOY_BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$DEPLOY_BUCKET" --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-bucket-lifecycle-configuration --bucket "$DEPLOY_BUCKET" --lifecycle-configuration \
  '{"Rules":[{"ID":"expire-old-packages","Status":"Enabled","Filter":{"Prefix":"lambda/"},"Expiration":{"Days":30},"NoncurrentVersionExpiration":{"NoncurrentDays":1},"AbortIncompleteMultipartUpload":{"DaysAfterInitiation":1}}]}'

# ── 5. Upload Lambda zip (content-hash key) ───────────────────────────────────
log "Upload s3://$DEPLOY_BUCKET/$CODE_KEY"
if aws s3api head-object --bucket "$DEPLOY_BUCKET" --key "$CODE_KEY" >/dev/null 2>&1; then
  echo "already uploaded (identical content)"
else
  aws s3 cp build/lambda.zip "s3://$DEPLOY_BUCKET/$CODE_KEY" --only-show-errors
fi

# ── 6. CloudFormation ─────────────────────────────────────────────────────────
log "CloudFormation stack $STACK_NAME"
aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --template-file infra/template.yaml \
  --s3-bucket "$DEPLOY_BUCKET" --s3-prefix cfn \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides "CodeBucket=$DEPLOY_BUCKET" "CodeKey=$CODE_KEY" "BudgetEmail=$BUDGET_EMAIL" "KeepWarm=$KEEP_WARM"

out() {
  aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
URL="$(out SiteUrl)"

# ── 7. Smoke test ─────────────────────────────────────────────────────────────
log "Smoke test"
for path in "" /api/health /api/tenders /api/tenders/T-002/analysis /tenders/T-002; do
  target="$URL$path"
  echo "Testing GET $target"
  start_time="$(date +%s%N)"
  resp_file="$(mktemp)"
  http_code="$(curl -s -o "$resp_file" -w "%{http_code}" --retry 6 --retry-delay 2 --max-time 15 "$target")"
  end_time="$(date +%s%N)"
  duration_ms=$(( (end_time - start_time) / 1000000 ))
  echo "  HTTP status: $http_code (time_total: ${duration_ms}ms)"
  [ "$http_code" = "200" ] || { echo "ERROR: $target returned HTTP $http_code" >&2; exit 1; }
  rm -f "$resp_file"
done

echo
echo "Deployed successfully: $URL"
