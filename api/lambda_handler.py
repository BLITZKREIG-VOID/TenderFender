"""
AWS Lambda entry point (Function URL, payload format v2.0).

Wraps the FastAPI app with Mangum. Lambda-only: Mangum lives in
``api/requirements-lambda.txt`` and is not needed for local development.

Handler string: ``api.lambda_handler.handler``
"""

from __future__ import annotations

from mangum import Mangum

from api.main import app

# lifespan="off": the app defines no startup/shutdown hooks.
handler = Mangum(app, lifespan="off")
