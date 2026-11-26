from dataclasses import replace
from pathlib import Path
from uuid import UUID

from vi_api.domain.errors import InvalidInput, NotFound
from vi_api.domain.identity.models import Membership
from vi_api.domain.training import policies
from vi_api.domain.training.models import (
    DatasetDraft,
    DatasetSummary,
    DatasetWithPhotos,
    PhotoFile,
)
from vi_api.domain.training.ports import DatasetRepository, TrainingFileStore


class DatasetService:
    """Training dataset use cases, scoped to the caller's organisation."""

    def __init__(self, datasets: DatasetRepository, files: TrainingFileStore):
        self.datasets = datasets
        self.files = files

    async def list_datasets(self, member: Membership) -> list[DatasetSummary]:
        return await self.datasets.list_for_org(member.org_id)

    async def open(self, member: Membership, dataset_id: UUID) -> DatasetWithPhotos:
        dataset = await self.datasets.open(member.org_id, dataset_id)
        if dataset is None:
            raise NotFound("Dataset not found", "dataset_not_found")
        return dataset

    async def save(self, member: Membership, dataset_id: UUID, draft: DatasetDraft) -> int:
        policies.require_editor(member)
        policies.check_draft(draft)
        files = [PhotoFile(photo.id, photo.digest, photo.media_type) for photo in draft.photos]
        if not await self.files.all_photos_exist(member.org_id, dataset_id, files):
            raise InvalidInput("A selected photo is missing. Upload it again.", "photo_missing")
        draft = replace(draft, class_info=policies.class_info_for(draft))
        return await self.datasets.save(member.org_id, dataset_id, draft)

    async def delete(self, member: Membership, dataset_id: UUID) -> None:
        policies.require_editor(member)
        job_ids = await self.datasets.delete_idle(member.org_id, dataset_id)
        await self.files.remove_dataset(member.org_id, dataset_id, job_ids)

    async def upload_photo(
        self,
        member: Membership,
        dataset_id: UUID,
        photo: PhotoFile,
        image: bytes,
    ) -> None:
        policies.check_upload(photo.media_type, image, photo.digest)
        await self.files.write_photo(member.org_id, dataset_id, photo, image)

    async def photo_file(
        self, member: Membership, dataset_id: UUID, photo_id: UUID
    ) -> tuple[Path, str]:
        photo = await self.datasets.find_photo(member.org_id, dataset_id, photo_id)
        if photo is None:
            raise NotFound("Photo not found", "photo_not_found")
        path = await self.files.photo_path(member.org_id, dataset_id, photo)
        if path is None:
            raise NotFound("Photo file unavailable", "photo_file_unavailable")
        return path, photo.media_type
