import hashlib
import json
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, StringConstraints, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from vi_api.domain.identity.models import Membership
from vi_api.infrastructure.database.session import Session
from vi_api.interfaces.http.controllers.auth import BrowserOrigin
from vi_api.interfaces.http.dependencies.identity import require_organisation_access
from vi_api.interfaces.http.validation import MAX_IMAGE_BYTES

router = APIRouter(
    prefix="/api/v1/organisations/{org_id}/training-datasets", tags=["Training datasets"]
)
OrgMember = Annotated[Membership, Depends(require_organisation_access)]
MediaType = Literal["image/jpeg", "image/png"]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


class Point(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


ClassName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class Box(BaseModel):
    start: Point
    end: Point
    label: ClassName | None = None

    @model_validator(mode="after")
    def nonempty(self):
        if self.start.x == self.end.x or self.start.y == self.end.y:
            raise ValueError("Draw a box with a positive width and height")
        return self


class Photo(BaseModel):
    id: UUID
    filename: str = Field(min_length=1, max_length=255)
    media_type: MediaType
    digest: Digest
    reviewed: bool
    boxes: list[Box] = Field(max_length=1000)


class ClassInfo(BaseModel):
    kind: Literal["good", "defect", "object"] = "object"
    hint: str = Field(default="", max_length=120)


class SaveDataset(BaseModel):
    part_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    inspection_note: str = Field(max_length=400)
    revision: int = Field(ge=0)
    photos: list[Photo] = Field(max_length=200)
    classes: list[ClassName] | None = Field(default=None, max_length=200)
    class_info: dict[ClassName, ClassInfo] | None = Field(default=None, max_length=200)


def require_editor(member: Membership) -> None:
    if member.role not in {"owner", "admin", "operator"}:
        raise HTTPException(403, "You do not have permission to edit datasets")


def image_path(
    org_id: UUID,
    dataset_id: UUID,
    photo_id: UUID,
    digest: str,
    media_type: str,
) -> Path:
    directory = os.getenv("VI_TRAINING_IMAGE_DIR")
    if not directory:
        raise HTTPException(503, "Training photo storage is unavailable")
    suffix = "jpg" if media_type == "image/jpeg" else "png"
    return Path(directory) / str(org_id) / str(dataset_id) / str(photo_id) / f"{digest}.{suffix}"


def write_image(path: Path, image: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent) as temporary:
        temporary.write(image)
        temporary.flush()
        os.fsync(temporary.fileno())
        try:
            os.link(temporary.name, path)
        except FileExistsError:
            pass


async def find_dataset(session: AsyncSession, org_id: UUID, dataset_id: UUID):
    row = await session.execute(
        text("""
            SELECT id, part_name, inspection_note, revision, classes, class_info
            FROM training_datasets WHERE id = :id AND org_id = :org_id
        """),
        {"id": dataset_id, "org_id": org_id},
    )
    return row.mappings().one_or_none()


@router.get("")
async def list_datasets(member: OrgMember, response: Response):
    response.headers["Cache-Control"] = "no-store"
    async with Session() as session:
        rows = await session.execute(
            text("""
                SELECT d.id, d.part_name, d.classes, d.class_info, d.updated_at,
                    (SELECT count(*) FROM training_photos p WHERE p.dataset_id = d.id) AS photo_count,
                    (SELECT count(*) FROM training_photos p
                        WHERE p.dataset_id = d.id AND p.reviewed) AS labeled_count,
                    (SELECT count(*) FROM training_jobs j
                        WHERE j.dataset_id = d.id AND j.status = 'succeeded') AS model_count,
                    (SELECT j.status FROM training_jobs j WHERE j.dataset_id = d.id
                        ORDER BY j.created_at DESC, j.id DESC LIMIT 1) AS latest_status
                FROM training_datasets d WHERE d.org_id = :org_id
                ORDER BY d.updated_at DESC, d.id
            """),
            {"org_id": member.org_id},
        )
        return [dict(row) for row in rows.mappings()]


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: UUID, member: OrgMember, _: BrowserOrigin):
    require_editor(member)
    async with Session.begin() as session:
        dataset = await session.scalar(
            text("SELECT id FROM training_datasets WHERE id = :id AND org_id = :org FOR UPDATE"),
            {"id": dataset_id, "org": member.org_id},
        )
        if dataset is None:
            raise HTTPException(404, "Dataset not found")
        active = await session.scalar(
            text("""
                SELECT 1 FROM training_jobs WHERE dataset_id = :id
                AND status IN ('queued', 'running') LIMIT 1
            """),
            {"id": dataset_id},
        )
        if active:
            raise HTTPException(409, "Stop the running training before deleting this project.")
        jobs = await session.scalars(
            text("DELETE FROM training_jobs WHERE dataset_id = :id RETURNING id"), {"id": dataset_id}
        )
        job_ids = list(jobs)
        await session.execute(text("DELETE FROM training_datasets WHERE id = :id"), {"id": dataset_id})
    await run_in_threadpool(remove_dataset_files, member.org_id, dataset_id, job_ids)
    return Response(status_code=204)


