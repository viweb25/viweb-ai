"""Export/check the public API contract. Run with the root PYTHONPATH (make contracts)."""

import argparse
import json
from pathlib import Path

from app.main import app

path = Path(__file__).resolve().parents[1] / "packages/schemas/openapi/api.json"
parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
content = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
if args.check:
    if not path.exists() or path.read_text() != content:
        raise SystemExit("OpenAPI drift: run uv run python scripts/export_openapi.py")
else:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
