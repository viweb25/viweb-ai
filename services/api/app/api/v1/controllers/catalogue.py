from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import catalogue_service
from app.schemas.catalogue import FunctionTemplate
from app.services.catalogue import CatalogueService

router = APIRouter(prefix="/api/v1", tags=["catalogue"])


@router.get("/function-templates", response_model=list[FunctionTemplate])
def templates(service: Annotated[CatalogueService, Depends(catalogue_service)]):
    """Public static catalogue. A template does not imply a trained model exists."""
    return service.list_templates()
