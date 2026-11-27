from collections.abc import Callable
from pathlib import Path
from typing import Literal, Protocol
from uuid import UUID

from vi_api.domain.training.models import (
    DatasetDraft,
    DatasetSummary,
    DatasetWithPhotos,
    JobRecord,
    JsonObject,
    PhotoFile,
    StartedJob,
    TrainingProgress,
    TrainingSource,
)

SnapshotBuilder = Callable[[TrainingSource, list[JsonObject]], JsonObject]
CheckpointVariant = Literal["best", "last"]


class DatasetRepository(Protocol):
    async def list_for_org(self, org_id: UUID) -> list[DatasetSummary]: ...

    async def open(self, org_id: UUID, dataset_id: UUID) -> DatasetWithPhotos | None: ...

    async def save(self, org_id: UUID, dataset_id: UUID, draft: DatasetDraft) -> int:
        """Store the draft and return the new revision.

        Raises NotFound or Conflict when the revision is stale.
        """

    async def archive_idle(self, org_id: UUID, dataset_id: UUID) -> None:
        """Archive a dataset without active jobs."""

    async def find_photo(
        self, org_id: UUID, dataset_id: UUID, photo_id: UUID
    ) -> PhotoFile | None: ...


class TrainingJobRepository(Protocol):
    async def start(
        self, org_id: UUID, dataset_id: UUID, revision: int, build_snapshot: SnapshotBuilder
    ) -> StartedJob:
        """Lock the dataset, reuse an active job or insert a new one atomically."""

    async def cancel(self, org_id: UUID, dataset_id: UUID, job_id: UUID) -> bool: ...

    async def latest(self, org_id: UUID, dataset_id: UUID) -> JobRecord | None: ...

    async def completed(self, org_id: UUID, dataset_id: UUID) -> list[JobRecord]: ...

    async def completed_snapshot(
        self, org_id: UUID, dataset_id: UUID, job_id: UUID
    ) -> JsonObject | None: ...


class TrainingFileStore(Protocol):
    """Photo files and the trainer's run directory."""

    async def write_photo(
        self, org_id: UUID, dataset_id: UUID, photo: PhotoFile, image: bytes
    ) -> None: ...

    async def photo_path(
        self, org_id: UUID, dataset_id: UUID, photo: PhotoFile
    ) -> Path | None:
        """Return the stored file, or None when it is missing."""

    async def all_photos_exist(
        self, org_id: UUID, dataset_id: UUID, photos: list[PhotoFile]
    ) -> bool: ...

    async def remove_dataset(self, org_id: UUID, dataset_id: UUID, job_ids: list[UUID]) -> None: ...

    async def read_progress(
        self, org_id: UUID, job_id: UUID, epochs: int | None
    ) -> TrainingProgress: ...

    async def read_evaluation(self, org_id: UUID, job_id: UUID) -> dict[str, float] | None: ...

    async def checkpoint(
        self, org_id: UUID, job_id: UUID, variant: CheckpointVariant
    ) -> Path | None: ...


class TrainedModelPreview(Protocol):
    async def preview(
        self, org_id: UUID, job_id: UUID, image: bytes, confidence: float
    ) -> bytes:
        """Return the inference service's JSON detections."""
