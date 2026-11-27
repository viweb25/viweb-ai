"""The inspection result log: list, review, and send photos back for retraining."""

import csv
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC
from io import StringIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import AwareDatetime, BaseModel

from vi_api.app.inspection_programs.run_service import RunService
from vi_api.container import get_run_service
from vi_api.domain.identity.models import Membership
from vi_api.domain.inspection_programs.models import Decision, ReviewStatus, RunFilter
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


def result_filters(
    program_id: UUID | None = None,
    decision: Decision | None = None,
    review_status: ReviewStatus | None = None,
    from_at: AwareDatetime | None = None,
    until_at: AwareDatetime | None = None,
) -> RunFilter:
    if from_at is not None and until_at is not None and from_at >= until_at:
        raise HTTPException(422, "Choose an end date on or after the start date.")
    return RunFilter(program_id, decision, review_status, from_at=from_at, until_at=until_at)


Filters = Annotated[RunFilter, Depends(result_filters)]


class ResultProgram(BaseModel):
    id: UUID
    name: str


@router.get("/programs")
async def list_result_programs(
    member: OrgMember, service: Runs, response: Response,
) -> list[ResultProgram]:
    response.headers.update(NO_STORE)
    return [ResultProgram(id=id_, name=name) for id_, name in await service.program_options(member)]


@router.get("")
async def list_runs(
    member: OrgMember,
    service: Runs,
    response: Response,
    filters: Filters,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    before_at: AwareDatetime | None = None,
    before_id: UUID | None = None,
) -> list[RunResponse]:
    if (before_at is None) != (before_id is None):
        raise HTTPException(422, "Both cursor fields are required.")
    response.headers.update(NO_STORE)
    page = replace(filters, limit=limit, before_at=before_at, before_id=before_id)
    return [RunResponse.build(run) for run in await service.list_runs(member, page)]


def _spreadsheet_text(value: str) -> str:
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


async def _result_csv(
    service: RunService, member: Membership, filters: RunFilter,
) -> AsyncIterator[str]:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow([
        "Run ID", "Inspected at (UTC)", "Program ID", "Program", "Program revision",
        "Model job ID", "Decision", "Review status", "Review note", "Reviewed at (UTC)",
    ])
    page = replace(filters, limit=200)
    while True:
        rows = await service.list_runs(member, page)
        for run in rows:
            writer.writerow([
                run.id, run.created_at.astimezone(UTC).isoformat() if run.created_at else "",
                run.program_id, _spreadsheet_text(run.program_name),
                (run.program_snapshot or {}).get("revision", ""), run.model_job_id,
                run.decision, run.review_status, _spreadsheet_text(run.review_note),
                run.reviewed_at.astimezone(UTC).isoformat() if run.reviewed_at else "",
            ])
        yield buffer.getvalue()
        if len(rows) < page.limit:
            return
        buffer.seek(0)
        buffer.truncate()
        page = replace(page, before_at=rows[-1].created_at, before_id=rows[-1].id)


@router.get("/export.csv")
async def export_results(member: OrgMember, service: Runs, filters: Filters) -> StreamingResponse:
    return StreamingResponse(
        _result_csv(service, member, filters), media_type="text/csv",
        headers={
            **NO_STORE,
            "Content-Disposition": 'attachment; filename="inspection-results.csv"',
        },
    )


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
