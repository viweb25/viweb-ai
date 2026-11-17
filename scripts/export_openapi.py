"""Export/check business and inference API snapshots using the root PYTHONPATH."""

import argparse
import json
from pathlib import Path

from app.main import app as business_app
from vi_inference.main import app as inference_app

ROOT = Path(__file__).resolve().parents[1] / "packages/schemas/openapi"
parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
for name, app in (("api.json", business_app), ("inference.json", inference_app)):
    path = ROOT / name
    content = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not path.exists() or path.read_text() != content:
            raise SystemExit(f"OpenAPI drift ({name}): run make export-contracts")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
