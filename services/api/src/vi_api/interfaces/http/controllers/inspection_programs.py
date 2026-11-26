"""Inspection programs: zones, golden layout and running an inspection."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from vi_api.app.inspection_programs.program_service import ProgramService
from vi_api.app.inspection_programs.run_service import RunService
from vi_api.container import get_program_service, get_run_service
from vi_api.interfaces.http.dependencies.identity import (
    BrowserOrigin,
    CurrentUserDependency,
    OrgMember,
)
from vi_api.interfaces.http.schemas.inspection_programs import (
    CreateProgram,
    GoldenLayoutResponse,
    ProgramResponse,
    ProgramSummaryResponse,
    RunResponse,
    SavedProgram,
    SaveProgram,
)
from vi_api.interfaces.http.validation import read_jpeg

router = APIRouter(
    prefix="/api/v1/organisations/{org_id}/inspection-programs", tags=["Inspection programs"]
)
Programs = Annotated[ProgramService, Depends(get_program_service)]
Runs = Annotated[RunService, Depends(get_run_service)]
NO_STORE = {"Cache-Control": "no-store"}
JPEG_BODY = {
    "requestBody": {
        "required": True,
        "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
    }
}


@router.get("")
async def list_programs(
    member: OrgMember, service: Programs, response: Response
) -> list[ProgramSummaryResponse]:
    response.headers.update(NO_STORE)
    return [ProgramSummaryResponse.build(item) for item in await service.list_programs(member)]


@router.post("", status_code=201)
async def create_program(
    data: CreateProgram, member: OrgMember, service: Programs, _: BrowserOrigin
) -> ProgramResponse:
    return ProgramResponse.build(*await service.create(member, data.dataset_id, data.name))


@router.get("/{program_id}")
async def open_program(
    program_id: UUID, member: OrgMember, service: Programs, response: Response
) -> ProgramResponse:
    response.headers.update(NO_STORE)
    return ProgramResponse.build(*await service.open(member, program_id))


@router.put("/{program_id}")
async def save_program(
    program_id: UUID, data: SaveProgram, member: OrgMember, service: Programs, _: BrowserOrigin
) -> SavedProgram:
    return SavedProgram(revision=await service.save(member, program_id, data.to_draft()))


@router.delete("/{program_id}", status_code=204)
async def delete_program(
    program_id: UUID, member: OrgMember, service: Programs, _: BrowserOrigin
) -> Response:
    await service.delete(member, program_id)
    return Response(status_code=204)


@router.post("/{program_id}/golden", openapi_extra=JPEG_BODY)
async def capture_golden(
    program_id: UUID, request: Request, member: OrgMember, service: Programs, _: BrowserOrigin
) -> GoldenLayoutResponse:
    """Propose the expected counts per zone from a photo of a known-good board."""
    image = await read_jpeg(request)
    return GoldenLayoutResponse.build(await service.capture_golden(member, program_id, image))


@router.post("/{program_id}/runs", status_code=201, openapi_extra=JPEG_BODY)
async def inspect_board(
    program_id: UUID,
    request: Request,
    member: OrgMember,
    user: CurrentUserDependency,
    service: Runs,
    _: BrowserOrigin,
) -> RunResponse:
    """Inspect one board photo: detect, compare with the golden layout, log the result."""
    image = await read_jpeg(request)
    return RunResponse.build(await service.inspect(member, user.id, program_id, image))
