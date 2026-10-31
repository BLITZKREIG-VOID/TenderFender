#!/usr/bin/env bash
# Tear down everything deploy_aws.sh created: site bucket contents, the stack, and the deploy bucket.
# Env: AWS_REGION (default ap-south-1), STACK_NAME (default tenderfender), YES=1 to skip the prompt.
set -euo pipefail

export AWS_REGION="${AWS_REGION:-ap-south-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_PAGER=""
STACK_NAME="${STACK_NAME:-tenderfender}"

command -v aws >/dev/null || { echo "aws CLI not found; install AWS CLI v2." >&2; exit 1; }
if ! ACCOUNT="$(aws sts get-caller-identity --query Account --output text 2>&1)"; then
  echo "ERROR: no valid AWS credentials. Run 'aws login' (or 'aws sso login') and re-run." >&2
  echo "       aws said: $ACCOUNT" >&2
  exit 1
fi
DEPLOY_BUCKET="tenderfender-deploy-${ACCOUNT}-${AWS_REGION}"

echo "This will DELETE stack '$STACK_NAME' and bucket s3://$DEPLOY_BUCKET in account $ACCOUNT ($AWS_REGION)."
if [ "${YES:-0}" != "1" ]; then
  read -r -p "Type 'yes' to continue: " answer
  [ "$answer" = "yes" ] || { echo "Aborted."; exit 1; }
fi

# Delete every object version and delete marker, then the bucket.
empty_versioned_bucket() {
  local bucket="$1" kind query key ver
  for kind in Versions DeleteMarkers; do
    query="${kind}[].[Key,VersionId]"
    aws s3api list-object-versions --bucket "$bucket" --query "$query" --output text |
      while read -r key ver; do
        [ -z "$key" ] || [ "$key" = "None" ] && continue
        aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$ver" >/dev/null
      done
  done
}

if aws cloudformation describe-stacks --stack-name "$STACK_NAME" >/dev/null 2>&1; then
  SITE_BUCKET="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='SiteBucketName'].OutputValue" --output text)"
  if [ -n "$SITE_BUCKET" ] && [ "$SITE_BUCKET" != "None" ]; then
    echo "Emptying s3://$SITE_BUCKET"
    aws s3 rm "s3://$SITE_BUCKET" --recursive --only-show-errors
  fi
  echo "Deleting stack $STACK_NAME (CloudFront takes a few minutes)"
  aws cloudformation delete-stack --stack-name "$STACK_NAME"
  aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"
else
  echo "Stack $STACK_NAME not found; skipping."
fi

if aws s3api head-bucket --bucket "$DEPLOY_BUCKET" 2>/dev/null; then
  echo "Emptying and deleting s3://$DEPLOY_BUCKET"
  empty_versioned_bucket "$DEPLOY_BUCKET"
  aws s3api delete-bucket --bucket "$DEPLOY_BUCKET"
else
  echo "Deploy bucket $DEPLOY_BUCKET not found; skipping."
fi

echo "Destroyed."