def remove_dataset_files(org_id: UUID, dataset_id: UUID, job_ids: list[UUID]) -> None:
    targets = []
    if image_root := os.getenv("VI_TRAINING_IMAGE_DIR"):
        targets.append(Path(image_root) / str(org_id) / str(dataset_id))
    if run_root := os.getenv("VI_TRAINING_RUN_DIR"):
        targets.extend(Path(run_root) / str(org_id) / str(job_id) for job_id in job_ids)
    for target in targets:
        shutil.rmtree(target, ignore_errors=True)


@router.put("/{dataset_id}/uploads/{photo_id}/{digest}", status_code=204)
async def upload_photo(
    dataset_id: UUID,
    photo_id: UUID,
    digest: Digest,
    request: Request,
    member: OrgMember,
    _: BrowserOrigin,
):
    require_editor(member)
    media_type = request.headers.get("content-type")
    if media_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(415, "Choose a JPEG or PNG photo")
    image = bytearray()
    async for chunk in request.stream():
        if len(image) + len(chunk) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Each photo must be 5 MiB or smaller")
        image.extend(chunk)
    is_jpeg = image.startswith(b"\xff\xd8\xff") and image.endswith(b"\xff\xd9")
    is_png = image.startswith(b"\x89PNG\r\n\x1a\n")
    if not (is_jpeg if media_type == "image/jpeg" else is_png):
        raise HTTPException(422, "The photo does not match its file type")
    if hashlib.sha256(image).hexdigest() != digest:
        raise HTTPException(422, "The upload did not match the selected photo")
    path = image_path(member.org_id, dataset_id, photo_id, digest, media_type)
    await run_in_threadpool(write_image, path, bytes(image))


@router.get("/{dataset_id}")
async def open_dataset(dataset_id: UUID, member: OrgMember, response: Response):
    response.headers["Cache-Control"] = "no-store"
    async with Session.begin() as session:
        await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        dataset = await find_dataset(session, member.org_id, dataset_id)
        if dataset is None:
            raise HTTPException(404, "Dataset not found")
        rows = await session.execute(
            text("""
                SELECT id, filename, media_type, digest, reviewed, boxes FROM training_photos
                WHERE dataset_id = :id ORDER BY position
            """),
            {"id": dataset_id},
        )
        return {**dataset, "photos": [dict(row) for row in rows.mappings()]}


