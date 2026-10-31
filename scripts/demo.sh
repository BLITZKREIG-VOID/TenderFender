#!/usr/bin/env bash
# Run the full pipeline from cached inputs, then serve the API (live mode).
set -euo pipefail
cd "$(dirname "$0")/.."
make pipeline
exec make api
