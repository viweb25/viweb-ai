"""Request and response contracts for inspection programs, runs and modules."""

from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from vi_api.domain.inspection_programs.models import (
    DatasetContext,
    GoldenLayout,
    Program,
    ProgramDraft,
    ProgramSummary,
    Region,
    Run,
    Zone,
)
from vi_api.domain.modules.catalogue import Module

ClassName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
ZoneName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
ProgramName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Unit = Annotated[float, Field(ge=0, le=1)]

# ---------- Programs ----------


class ZoneBody(BaseModel):
    id: UUID
    name: ZoneName
    x1: Unit
    y1: Unit
    x2: Unit
    y2: Unit
    expected: dict[ClassName, Annotated[int, Field(ge=0, le=500)]] = Field(
        default={}, max_length=200
    )
    critical: bool = True

    @model_validator(mode="after")
    def positive_area(self):
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("A zone needs a positive width and height")
        return self

    def to_domain(self) -> Zone:
        return Zone(
            id=self.id,
            name=self.name,
            region=Region(self.x1, self.y1, self.x2, self.y2),
            expected=dict(self.expected),
            critical=self.critical,
        )

    @classmethod
    def from_domain(cls, zone: Zone) -> "ZoneBody":
        return cls(
            id=zone.id,
            name=zone.name,
            x1=zone.region.x1,
            y1=zone.region.y1,
            x2=zone.region.x2,
            y2=zone.region.y2,
            expected=zone.expected,
            critical=zone.critical,
        )


class CreateProgram(BaseModel):
    name: ProgramName
    dataset_id: UUID


class SaveProgram(BaseModel):
    name: ProgramName
    model_job_id: UUID | None = None
    confidence: float = Field(default=0.5, ge=0.05, le=0.99)
    review_margin: float = Field(default=0.15, ge=0, le=0.5)
    revision: int = Field(ge=1)
    zones: list[ZoneBody] = Field(default=[], max_length=50)

    def to_draft(self) -> ProgramDraft:
        return ProgramDraft(
            name=self.name,
            model_job_id=self.model_job_id,
            confidence=self.confidence,
            review_margin=self.review_margin,
            revision=self.revision,
            zones=[zone.to_domain() for zone in self.zones],
        )


class ProgramResponse(BaseModel):
    id: UUID
    name: str
    dataset_id: UUID
    model_job_id: UUID | None
    confidence: float
    review_margin: float
    revision: int
    updated_at: datetime | None
    published_revision: int | None = None
    zones: list[ZoneBody]
    classes: list[str]
    defect_classes: list[str]

    @classmethod
    def build(cls, program: Program, context: DatasetContext) -> "ProgramResponse":
        return cls(
            id=program.id,
            name=program.name,
            dataset_id=program.dataset_id,
            model_job_id=program.model_job_id,
            confidence=program.confidence,
            review_margin=program.review_margin,
            revision=program.revision,
            updated_at=program.updated_at,
            published_revision=program.published_revision,
            zones=[ZoneBody.from_domain(zone) for zone in program.zones],
            classes=context.classes,
            defect_classes=sorted(context.defect_classes),
        )


class ProgramSummaryResponse(BaseModel):
    id: UUID
    name: str
    dataset_id: UUID
    dataset_name: str
    model_job_id: UUID | None
    zone_count: int
    run_count: int
    pass_count: int
    pending_reviews: int
    last_run_at: datetime | None
    updated_at: datetime
    published_revision: int | None = None
    published_name: str | None = None

    @classmethod
    def build(cls, summary: ProgramSummary) -> "ProgramSummaryResponse":
        return cls(**asdict(summary))


class SavedProgram(BaseModel):
    revision: int


class DetectionResponse(BaseModel):
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float


class GoldenLayoutResponse(BaseModel):
    expected: dict[UUID, dict[str, int]]
    detections: list[DetectionResponse]
    outside: int

    @classmethod
    def build(cls, layout: GoldenLayout) -> "GoldenLayoutResponse":
        return cls(
            expected=layout.expected,
            detections=[DetectionResponse(**asdict(item)) for item in layout.detections],
            outside=layout.outside,
        )


# ---------- Runs ----------


class ZoneResultResponse(BaseModel):
    zone_id: UUID
    name: str
    decision: Literal["PASS", "FAIL", "REVIEW"]
    critical: bool
    expected: dict[str, int]
    found: dict[str, int]
    missing: dict[str, int]
    extra: dict[str, int]
    defects: list[str]
    uncertain: int


class RunResponse(BaseModel):
    id: UUID
    program_id: UUID
    program_name: str
    dataset_id: UUID | None
    model_job_id: UUID | None
    decision: Literal["PASS", "FAIL", "REVIEW"]
    zone_results: list[ZoneResultResponse]
    detections: list[DetectionResponse]
    confidence: float
    created_at: datetime | None
    review_status: Literal["none", "pending", "confirmed", "corrected"]
    review_note: str
    reviewed_at: datetime | None
    sent_to_dataset_at: datetime | None
    program_snapshot: dict | None = None
    dataset_archived: bool = False

    @classmethod
    def build(cls, run: Run) -> "RunResponse":
        data = asdict(run)
        data.pop("created_by")
        data.pop("image_digest")
        return cls(**data)


class ReviewRun(BaseModel):
    status: Literal["confirmed", "corrected", "pending"]
    note: str = Field(default="", max_length=400)


class SentToDataset(BaseModel):
    photo_id: UUID


# ---------- Modules ----------


class ModuleSectionResponse(BaseModel):
    key: str
    name: str
    icon: str


class ModuleResponse(BaseModel):
    key: str
    name: str
    summary: str
    icon: str
    status: Literal["available", "coming_soon"]
    sections: list[ModuleSectionResponse]
    highlights: list[str]

    @classmethod
    def build(cls, module: Module) -> "ModuleResponse":
        return cls.model_validate(asdict(module))
