from app.interfaces.catalogue import CatalogueRepository
from app.schemas.catalogue import FunctionTemplate


class CatalogueService:
    def __init__(self, repository: CatalogueRepository):
        self.repository = repository

    def list_templates(self) -> list[FunctionTemplate]:
        return self.repository.list_templates()
