"""Pure inspection rules: compare detections with the golden layout. No I/O.

Rules (in order):
1. A detection belongs to the first zone that contains its centre.
2. Detections at or above the confidence threshold are counted. Those just below it
   (within ``review_margin``) are *uncertain*.
3. A zone FAILS when any expected item is missing, any item is extra or unexpected,
   or a defect class is found. Otherwise it needs REVIEW when it has uncertain
   detections, else it PASSES.
4. The board FAILS when a critical zone fails. A failing non-critical zone, or any zone
   that needs review, sends the board to REVIEW. Otherwise the board PASSES.
"""

from collections import Counter
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from vi_api.domain.errors import InvalidInput, PermissionDenied
from vi_api.domain.identity.models import Membership
from vi_api.domain.inspection_programs.models import (
    Decision,
    Detection,
    Evaluation,
    GoldenLayout,
    ProgramDraft,
    Zone,
    ZoneResult,
)

EDITOR_ROLES = frozenset({"owner", "admin", "operator"})
INSPECTOR_ROLES = EDITOR_ROLES
MAX_ZONES = 50
MAX_EXPECTED_PER_CLASS = 500
MIN_REGION_SIDE = 0.01
MIN_DETECTION_CONFIDENCE = 0.05


def require_editor(member: Membership) -> None:
    if member.role not in EDITOR_ROLES:
        raise PermissionDenied("You do not have permission to change inspection programs")


def require_inspector(member: Membership) -> None:
    if member.role not in INSPECTOR_ROLES:
        raise PermissionDenied("You do not have permission to run or review inspections")


def check_draft(draft: ProgramDraft, classes: Iterable[str]) -> None:
    """Validate a program before saving. ``classes`` are the project's class names."""
    if not draft.name.strip():
        raise InvalidInput("Give the program a name.", "invalid_program")
    if not draft.review_margin < draft.confidence:
        raise InvalidInput(
            "The review margin must be smaller than the confidence.", "invalid_program"
        )
    if len(draft.zones) > MAX_ZONES:
        raise InvalidInput(f"A program can have up to {MAX_ZONES} zones.", "invalid_program")
    names = [zone.name.strip().casefold() for zone in draft.zones]
    if any(not name for name in names):
        raise InvalidInput("Give every zone a name.", "invalid_zone")
    if len(set(names)) != len(names):
        raise InvalidInput("Each zone needs a different name.", "invalid_zone")
    if len({zone.id for zone in draft.zones}) != len(draft.zones):
        raise InvalidInput("Each zone must have a unique ID.", "invalid_zone")
    known = set(classes)
    for zone in draft.zones:
        region = zone.region
        if not (0 <= region.x1 < region.x2 <= 1 and 0 <= region.y1 < region.y2 <= 1):
            raise InvalidInput(f"Zone “{zone.name}” is outside the photo.", "invalid_zone")
        if region.x2 - region.x1 < MIN_REGION_SIDE or region.y2 - region.y1 < MIN_REGION_SIDE:
            raise InvalidInput(f"Zone “{zone.name}” is too small.", "invalid_zone")
        for label, count in zone.expected.items():
            if label not in known:
                raise InvalidInput(
                    f"Zone “{zone.name}” expects “{label}”, which is not a class of this project.",
                    "unknown_class",
                )
            if not 0 <= count <= MAX_EXPECTED_PER_CLASS:
                raise InvalidInput(
                    f"Zone “{zone.name}”: “{label}” count is out of range.", "invalid_zone"
                )


def detection_floor(confidence: float, review_margin: float) -> float:
    """The lowest confidence to request from the model, so uncertain detections are visible."""
    return max(MIN_DETECTION_CONFIDENCE, round(confidence - review_margin, 4))


