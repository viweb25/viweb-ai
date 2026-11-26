from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from vi_api.app.inspection.inspection_service import InspectionService
from vi_api.container import get_inspection_service
from vi_api.domain.inspection.ports import Engine
from vi_api.interfaces.http.dependencies.identity import BrowserOrigin, CurrentUserDependency
from vi_api.interfaces.http.validation import read_jpeg_frame

router = APIRouter(prefix="/api/v1/demo", tags=["Inspection"])
Inspections = Annotated[InspectionService, Depends(get_inspection_service)]
NO_STORE = {"Cache-Control": "no-store"}


@router.post(
    "/{engine}",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def inspect(
    engine: Engine,
    request: Request,
    service: Inspections,
    origin: BrowserOrigin,
    user: CurrentUserDependency,
) -> Response:
    image = await read_jpeg_frame(request)
    result = await service.inspect(user, engine, image, request.query_params.multi_items())
    return Response(
        result.content,
        status_code=result.status_code,
        media_type="application/json",
        headers=NO_STORE,
    )


@router.get("/detection-model")
async def detection_model(service: Inspections, user: CurrentUserDependency) -> Response:
    content = await service.detection_model(user)
    return Response(content, media_type="application/json", headers=NO_STORE)
