from main import app
import json

schema = app.openapi()
print(json.dumps(schema, indent=2))
