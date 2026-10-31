#!/usr/bin/env bash
# Build the Lambda deployment package: build/lambda/ (tree), build/lambda.zip, build/lambda.sha.
# Dependencies are resolved for Lambda (x86_64 manylinux, LAMBDA_PYTHON) regardless of the host.
set -euo pipefail

cd "$(dirname "$0")/.."
LAMBDA_PYTHON="${LAMBDA_PYTHON:-3.14}"   # must match Runtime in infra/template.yaml (python${LAMBDA_PYTHON})
OUT=build/lambda

command -v uv >/dev/null || { echo "package-lambda: uv is required (https://docs.astral.sh/uv/)" >&2; exit 1; }

rm -rf "$OUT" build/lambda.zip build/lambda.sha
mkdir -p "$OUT"

uv pip install --quiet --target "$OUT" --python-platform x86_64-manylinux2014 \
  --python-version "$LAMBDA_PYTHON" --only-binary :all: -r api/requirements-lambda.txt

# Application code and the data the API reads (api/loaders.py resolves everything relative to the package root).
cp -r api "$OUT/api"
for d in artifacts/rules artifacts/graph artifacts/fused kb/passages data/tenders; do
  if [ -d "$d" ]; then
    mkdir -p "$OUT/$(dirname "$d")"
    cp -r "$d" "$OUT/$d"
  else
    echo "package-lambda: WARNING: $d is missing, package will not contain it (run 'make pipeline' first)" >&2
  fi
done
find "$OUT" -name __pycache__ -type d -prune -exec rm -rf {} +
rm -rf "${OUT:?}/bin"
rm -f "$OUT/api/requirements-api.txt"

# Content hash over file paths + bytes: identical inputs give an identical S3 key (idempotent deploys).
( cd "$OUT" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -c1-16 ) > build/lambda.sha

# Deterministic zip (sorted entries, fixed timestamps, explicit modes).
python3 - "$OUT" build/lambda.zip <<'PY'
import os, sys, zipfile
src, dest = sys.argv[1:3]
with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(root, name)
            info = zipfile.ZipInfo(os.path.relpath(full, src), date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if os.access(full, os.X_OK) else 0o644) << 16
            with open(full, "rb") as fh:
                z.writestr(info, fh.read())
PY

echo "package-lambda: build/lambda.zip $(du -h build/lambda.zip | cut -f1) ($(du -sh "$OUT" | cut -f1) unzipped), hash $(cat build/lambda.sha)"
