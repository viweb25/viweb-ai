import json
from pathlib import Path

from app.schemas.catalogue import FunctionTemplate


class JsonCatalogueRepository:
    """Static public reference data; never a repository for customer records."""

    def __init__(self, path: Path):
        self.path = path

    def list_templates(self) -> list[FunctionTemplate]:
        return [FunctionTemplate.model_validate(row) for row in json.loads(self.path.read_text())]
