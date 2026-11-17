from pathlib import Path

from vi_api.app.catalogue.get_function_templates import GetFunctionTemplates
from vi_api.app.health.check_readiness import CheckReadiness
from vi_api.infrastructure.database.readiness import DatabaseReadinessRepository
from vi_api.infrastructure.database.session import engine
from vi_api.infrastructure.repository.catalogue import JsonCatalogueRepository

ROOT = Path(__file__).resolve().parents[4]


def get_function_templates() -> GetFunctionTemplates:
    """Composition root: create the operation and its dependencies per request."""
    return GetFunctionTemplates(
        JsonCatalogueRepository(ROOT / "packages/schemas/functions/catalogue.json")
    )


def check_readiness() -> CheckReadiness:
    return CheckReadiness(DatabaseReadinessRepository(engine))
