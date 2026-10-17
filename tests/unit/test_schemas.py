from pathlib import Path

from photo_workflow.schemas import schema_documents


def test_committed_schemas_match_models():
    root = Path(__file__).parents[2] / 'src/photo_workflow/schemas'
    documents = schema_documents()
    assert {path.name for path in root.glob('*.json')} == set(documents)
    for name, expected in documents.items():
        assert (root / name).read_bytes() == expected
