"""The product modules shown in the app menu."""

from typing import Annotated

from fastapi import APIRouter, Depends

from vi_api.app.modules.list_modules import ListModules
from vi_api.container import get_list_modules
from vi_api.interfaces.http.dependencies.identity import CurrentUserDependency
from vi_api.interfaces.http.schemas.inspection_programs import ModuleResponse

router = APIRouter(prefix="/api/v1", tags=["Modules"])


@router.get("/modules")
async def list_modules(
    _: CurrentUserDependency, operation: Annotated[ListModules, Depends(get_list_modules)]
) -> list[ModuleResponse]:
    return [ModuleResponse.build(module) for module in await operation.execute()]
