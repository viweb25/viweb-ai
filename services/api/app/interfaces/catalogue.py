from typing import Protocol

from app.schemas.catalogue import FunctionTemplate


class CatalogueRepository(Protocol):
    def list_templates(self) -> list[FunctionTemplate]: ...
