from dataclasses import asdict
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from vi_api.app.training.job_service import TrainingJobService
from vi_api.container import get_training_job_service
from vi_api.domain.training.models import JobView
from vi_api.interfaces.http.dependencies.identity import BrowserOrigin, OrgMember
from vi_api.interfaces.http.schemas.training import StartTraining, TrainingJob
from vi_api.interfaces.http.validation import read_jpeg

router = APIRouter(
    prefix="/api/v1/organisations/{org_id}/training-datasets", tags=["Training jobs"]
)
Jobs = Annotated[TrainingJobService, Depends(get_training_job_service)]
NO_STORE = {"Cache-Control": "no-store"}


def to_response(view: JobView) -> TrainingJob:
    return TrainingJob.model_validate(asdict(view))


@router.post("/{dataset_id}/jobs", status_code=202)
async def start_training(
    dataset_id: UUID, data: StartTraining, member: OrgMember, service: Jobs, _: BrowserOrigin
) -> TrainingJob:
    options = data.options.model_dump() if data.options else None
    return to_response(await service.start(member, dataset_id, data.revision, options))


@router.post("/{dataset_id}/jobs/{job_id}/cancel", status_code=204)
async def cancel_training(
    dataset_id: UUID, job_id: UUID, member: OrgMember, service: Jobs, _: BrowserOrigin
) -> Response:
    await service.cancel(member, dataset_id, job_id)
    return Response(status_code=204)


@router.get("/{dataset_id}/jobs/latest")
async def latest_job(
    dataset_id: UUID, member: OrgMember, service: Jobs, response: Response
) -> TrainingJob | None:
    response.headers.update(NO_STORE)
    view = await service.latest(member, dataset_id)
    return to_response(view) if view else None


@router.get("/{dataset_id}/jobs")
async def completed_jobs(
    dataset_id: UUID, member: OrgMember, service: Jobs, response: Response
) -> list[TrainingJob]:
    response.headers.update(NO_STORE)
    return [to_response(view) for view in await service.completed(member, dataset_id)]


@router.get("/{dataset_id}/jobs/{job_id}/checkpoint", response_class=FileResponse)
async def download_checkpoint(
    dataset_id: UUID,
    job_id: UUID,
    member: OrgMember,
    service: Jobs,
    variant: Literal["best", "last"] = "best",
):
    path = await service.checkpoint(member, dataset_id, job_id, variant)
    return FileResponse(
        path, filename=f"{variant}.pt", media_type="application/octet-stream", headers=NO_STORE
    )


@router.post("/{dataset_id}/jobs/{job_id}/preview")
async def test_trained_model(
    dataset_id: UUID,
    job_id: UUID,
    request: Request,
    member: OrgMember,
    service: Jobs,
    _: BrowserOrigin,
    confidence: Annotated[float, Query(ge=0.01, le=1)] = 0.5,
    check: bool = False,
    reference: UUID | None = None,
) -> Response:
    image = await read_jpeg(request)
    result = await service.preview(
        member, dataset_id, job_id, image, confidence, check, reference
    )
    if isinstance(result, bytes):
        return Response(result, media_type="application/json", headers=NO_STORE)
    return JSONResponse(result, headers=NO_STORE)
