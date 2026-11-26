"""The inspection result log: list, review, and send photos back for retraining."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse

from vi_api.app.inspection_programs.run_service import RunService
from vi_api.container import get_run_service
from vi_api.domain.inspection_programs.models import RunFilter
from vi_api.interfaces.http.dependencies.identity import (
    BrowserOrigin,
    CurrentUserDependency,
    OrgMember,
)
from vi_api.interfaces.http.schemas.inspection_programs import (
    ReviewRun,
    RunResponse,
    SentToDataset,
)

router = APIRouter(
    prefix="/api/v1/organisations/{org_id}/inspection-runs", tags=["Inspection results"]
)
Runs = Annotated[RunService, Depends(get_run_service)]
NO_STORE = {"Cache-Control": "no-store"}


@router.get("")
async def list_runs(
    member: OrgMember,
    service: Runs,
    response: Response,
    program_id: UUID | None = None,
    decision: Literal["PASS", "FAIL", "REVIEW"] | None = None,
    review_status: Literal["none", "pending", "confirmed", "corrected"] | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[RunResponse]:
    response.headers.update(NO_STORE)
    filters = RunFilter(program_id, decision, review_status, limit)
    return [RunResponse.build(run) for run in await service.list_runs(member, filters)]


@router.get("/{run_id}")
async def open_run(
    run_id: UUID, member: OrgMember, service: Runs, response: Response
) -> RunResponse:
    response.headers.update(NO_STORE)
    return RunResponse.build(await service.get(member, run_id))


@router.get("/{run_id}/image", response_class=FileResponse)
async def run_image(run_id: UUID, member: OrgMember, service: Runs):
    path = await service.image_path(member, run_id)
    return FileResponse(
        path, media_type="image/jpeg", headers={**NO_STORE, "X-Content-Type-Options": "nosniff"}
    )


@router.post("/{run_id}/review", status_code=204)
async def review_run(
    run_id: UUID,
    data: ReviewRun,
    member: OrgMember,
    user: CurrentUserDependency,
    service: Runs,
    _: BrowserOrigin,
) -> Response:
    await service.review(member, user.id, run_id, data.status, data.note)
    return Response(status_code=204)


@router.post("/{run_id}/send-to-dataset", status_code=201)
async def send_to_dataset(
    run_id: UUID, member: OrgMember, service: Runs, _: BrowserOrigin
) -> SentToDataset:
    """Add the photo to the project so a person can correct its boxes before retraining."""
    return SentToDataset(photo_id=await service.send_to_dataset(member, run_id))
