"""Dump the OpenAPI schema to JSON without starting the server."""

import json

from app.main import app

with open("../openapi.json", "w") as f:
    json.dump(app.openapi(), f, indent=2)

print("Wrote openapi.json")
