"""Regenerate committed schemas from the installed package."""

from pathlib import Path

from photo_workflow.schemas import schema_documents

root = Path(__file__).resolve().parents[1] / 'src/photo_workflow/schemas'
for name, document in schema_documents().items():
    (root / name).write_bytes(document)
