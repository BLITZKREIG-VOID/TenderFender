"""
AWS Lambda entry point (Function URL, payload format v2.0).

Wraps the FastAPI app with Mangum. Lambda-only: Mangum lives in
``api/requirements-lambda.txt`` and is not needed for local development.

Handler string: ``api.lambda_handler.handler``
"""

from __future__ import annotations

from mangum import Mangum

from api.main import app


class LambdaHandler:
    def __init__(self):
        self.mangum = Mangum(app, lifespan="off")

    def __call__(self, event: dict, context) -> dict:
        if isinstance(event, dict) and event.get("source") == "aws.events":
            return {"warm": True}
        return self.mangum(event, context)


handler = LambdaHandler()
