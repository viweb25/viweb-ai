"""Pure training rules. No I/O, so every rule is unit-testable."""

import hashlib
from collections import Counter
from uuid import UUID

from vi_api.domain.errors import InvalidInput, PermissionDenied, UnsupportedMediaType
from vi_api.domain.identity.models import Membership
from vi_api.domain.training.models import DatasetDraft, JsonObject, TrainingSource

EDITOR_ROLES = frozenset({"owner", "admin", "operator"})
PHOTO_MEDIA_TYPES = frozenset({"image/jpeg", "image/png"})
MIN_TRAINING_PHOTOS = 4
MIN_PHOTOS_WITH_PARTS = 2
MIN_PHOTOS_PER_LABEL = 2
LABEL_AGREEMENT = 0.45
LABEL_AGREEMENT_MARGIN = 0.20
NESTED_CONTAINMENT = 0.70


def require_editor(member: Membership) -> None:
    if member.role not in EDITOR_ROLES:
        raise PermissionDenied("You do not have permission to edit datasets")


def check_upload(media_type: str | None, image: bytes, digest: str) -> None:
    if media_type not in PHOTO_MEDIA_TYPES:
        raise UnsupportedMediaType("Choose a JPEG or PNG photo")
    is_jpeg = image.startswith(b"\xff\xd8\xff") and image.endswith(b"\xff\xd9")
    is_png = image.startswith(b"\x89PNG\r\n\x1a\n")
    if not (is_jpeg if media_type == "image/jpeg" else is_png):
        raise InvalidInput("The photo does not match its file type", "invalid_image")
    if hashlib.sha256(image).hexdigest() != digest:
        raise InvalidInput("The upload did not match the selected photo", "digest_mismatch")


def check_draft(draft: DatasetDraft) -> None:
    if len({photo.id for photo in draft.photos}) != len(draft.photos):
        raise InvalidInput("Each photo must have a unique ID")
    if draft.classes is None:
        return
    if len({name.casefold() for name in draft.classes}) != len(draft.classes):
        raise InvalidInput("Each class must have a unique name.")
    allowed = set(draft.classes)
    if any(
        (box.get("label") or draft.part_name) not in allowed
        for photo in draft.photos
        for box in photo.boxes
    ):
        raise InvalidInput("Add every existing box label to the project classes before saving.")


def class_info_for(draft: DatasetDraft) -> dict[str, JsonObject] | None:
    """Keep descriptions only for classes that the draft still has."""
    if draft.class_info is None:
        return None
    return {
        name: info
        for name, info in draft.class_info.items()
        if draft.classes is None or name in draft.classes
    }


def build_snapshot(
    org_id: UUID,
    source: TrainingSource,
    photos: list[JsonObject],
    options: JsonObject | None,
) -> JsonObject:
    """Validate a dataset for training and return the job's immutable snapshot."""
    if not all(photo["reviewed"] for photo in photos):
        raise InvalidInput("Review all photos before starting training.")
    unique: dict[str, JsonObject] = {}
    for photo in photos:
        previous = unique.setdefault(photo["digest"], photo)
        if previous["boxes"] != photo["boxes"]:
            raise InvalidInput("Identical photos have different labels. Check the boxes.")
    if options and options.get("min_box_px"):
        minimum = options["min_box_px"] / options["imgsz"]
        for photo in unique.values():
            photo["boxes"] = [
                box
                for box in photo["boxes"]
                if all(abs(box["start"][axis] - box["end"][axis]) >= minimum for axis in ("x", "y"))
            ]
    with_parts = sum(bool(photo["boxes"]) for photo in unique.values())
    if len(unique) < MIN_TRAINING_PHOTOS or with_parts < MIN_PHOTOS_WITH_PARTS:
        raise InvalidInput("Add at least four different photos, with the part in two.")
    coverage = Counter(
        label
        for photo in unique.values()
        for label in {box.get("label") or source.part_name for box in photo["boxes"]}
    )
    if source.classes and set(source.classes) != set(coverage):
        raise InvalidInput("Label examples of each project class before training.")
    if min(coverage.values()) < MIN_PHOTOS_PER_LABEL:
        raise InvalidInput("Include each part label in at least two different photos.")
    return {
        "org_id": str(org_id),
        "part_name": source.part_name,
        "photos": list(unique.values()),
        "options": options,
    }


def reference_views(snapshot: JsonObject) -> list[JsonObject]:
    """One example photo per distinct combination of labelled parts."""
    views: dict[tuple, JsonObject] = {}
    for index, photo in enumerate(snapshot["photos"], start=1):
        counts = Counter(box.get("label") or snapshot["part_name"] for box in photo["boxes"])
        if counts:
            views.setdefault(
                tuple(sorted(counts.items())),
                {
                    "id": photo["id"],
                    "name": photo.get("filename") or f"Training photo {index}",
                    "counts": dict(counts),
                },
            )
    return list(views.values())


def expected_parts(snapshot: JsonObject, reference: UUID | None) -> dict[str, int]:
    views = reference_views(snapshot)
    if reference is None and len(views) == 1:
        return views[0]["counts"]
    for view in views:
        if str(view["id"]) == str(reference):
            return view["counts"]
    raise InvalidInput("Choose the training view that matches the new photo.")


def overlap(first, second, *, containment: bool = False) -> float:
    x1, y1, x2, y2 = first
    a1, b1, a2, b2 = second
    intersection = max(0, min(x2, a2) - max(x1, a1)) * max(0, min(y2, b2) - max(y1, b1))
    if intersection == 0:
        return 0.0
    area_a = (x2 - x1) * (y2 - y1)
    area_b = (a2 - a1) * (b2 - b1)
    denominator = min(area_a, area_b) if containment else area_a + area_b - intersection
    return intersection / denominator


def resolve_label_conflicts(snapshot, expected, detections):
    """Use matching good views to resolve competing labels on the same physical part."""
    references = {label: [] for label in expected}
    for photo in snapshot["photos"]:
        boxes = [(box.get("label") or snapshot["part_name"], box) for box in photo["boxes"]]
        if Counter(label for label, _ in boxes) != expected:
            continue
        for label, box in boxes:
            start, end = box["start"], box["end"]
            references[label].append((
                min(start["x"], end["x"]), min(start["y"], end["y"]),
                max(start["x"], end["x"]), max(start["y"], end["y"]),
            ))

    candidates = []
    for detection in detections:
        bounds = tuple(detection[key] for key in ("x1", "y1", "x2", "y2"))
        agreement = max(
            (overlap(bounds, box) for box in references.get(detection["label"], [])),
            default=0.0,
        )
        candidates.append((detection, bounds, agreement))

    return [
        detection
        for detection, bounds, agreement in candidates
        if not (
            agreement < LABEL_AGREEMENT
            and any(
                other_agreement >= LABEL_AGREEMENT
                and other_agreement - agreement >= LABEL_AGREEMENT_MARGIN
                and overlap(bounds, other_bounds, containment=True) >= NESTED_CONTAINMENT
                for _, other_bounds, other_agreement in candidates
            )
        )
    ]


def evaluate_parts(expected, detections):
    found = Counter(detection["label"] for detection in detections)
    return {
        "decision": "PASS" if dict(found) == expected else "FAIL",
        "detections": detections,
        "expected": expected,
        "found": dict(found),
    }