@router.put("/{dataset_id}")
async def save_dataset(
    dataset_id: UUID,
    data: SaveDataset,
    member: OrgMember,
    _: BrowserOrigin,
):
    require_editor(member)
    if len({photo.id for photo in data.photos}) != len(data.photos):
        raise HTTPException(422, "Each photo must have a unique ID")

    if data.classes is not None:
        if len({name.casefold() for name in data.classes}) != len(data.classes):
            raise HTTPException(422, "Each class must have a unique name.")
        allowed = set(data.classes)
        if any((box.label or data.part_name) not in allowed for photo in data.photos for box in photo.boxes):
            raise HTTPException(422, "Add every existing box label to the project classes before saving.")

    def all_images_exist() -> bool:
        return all(
            image_path(
                member.org_id, dataset_id, photo.id, photo.digest, photo.media_type
            ).is_file()
            for photo in data.photos
        )

    if not await run_in_threadpool(all_images_exist):
        raise HTTPException(422, "A selected photo is missing. Upload it again.")
    values = {
        "id": dataset_id,
        "org_id": member.org_id,
        "part": data.part_name,
        "note": data.inspection_note,
        "revision": data.revision,
        "classes": json.dumps(data.classes) if data.classes is not None else None,
        "class_info": json.dumps({
            name: info.model_dump() for name, info in data.class_info.items()
            if data.classes is None or name in data.classes
        }) if data.class_info is not None else None,
    }
    async with Session.begin() as session:
        if data.revision == 0:
            statement = """
                INSERT INTO training_datasets (id, org_id, part_name, inspection_note, classes, class_info)
                VALUES (:id, :org_id, :part, :note, COALESCE(CAST(:classes AS jsonb), '[]'::jsonb),
                    COALESCE(CAST(:class_info AS jsonb), '{}'::jsonb))
                ON CONFLICT (id) DO NOTHING RETURNING revision
            """
        else:
            statement = """
                UPDATE training_datasets SET part_name = :part, inspection_note = :note,
                    classes = COALESCE(CAST(:classes AS jsonb), classes),
                    class_info = COALESCE(CAST(:class_info AS jsonb), class_info),
                    revision = revision + 1, updated_at = now()
                WHERE id = :id AND org_id = :org_id AND revision = :revision RETURNING revision
            """
        revision = await session.scalar(text(statement), values)
        if revision is None:
            if await find_dataset(session, member.org_id, dataset_id) is None:
                raise HTTPException(404, "Dataset not found")
            raise HTTPException(409, "A newer saved version exists. Reopen the dataset first.")
        await session.execute(
            text("DELETE FROM training_photos WHERE dataset_id = :id"), {"id": dataset_id}
        )
        if not data.photos:
            return {"revision": revision}
        await session.execute(
            text("""
                INSERT INTO training_photos
                    (dataset_id, id, filename, media_type, digest, reviewed, boxes, position)
                VALUES (:dataset_id, :id, :filename, :media_type, :digest,
                    :reviewed, CAST(:boxes AS jsonb), :position)
            """),
            [
                {
                    **photo.model_dump(),
                    "dataset_id": dataset_id,
                    "position": position,
                    "boxes": json.dumps([box.model_dump(exclude_none=True) for box in photo.boxes]),
                }
                for position, photo in enumerate(data.photos)
            ],
        )
    return {"revision": revision}


@router.get("/{dataset_id}/photos/{photo_id}")
async def open_photo(dataset_id: UUID, photo_id: UUID, member: OrgMember):
    async with Session() as session:
        result = await session.execute(
            text("""
                SELECT p.media_type, p.digest FROM training_photos p
                JOIN training_datasets d ON d.id = p.dataset_id
                WHERE d.org_id = :org_id AND d.id = :dataset_id AND p.id = :photo_id
            """),
            {"org_id": member.org_id, "dataset_id": dataset_id, "photo_id": photo_id},
        )
        photo = result.mappings().one_or_none()
    if photo is None:
        raise HTTPException(404, "Photo not found")
    path = image_path(member.org_id, dataset_id, photo_id, photo["digest"], photo["media_type"])
    if not await run_in_threadpool(path.is_file):
        raise HTTPException(404, "Photo file unavailable")
    return FileResponse(
        path,
        media_type=photo["media_type"],
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
