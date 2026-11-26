from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse

from vi_api.app.training.dataset_service import DatasetService
from vi_api.container import get_dataset_service
from vi_api.domain.training.models import PhotoFile
from vi_api.interfaces.http.dependencies.identity import BrowserOrigin, OrgMember
from vi_api.interfaces.http.schemas.training import Digest, SaveDataset, SavedRevision
from vi_api.interfaces.http.validation import MAX_IMAGE_BYTES, read_limited

router = APIRouter(
    prefix="/api/v1/organisations/{org_id}/training-datasets", tags=["Training datasets"]
)
Datasets = Annotated[DatasetService, Depends(get_dataset_service)]
NO_STORE = {"Cache-Control": "no-store"}


@router.get("")
async def list_datasets(member: OrgMember, service: Datasets, response: Response) -> list[dict]:
    response.headers.update(NO_STORE)
    return [asdict(dataset) for dataset in await service.list_datasets(member)]


@router.get("/{dataset_id}")
async def open_dataset(
    dataset_id: UUID, member: OrgMember, service: Datasets, response: Response
) -> dict:
    response.headers.update(NO_STORE)
    opened = await service.open(member, dataset_id)
    return {**asdict(opened.dataset), "photos": [asdict(photo) for photo in opened.photos]}


@router.put("/{dataset_id}")
async def save_dataset(
    dataset_id: UUID, data: SaveDataset, member: OrgMember, service: Datasets, _: BrowserOrigin
) -> SavedRevision:
    return SavedRevision(revision=await service.save(member, dataset_id, data.to_draft()))


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: UUID, member: OrgMember, service: Datasets, _: BrowserOrigin
) -> Response:
    await service.delete(member, dataset_id)
    return Response(status_code=204)


@router.put("/{dataset_id}/uploads/{photo_id}/{digest}", status_code=204)
async def upload_photo(
    dataset_id: UUID,
    photo_id: UUID,
    digest: Digest,
    request: Request,
    member: OrgMember,
    service: Datasets,
    _: BrowserOrigin,
) -> None:
    media_type = request.headers.get("content-type") or ""
    photo = PhotoFile(photo_id, digest, media_type)
    image = await read_limited(request, MAX_IMAGE_BYTES, "Each photo must be 5 MiB or smaller")
    await service.upload_photo(member, dataset_id, photo, image)


@router.get("/{dataset_id}/photos/{photo_id}")
async def open_photo(
    dataset_id: UUID, photo_id: UUID, member: OrgMember, service: Datasets
) -> FileResponse:
    path, media_type = await service.photo_file(member, dataset_id, photo_id)
    return FileResponse(
        path, media_type=media_type, headers={**NO_STORE, "X-Content-Type-Options": "nosniff"}
    )
