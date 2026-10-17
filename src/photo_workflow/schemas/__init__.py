"""Generate the committed JSON Schemas from the versioned models."""

import inspect
import json
import re

from photo_workflow import models
from photo_workflow.config import Configuration


def schema_documents():
    classes = [value for _, value in inspect.getmembers(models, inspect.isclass)
               if issubclass(value, models.Record) and value is not models.Record]
    classes.append(Configuration)
    return {re.sub(r'(?<!^)(?=[A-Z])', '-', model.__name__).lower() + '.schema.json':
            (json.dumps(model.model_json_schema(), sort_keys=True, indent=2) + '\n').encode() for model in classes}
