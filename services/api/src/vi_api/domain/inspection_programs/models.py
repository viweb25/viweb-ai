"""Inspection programs: a golden layout split into zones, and the log of inspection runs."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

Decision = Literal["PASS", "FAIL", "REVIEW"]
ReviewStatus = Literal["none", "pending", "confirmed", "corrected"]
JsonObject = dict[str, Any]


@dataclass(frozen=True)
class Region:
    """A rectangle in normalised image coordinates (0–1)."""

    x1: float
    y1: float
    x2: float
    y2: float

    def contains(self, x: float, y: float) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2


@dataclass(frozen=True)
class Zone:
    """One area of the board and what must be found inside it (the golden layout)."""

    id: UUID
    name: str
    region: Region
    expected: dict[str, int]
    critical: bool = True


@dataclass(frozen=True)
class Program:
    id: UUID
    name: str
    dataset_id: UUID
    model_job_id: UUID | None
    confidence: float
    review_margin: float
    revision: int
    zones: list[Zone]
    updated_at: datetime | None = None
    published_revision: int | None = None


@dataclass(frozen=True)
class ProgramDraft:
    """A complete program save. Zones replace the stored zones."""

    name: str
    model_job_id: UUID | None
    confidence: float
    review_margin: float
    revision: int
    zones: list[Zone]


@dataclass(frozen=True)
class ProgramSummary:
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


@dataclass(frozen=True)
class DatasetContext:
    """What a program needs to know about its project."""

    part_name: str
    classes: list[str]
    defect_classes: frozenset[str]


def program_snapshot(program: Program, context: DatasetContext) -> JsonObject:
    return {
        "revision": program.revision,
        "name": program.name,
        "confidence": program.confidence,
        "review_margin": program.review_margin,
        "classes": context.classes,
        "defect_classes": sorted(context.defect_classes),
        "zones": [dict(asdict(zone), id=str(zone.id)) for zone in program.zones],
    }


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2


@dataclass(frozen=True)
class ZoneResult:
    zone_id: UUID
    name: str
    decision: Decision
    critical: bool
    expected: dict[str, int]
    found: dict[str, int]
    missing: dict[str, int]
    extra: dict[str, int]
    defects: list[str]
    uncertain: int


@dataclass(frozen=True)
class Evaluation:
    decision: Decision
    zones: list[ZoneResult]
    outside: int
    """Confident detections that fall in no zone."""


@dataclass(frozen=True)
class Run:
    id: UUID
    program_id: UUID
    model_job_id: UUID | None
    decision: Decision
    zone_results: list[JsonObject]
    detections: list[JsonObject]
    confidence: float
    image_digest: str
    created_by: UUID
    review_status: ReviewStatus
    created_at: datetime | None = None
    program_name: str = ""
    dataset_id: UUID | None = None
    review_note: str = ""
    reviewed_at: datetime | None = None
    sent_to_dataset_at: datetime | None = None
    program_snapshot: JsonObject | None = None
    dataset_archived: bool = False


@dataclass(frozen=True)
class RunFilter:
    program_id: UUID | None = None
    decision: Decision | None = None
    review_status: ReviewStatus | None = None
    limit: int = 50
    from_at: datetime | None = None
    until_at: datetime | None = None
    before_at: datetime | None = None
    before_id: UUID | None = None


@dataclass(frozen=True)
class GoldenLayout:
    """Expected counts proposed from a photo of a known-good board."""

    expected: dict[UUID, dict[str, int]]
    detections: list[Detection] = field(default_factory=list)
    outside: int = 0
