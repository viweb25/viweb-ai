"""Request and response contracts for training datasets and jobs."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from vi_api.domain.training.models import DatasetDraft
from vi_api.domain.training.models import Photo as PhotoRecord

MediaType = Literal["image/jpeg", "image/png"]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
ClassName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class Point(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


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
    part_name: ClassName
    inspection_note: str = Field(max_length=400)
    revision: int = Field(ge=0)
    photos: list[Photo] = Field(max_length=200)
    classes: list[ClassName] | None = Field(default=None, max_length=200)
    class_info: dict[ClassName, ClassInfo] | None = Field(default=None, max_length=200)

    def to_draft(self) -> DatasetDraft:
        return DatasetDraft(
            part_name=self.part_name,
            inspection_note=self.inspection_note,
            revision=self.revision,
            photos=[
                PhotoRecord(
                    id=photo.id,
                    filename=photo.filename,
                    media_type=photo.media_type,
                    digest=photo.digest,
                    reviewed=photo.reviewed,
                    boxes=[box.model_dump(exclude_none=True) for box in photo.boxes],
                )
                for photo in self.photos
            ],
            classes=self.classes,
            class_info=(
                {name: info.model_dump() for name, info in self.class_info.items()}
                if self.class_info is not None
                else None
            ),
        )


class SavedRevision(BaseModel):
    revision: int


class TrainingOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_name: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=1000)
    epochs: int = Field(default=100, ge=1, le=300)
    batch: int = Field(default=16, ge=1, le=32)
    imgsz: Literal[320, 416, 512, 640, 768, 960, 1024] = 640
    validation_percent: int = Field(default=20, ge=5, le=40)
    test_percent: int = Field(default=10, ge=0, le=40)
    min_box_px: int = Field(default=0, ge=0, le=128)
    pretrained: bool = True
    freeze: int = Field(default=0, ge=0, le=10)
    lr0: float = Field(default=0.01, gt=0, le=0.1)
    lrf: float = Field(default=0.01, gt=0, le=1)
    cos_lr: bool = False
    warmup_epochs: float = Field(default=3, ge=0, le=15)
    optimizer: Literal["SGD", "Adam", "AdamW"] = "SGD"
    momentum: float = Field(default=0.937, ge=0, lt=1)
    weight_decay: float = Field(default=0.0005, ge=0, le=0.1)
    patience: int = Field(default=20, ge=1, le=100)
    seed: int = Field(default=0, ge=0, le=2147483647)
    box: float = Field(default=7.5, gt=0, le=20)
    cls: float = Field(default=0.5, gt=0, le=10)
    dfl: float = Field(default=1.5, gt=0, le=10)
    degrees: float = Field(default=0, ge=0, le=90)
    translate: float = Field(default=0.1, ge=0, le=0.5)
    scale: float = Field(default=0.5, ge=0, le=1)
    shear: float = Field(default=0, ge=0, le=30)
    perspective: float = Field(default=0, ge=0, le=0.001)
    hsv_h: float = Field(default=0.015, ge=0, le=0.5)
    hsv_s: float = Field(default=0.7, ge=0, le=1)
    hsv_v: float = Field(default=0.4, ge=0, le=1)
    fliplr: float = Field(default=0.5, ge=0, le=1)
    flipud: float = Field(default=0, ge=0, le=1)
    mosaic: float = Field(default=1, ge=0, le=1)
    mixup: float = Field(default=0, ge=0, le=1)
    close_mosaic: int = Field(default=10, ge=0, le=100)
    save_period: int = Field(default=0, ge=0, le=100)
    max_minutes: int = Field(default=240, ge=1, le=240)
    preset: Literal["fast", "balanced", "accurate", "custom"] = "custom"
    model_size: Literal["n", "s", "m", "l", "x"] = "n"
    copy_paste: float = Field(default=0, ge=0, le=1)
    erasing: float = Field(default=0.4, ge=0, le=0.9)
    iou: float = Field(default=0.7, ge=0.1, le=0.95)
    max_det: int = Field(default=300, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_split(self):
        if self.validation_percent + self.test_percent > 50:
            raise ValueError("Leave at least 50% of the data for training.")
        return self


class StartTraining(BaseModel):
    revision: int = Field(gt=0)
    options: TrainingOptions | None = None


class TrainingProgress(BaseModel):
    phase: Literal["preparing", "learning", "checking"]
    epoch: int = 0
    epochs: int | None = None
    score: float | None = None
    eta_seconds: int | None = None


class ReferenceView(BaseModel):
    id: UUID
    name: str
    counts: dict[str, int]


class TrainingJob(BaseModel):
    id: UUID
    dataset_revision: int
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    error: str | None
    created_at: datetime
    finished_at: datetime | None
    reference_views: list[ReferenceView] = Field(default_factory=list)
    evaluation: dict[str, float] | None = None
    version_name: str = ""
    notes: str = ""
    progress: TrainingProgress | None = None
    options: TrainingOptions | None = None
