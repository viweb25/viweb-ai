import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[2]


def test_all_schemas_and_examples():
    for path in (ROOT / "packages/schemas").rglob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text()))
    schema = json.loads((ROOT / "packages/schemas/results/inspection.schema.json").read_text())
    example = json.loads((ROOT / "packages/schemas/examples/inspection.json").read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    validator.validate(example)
    for status in ["error", "timeout"]:
        example.update(execution_status=status, decision="PASS")
        with pytest.raises(ValidationError):
            validator.validate(example)


def test_catalogue_configs_are_valid():
    items = json.loads((ROOT / "packages/schemas/functions/catalogue.json").read_text())
    assert len({item["id"] for item in items}) == 8
    for item in items:
        validator = Draft202012Validator(item["config_schema"])
        validator.validate({"name": "Line one"})
        with pytest.raises(ValidationError):
            validator.validate({"name": ""})
