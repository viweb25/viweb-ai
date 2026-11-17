from pathlib import Path

from app.repositories.catalogue import JsonCatalogueRepository
from app.services.catalogue import CatalogueService

ROOT = Path(__file__).resolve().parents[4]


def catalogue_service() -> CatalogueService:
    return CatalogueService(
        JsonCatalogueRepository(ROOT / "packages/schemas/functions/catalogue.json")
    )
