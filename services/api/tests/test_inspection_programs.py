"""Inspection programs: golden-layout rules, services with fake storage, and HTTP routes."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from vi_api.app.inspection_programs.program_service import ProgramService
from vi_api.app.inspection_programs.run_service import RunService
from vi_api.bootstrap import app
from vi_api.container import get_program_service, get_run_service
from vi_api.domain.errors import Conflict, InvalidInput, NotFound, PermissionDenied
from vi_api.domain.identity.models import CurrentUser, Membership
from vi_api.domain.inspection_programs import policies
from vi_api.domain.inspection_programs.models import (
    DatasetContext,
    Detection,
    Program,
    ProgramDraft,
    Region,
    Run,
    RunFilter,
    Zone,
)
from vi_api.interfaces.http.dependencies.identity import get_current_user

ORG = uuid4()
USER = uuid4()
DATASET = uuid4()
JOB = uuid4()
OPERATOR = Membership(ORG, "Factory", "operator")
VIEWER = Membership(ORG, "Factory", "viewer")
ORIGIN = "http://127.0.0.1:3000"
JPEG = b"\xff\xd8\xff\xe0board\xff\xd9"
LEFT = Zone(uuid4(), "Left terminals", Region(0, 0, 0.5, 1), {"bolt_ok": 2, "wire_red": 1})
RIGHT = Zone(uuid4(), "Right switch", Region(0.5, 0, 1, 1), {"switch_on": 1}, critical=False)
CONTEXT = DatasetContext(
    "Board", ["bolt_ok", "bolt_missing", "wire_red", "switch_on"], frozenset({"bolt_missing"})
)


def run(coroutine):
    return asyncio.run(coroutine)


def det(label, x, y=0.5, confidence=0.9):
    return Detection(label, confidence, x - 0.05, y - 0.05, x + 0.05, y + 0.05)


def good_board():
    return [det("bolt_ok", 0.1), det("bolt_ok", 0.2), det("wire_red", 0.3), det("switch_on", 0.8)]


# ---------- Rules (guide step 8) ----------


def test_golden_board_passes():
    result = policies.evaluate([LEFT, RIGHT], good_board(), 0.5, 0.15, CONTEXT.defect_classes)
    assert result.decision == "PASS"
    assert [zone.decision for zone in result.zones] == ["PASS", "PASS"]


def test_missing_bolt_fails_its_zone_and_the_board():
    detections = good_board()[1:]
    result = policies.evaluate([LEFT, RIGHT], detections, 0.5, 0.15)
    assert result.decision == "FAIL"
    assert result.zones[0].missing == {"bolt_ok": 1}
    assert result.zones[1].decision == "PASS"


def test_extra_or_unexpected_item_fails():
    detections = [*good_board(), det("wire_red", 0.4)]
    result = policies.evaluate([LEFT, RIGHT], detections, 0.5, 0.15)
    assert result.zones[0].extra == {"wire_red": 1}
    assert result.decision == "FAIL"


def test_defect_class_fails_even_when_counts_match():
    zone = replace(LEFT, expected={"bolt_ok": 1, "bolt_missing": 1})
    detections = [det("bolt_ok", 0.1), det("bolt_missing", 0.2)]
    result = policies.evaluate([zone], detections, 0.5, 0.15, CONTEXT.defect_classes)
    assert result.zones[0].defects == ["bolt_missing"]
    assert result.decision == "FAIL"


def test_uncertain_detection_sends_board_to_review():
    detections = [*good_board(), det("bolt_ok", 0.15, confidence=0.4)]
    result = policies.evaluate([LEFT, RIGHT], detections, 0.5, 0.15)
    assert result.zones[0].uncertain == 1
    assert result.decision == "REVIEW"


def test_detection_below_review_band_is_ignored():
    detections = [*good_board(), det("bolt_ok", 0.15, confidence=0.2)]
    assert policies.evaluate([LEFT, RIGHT], detections, 0.5, 0.15).decision == "PASS"


def test_non_critical_zone_failure_needs_review_not_fail():
    detections = good_board()[:3]
    result = policies.evaluate([LEFT, RIGHT], detections, 0.5, 0.15)
    assert result.zones[1].decision == "FAIL"
    assert result.decision == "REVIEW"


def test_detections_outside_zones_are_counted_not_judged():
    small = replace(LEFT, region=Region(0, 0, 0.5, 0.3), expected={})
    result = policies.evaluate([small], [det("bolt_ok", 0.2, y=0.8)], 0.5, 0.15)
    assert result.outside == 1
    assert result.decision == "PASS"


def test_evaluate_requires_zones():
    with pytest.raises(InvalidInput):
        policies.evaluate([], good_board(), 0.5, 0.15)


def test_golden_layout_counts_confident_detections_per_zone():
    layout = policies.golden_layout(
        [LEFT, RIGHT],
        [*good_board(), det("bolt_ok", 0.1, confidence=0.2), det("car", 0.2)],
        0.5,
        CONTEXT.classes,
    )
    assert layout.expected[LEFT.id] == {"bolt_ok": 2, "wire_red": 1}
    assert layout.expected[RIGHT.id] == {"switch_on": 1}


def test_draft_rejects_unknown_class_and_duplicate_zone_names():
    draft = ProgramDraft("P", JOB, 0.5, 0.15, 1, [replace(LEFT, expected={"nut": 1})])
    with pytest.raises(InvalidInput, match="not a class"):
        policies.check_draft(draft, CONTEXT.classes)
    twin = replace(RIGHT, name="left terminals", expected={})
    with pytest.raises(InvalidInput, match="different name"):
        policies.check_draft(replace(draft, zones=[LEFT, twin]), CONTEXT.classes)


def test_draft_rejects_margin_not_below_confidence():
    with pytest.raises(InvalidInput):
        policies.check_draft(ProgramDraft("P", None, 0.3, 0.3, 1, []), CONTEXT.classes)


def test_detection_floor_and_parsing():
    assert policies.detection_floor(0.5, 0.15) == 0.35
    assert policies.detection_floor(0.1, 0.2) == policies.MIN_DETECTION_CONFIDENCE
    rows = [
        {"label": "a", "confidence": 1, "x1": 0, "y1": 0, "x2": 1, "y2": 1},
        {"label": "broken"},
    ]
    assert len(policies.parse_detections(rows)) == 1


# ---------- Services with fakes ----------


class FakePrograms:
    def __init__(self, program):
        self.program = program
        self.saved = None
        self.completed = True

    async def get(self, org_id, program_id):
        return self.program if program_id == self.program.id and org_id == ORG else None

    async def dataset_context(self, org_id, dataset_id):
        return CONTEXT

    async def is_completed_job(self, org_id, dataset_id, job_id):
        return self.completed

    async def save(self, org_id, program_id, draft):
        self.saved = draft
        return draft.revision + 1

    async def delete(self, org_id, program_id):
        return [uuid4()]


class FakeRuns:
    def __init__(self):
        self.runs = {}
        self.sent = []
        self.reviews = []

    async def add(self, org_id, run):
        stored = replace(run, created_at=datetime.now(UTC))
        self.runs[run.id] = stored
        return stored

    async def get(self, org_id, run_id):
        return self.runs.get(run_id) if org_id == ORG else None

    async def list_for_org(self, org_id, filters):
        return list(self.runs.values())[: filters.limit]

    async def review(self, org_id, run_id, user_id, status, note):
        self.reviews.append((run_id, status, note))
        return run_id in self.runs

    async def send_to_dataset(self, org_id, run_id, photo):
        if self.runs[run_id].sent_to_dataset_at:
            raise Conflict("already", "already_sent")
        self.sent.append(photo)


class FakeImages:
    def __init__(self):
        self.stored = {}
        self.removed = []

    async def write(self, org_id, run_id, image):
        self.stored[run_id] = image

    async def path(self, org_id, run_id):
        return Path("/run.jpg") if run_id in self.stored else None

    async def read(self, org_id, run_id):
        return self.stored.get(run_id)

    async def remove(self, org_id, run_ids):
        self.removed.extend(run_ids)


class FakeFiles:
    def __init__(self):
        self.written = []

    async def checkpoint(self, org_id, job_id, variant):
        return Path("/best.pt")

    async def write_photo(self, org_id, dataset_id, photo, image):
        self.written.append((dataset_id, photo))


class FakePreview:
    def __init__(self, detections):
        self.detections = detections
        self.calls = []

    async def preview(self, org_id, job_id, image, confidence):
        self.calls.append(confidence)
        return json.dumps([d.__dict__ for d in self.detections]).encode()


def program(**changes):
    base = Program(uuid4(), "Board A", DATASET, JOB, 0.5, 0.15, 3, [LEFT, RIGHT])
    return replace(base, **changes)


def run_service(item, detections):
    preview = FakePreview(detections)
    service = RunService(FakePrograms(item), FakeRuns(), FakeImages(), FakeFiles(), preview)
    return service, preview


def test_inspect_logs_result_with_photo_and_asks_for_uncertain_detections():
    item = program()
    service, preview = run_service(item, good_board())
    result = run(service.inspect(OPERATOR, USER, item.id, JPEG))
    assert result.decision == "PASS"
    assert result.review_status == "none"
    assert preview.calls == [0.35]
    assert service.images.stored[result.id] == JPEG
    assert service.runs.runs[result.id].zone_results[0]["name"] == "Left terminals"


def test_review_result_starts_in_queue():
    item = program()
    service, _ = run_service(item, [*good_board(), det("bolt_ok", 0.15, confidence=0.4)])
    assert run(service.inspect(OPERATOR, USER, item.id, JPEG)).review_status == "pending"


def test_inspect_requires_model_and_inspector_role():
    item = program(model_job_id=None)
    service, _ = run_service(item, [])
    with pytest.raises(InvalidInput):
        run(service.inspect(OPERATOR, USER, item.id, JPEG))
    with pytest.raises(PermissionDenied):
        run(service.inspect(VIEWER, USER, item.id, JPEG))


def test_send_to_dataset_adds_unreviewed_photo_with_suggested_boxes_once():
    item = program()
    service, _ = run_service(item, [*good_board()[1:], det("car", 0.3)])
    result = run(service.inspect(OPERATOR, USER, item.id, JPEG))
    photo_id = run(service.send_to_dataset(OPERATOR, result.id))
    photo = service.runs.sent[0]
    assert photo.id == photo_id and photo.reviewed is False
    assert {box["label"] for box in photo.boxes} == {"bolt_ok", "wire_red", "switch_on"}
    assert service.files.written[0][0] == DATASET
    service.runs.runs[result.id] = replace(result, sent_to_dataset_at=datetime.now(UTC))
    with pytest.raises(Conflict):
        run(service.send_to_dataset(OPERATOR, result.id))


def test_review_unknown_run_is_not_found():
    service, _ = run_service(program(), [])
    with pytest.raises(NotFound):
        run(service.review(OPERATOR, USER, uuid4(), "confirmed", ""))


def test_save_checks_classes_and_model():
    item = program()
    repo = FakePrograms(item)
    service = ProgramService(repo, FakeFiles(), FakePreview([]), FakeImages())
    draft = ProgramDraft("Board A", JOB, 0.5, 0.15, 3, [LEFT])
    assert run(service.save(OPERATOR, item.id, draft)) == 4
    repo.completed = False
    with pytest.raises(InvalidInput):
        run(service.save(OPERATOR, item.id, draft))


def test_capture_golden_uses_saved_zones():
    item = program()
    service = ProgramService(
        FakePrograms(item), FakeFiles(), FakePreview(good_board()), FakeImages()
    )
    layout = run(service.capture_golden(OPERATOR, item.id, JPEG))
    assert layout.expected[RIGHT.id] == {"switch_on": 1}


def test_delete_removes_run_photos():
    item = program()
    images = FakeImages()
    service = ProgramService(FakePrograms(item), FakeFiles(), FakePreview([]), images)
    run(service.delete(OPERATOR, item.id))
    assert len(images.removed) == 1


# ---------- HTTP ----------


@pytest.fixture
def client():
    item = program()
    service, _ = run_service(item, good_board())
    programs = ProgramService(service.programs, service.files, service.previews, service.images)
    user = CurrentUser(USER, "Op", "op@example.test", [OPERATOR])
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_run_service] = lambda: service
    app.dependency_overrides[get_program_service] = lambda: programs
    try:
        yield TestClient(app), item, service
    finally:
        app.dependency_overrides.clear()


def test_http_inspect_then_list_and_review(client):
    http, item, service = client
    base = f"/api/v1/organisations/{ORG}"
    response = http.post(
        f"{base}/inspection-programs/{item.id}/runs",
        content=JPEG,
        headers={"Content-Type": "image/jpeg", "Origin": ORIGIN},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["decision"] == "PASS" and len(body["zone_results"]) == 2
    assert "created_by" not in body
    listed = http.get(f"{base}/inspection-runs?review_status=none").json()
    assert listed[0]["id"] == body["id"]
    reviewed = http.post(
        f"{base}/inspection-runs/{body['id']}/review",
        json={"status": "confirmed", "note": "ok"},
        headers={"Origin": ORIGIN},
    )
    assert reviewed.status_code == 204
    assert service.runs.reviews[0][1] == "confirmed"


def test_http_rejects_foreign_origin_and_other_org(client):
    http, item, _ = client
    response = http.post(
        f"/api/v1/organisations/{ORG}/inspection-programs/{item.id}/runs",
        content=JPEG,
        headers={"Content-Type": "image/jpeg", "Origin": "https://evil.test"},
    )
    assert response.status_code == 403
    other = http.get(f"/api/v1/organisations/{uuid4()}/inspection-runs")
    assert other.status_code == 403


def test_http_save_program_validates_zone_shape(client):
    http, item, _ = client
    zone = {"id": str(uuid4()), "name": "Z", "x1": 0.5, "y1": 0, "x2": 0.4, "y2": 1}
    response = http.put(
        f"/api/v1/organisations/{ORG}/inspection-programs/{item.id}",
        json={"name": "P", "revision": 3, "zones": [zone]},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 422


def test_http_modules_lists_available_and_coming_soon(client):
    http, _, _ = client
    modules = http.get("/api/v1/modules").json()
    status = {module["key"]: module["status"] for module in modules}
    assert status["object-detection"] == "available"
    assert status["anomaly-detection"] == "coming_soon"


def test_run_filter_defaults():
    assert RunFilter().limit == 50
    assert Run.__dataclass_fields__["review_status"]
