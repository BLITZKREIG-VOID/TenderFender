#!/usr/bin/env bash
# Run the full pipeline from cached inputs, then serve the API (live mode).
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${DEMO:-1}" = "1" ]; then
    "${PY:-.venv/bin/python}" scripts/demo_guard.py
fi
make pipeline
exec make api
