from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

JsonObject = dict[str, Any]
ACTIVE_JOB_STATUSES = ("queued", "running")


@dataclass(frozen=True)
class DatasetSummary:
    id: UUID
    part_name: str
    classes: list[str]
    class_info: JsonObject
    updated_at: datetime
    photo_count: int
    labeled_count: int
    model_count: int
    latest_status: str | None


@dataclass(frozen=True)
class Dataset:
    id: UUID
    part_name: str
    inspection_note: str
    revision: int
    classes: list[str]
    class_info: JsonObject


@dataclass(frozen=True)
class Photo:
    id: UUID
    filename: str
    media_type: str
    digest: str
    reviewed: bool
    boxes: list[JsonObject]


@dataclass(frozen=True)
class PhotoFile:
    """Identifies one stored photo file. The digest is the SHA-256 hex of its bytes."""

    id: UUID
    digest: str
    media_type: str


@dataclass(frozen=True)
class DatasetWithPhotos:
    dataset: Dataset
    photos: list[Photo]


@dataclass(frozen=True)
class DatasetDraft:
    """A complete dataset save. ``revision`` 0 creates the dataset."""

    part_name: str
    inspection_note: str
    revision: int
    photos: list[Photo]
    classes: list[str] | None
    class_info: dict[str, JsonObject] | None


@dataclass(frozen=True)
class TrainingSource:
    """The locked dataset row that a new training job snapshots."""

    part_name: str
    revision: int
    classes: list[str]


@dataclass(frozen=True)
class JobRecord:
    id: UUID
    dataset_revision: int
    status: str
    error: str | None
    created_at: datetime
    finished_at: datetime | None
    snapshot: JsonObject | None = None
    options: JsonObject | None = None


@dataclass(frozen=True)
class StartedJob:
    job: JobRecord
    created: bool


@dataclass
class TrainingProgress:
    phase: str = "preparing"
    epoch: int = 0
    epochs: int | None = None
    score: float | None = None
    eta_seconds: int | None = None


@dataclass
class JobView:
    id: UUID
    dataset_revision: int
    status: str
    error: str | None
    created_at: datetime
    finished_at: datetime | None
    reference_views: list[JsonObject] = field(default_factory=list)
    evaluation: dict[str, float] | None = None
    version_name: str = ""
    notes: str = ""
    progress: TrainingProgress | None = None
    options: JsonObject | None = None

    @classmethod
    def from_record(cls, record: JobRecord, **extra) -> "JobView":
        return cls(
            id=record.id,
            dataset_revision=record.dataset_revision,
            status=record.status,
            error=record.error,
            created_at=record.created_at,
            finished_at=record.finished_at,
            **extra,
        )