def parse_detections(rows: Iterable[dict[str, Any]]) -> list[Detection]:
    detections = []
    for row in rows:
        try:
            item = Detection(
                label=str(row["label"]),
                confidence=float(row["confidence"]),
                x1=float(row["x1"]),
                y1=float(row["y1"]),
                x2=float(row["x2"]),
                y2=float(row["y2"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if item.x2 > item.x1 and item.y2 > item.y1:
            detections.append(item)
    return detections


def zone_index(zones: list[Zone], detection: Detection) -> int | None:
    x, y = detection.center
    return next((index for index, zone in enumerate(zones) if zone.region.contains(x, y)), None)


def _positive(counter: Counter) -> dict[str, int]:
    return {label: count for label, count in sorted(counter.items()) if count > 0}


def evaluate_zone(
    zone: Zone, confident: list[Detection], uncertain: int, defect_classes: frozenset[str]
) -> ZoneResult:
    found = Counter(detection.label for detection in confident)
    expected = Counter(zone.expected)
    missing = _positive(expected - found)
    extra = _positive(found - expected)
    defects = sorted(label for label in found if label in defect_classes)
    decision: Decision
    if missing or extra or defects:
        decision = "FAIL"
    elif uncertain:
        decision = "REVIEW"
    else:
        decision = "PASS"
    return ZoneResult(
        zone_id=zone.id,
        name=zone.name,
        decision=decision,
        critical=zone.critical,
        expected=dict(zone.expected),
        found=_positive(found),
        missing=missing,
        extra=extra,
        defects=defects,
        uncertain=uncertain,
    )


def board_decision(results: list[ZoneResult]) -> Decision:
    if any(result.decision == "FAIL" and result.critical for result in results):
        return "FAIL"
    if any(result.decision != "PASS" for result in results):
        return "REVIEW"
    return "PASS"


def evaluate(
    zones: list[Zone],
    detections: list[Detection],
    confidence: float,
    review_margin: float,
    defect_classes: frozenset[str] = frozenset(),
) -> Evaluation:
    if not zones:
        raise InvalidInput("Add at least one zone before inspecting.", "zones_required")
    floor = confidence - review_margin
    confident: list[list[Detection]] = [[] for _ in zones]
    uncertain = [0] * len(zones)
    outside = 0
    for detection in detections:
        if detection.confidence < floor:
            continue
        index = zone_index(zones, detection)
        if index is None:
            outside += detection.confidence >= confidence
        elif detection.confidence >= confidence:
            confident[index].append(detection)
        else:
            uncertain[index] += 1
    results = [
        evaluate_zone(zone, confident[index], uncertain[index], defect_classes)
        for index, zone in enumerate(zones)
    ]
    return Evaluation(decision=board_decision(results), zones=results, outside=outside)


def golden_layout(
    zones: list[Zone], detections: list[Detection], confidence: float, classes: Iterable[str]
) -> GoldenLayout:
    """Count confident detections per zone on a known-good board: the proposed golden layout.

    Only the project's own classes count, so the proposal can always be saved.
    """
    if not zones:
        raise InvalidInput("Draw the zones first, then capture the golden board.", "zones_required")
    counts: dict[UUID, Counter] = {zone.id: Counter() for zone in zones}
    outside = 0
    known = set(classes)
    kept = [
        detection
        for detection in detections
        if detection.confidence >= confidence and detection.label in known
    ]
    for detection in kept:
        index = zone_index(zones, detection)
        if index is None:
            outside += 1
        else:
            counts[zones[index].id][detection.label] += 1
    return GoldenLayout(
        expected={zone_id: _positive(counter) for zone_id, counter in counts.items()},
        detections=kept,
        outside=outside,
    )


def initial_review_status(decision: Decision) -> str:
    """Results a person should look at start in the review queue."""
    return "pending" if decision == "REVIEW" else "none"


def suggested_boxes(
    detections: Iterable[dict[str, Any]], confidence: float, classes: Iterable[str]
) -> list[dict]:
    """Turn a run's confident detections of project classes into editable dataset boxes."""
    known = set(classes)
    return [
        {
            "label": detection.label,
            "start": {"x": detection.x1, "y": detection.y1},
            "end": {"x": detection.x2, "y": detection.y2},
        }
        for detection in parse_detections(detections)
        if detection.confidence >= confidence and detection.label in known
    ]
