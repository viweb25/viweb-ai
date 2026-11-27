import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from vi_api.app.training.dataset_service import DatasetService
from vi_api.app.training.job_service import TrainingJobService
from vi_api.bootstrap import app
from vi_api.container import get_dataset_service, get_training_job_service
from vi_api.domain.errors import Conflict, InvalidInput, NotFound, PermissionDenied
from vi_api.domain.identity.models import CurrentUser, Membership
from vi_api.domain.training import policies
from vi_api.domain.training.models import (
    DatasetDraft,
    JobRecord,
    Photo,
    PhotoFile,
    StartedJob,
    TrainingProgress,
    TrainingSource,
)
from vi_api.interfaces.http.dependencies.identity import get_current_user

ORG = uuid4()
OPERATOR = Membership(ORG, "Factory", "operator")
VIEWER = Membership(ORG, "Factory", "viewer")
ORIGIN = "http://127.0.0.1:3000"
NOW = datetime.now(UTC)


def run(coroutine):
    return asyncio.run(coroutine)


def box(label=None, x=0.1):
    value = {"start": {"x": x, "y": 0.1}, "end": {"x": x + 0.2, "y": 0.3}}
    return {**value, "label": label} if label else value


def photo_row(digest, boxes, reviewed=True):
    return {"id": uuid4(), "filename": "a.jpg", "digest": digest, "media_type": "image/jpeg",
            "reviewed": reviewed, "boxes": boxes}


class FakeFiles:
    def __init__(self, present=True):
        self.present = present
        self.written = []
        self.removed = []

    async def write_photo(self, org_id, dataset_id, photo, image):
        self.written.append((org_id, dataset_id, photo, image))

    async def photo_path(self, org_id, dataset_id, photo):
        return Path("/photo.jpg") if self.present else None

    async def all_photos_exist(self, org_id, dataset_id, photos):
        return self.present

    async def remove_dataset(self, org_id, dataset_id, job_ids):
        self.removed.append((org_id, dataset_id, job_ids))

    async def read_progress(self, org_id, job_id, epochs):
        return TrainingProgress(phase="learning", epoch=3, epochs=epochs)

    async def read_evaluation(self, org_id, job_id):
        return {"precision": 0.9}

    async def checkpoint(self, org_id, job_id, variant):
        return Path(f"/{variant}.pt") if self.present else None


class FakeDatasets:
    def __init__(self):
        self.saved = None

    async def save(self, org_id, dataset_id, draft):
        self.saved = (org_id, dataset_id, draft)
        return draft.revision + 1

    async def archive_idle(self, org_id, dataset_id):
        self.archived = (org_id, dataset_id)

    async def find_photo(self, org_id, dataset_id, photo_id):
        return None

    async def open(self, org_id, dataset_id):
        return None


def draft(**changes):
    value = DatasetDraft(
        part_name="Cap",
        inspection_note="",
        revision=0,
        photos=[Photo(uuid4(), "a.jpg", "image/jpeg", "a" * 64, True, [box()])],
        classes=["Cap"],
        class_info={"Cap": {"kind": "good", "hint": ""}, "Removed": {"kind": "defect", "hint": ""}},
    )
    return replace(value, **changes)


def test_save_requires_editor_role_and_drops_stale_class_info():
    datasets = DatasetService(FakeDatasets(), FakeFiles())
    with pytest.raises(PermissionDenied):
        run(datasets.save(VIEWER, uuid4(), draft()))
    assert run(datasets.save(OPERATOR, uuid4(), draft())) == 1
    assert datasets.datasets.saved[2].class_info == {"Cap": {"kind": "good", "hint": ""}}


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"classes": ["Cap", "cap"]}, "Each class must have a unique name."),
        ({"classes": ["Other"]}, "Add every existing box label"),
    ],
)
def test_save_rejects_invalid_classes(changes, message):
    with pytest.raises(InvalidInput, match=message):
        run(DatasetService(FakeDatasets(), FakeFiles()).save(OPERATOR, uuid4(), draft(**changes)))


def test_save_rejects_duplicate_photo_ids_and_missing_files():
    photo = draft().photos[0]
    with pytest.raises(InvalidInput, match="unique ID"):
        run(DatasetService(FakeDatasets(), FakeFiles()).save(
            OPERATOR, uuid4(), draft(photos=[photo, photo])
        ))
    with pytest.raises(InvalidInput, match="Upload it again"):
        run(DatasetService(FakeDatasets(), FakeFiles(present=False)).save(
            OPERATOR, uuid4(), draft()
        ))


def test_upload_checks_type_signature_and_digest():
    files = FakeFiles()
    service = DatasetService(FakeDatasets(), files)
    image = b"\xff\xd8\xffdata\xff\xd9"
    digest = hashlib.sha256(image).hexdigest()
    run(service.upload_photo(OPERATOR, uuid4(), PhotoFile(uuid4(), digest, "image/jpeg"), image))
    assert files.written[0][3] == image
    with pytest.raises(InvalidInput, match="file type"):
        run(service.upload_photo(OPERATOR, uuid4(), PhotoFile(uuid4(), digest, "image/png"), image))
    with pytest.raises(InvalidInput, match="did not match"):
        run(service.upload_photo(
            OPERATOR, uuid4(), PhotoFile(uuid4(), "0" * 64, "image/jpeg"), image
        ))


def test_delete_archives_dataset_and_keeps_files():
    files = FakeFiles()
    datasets = FakeDatasets()
    dataset_id = uuid4()
    run(DatasetService(datasets, files).delete(OPERATOR, dataset_id))
    assert datasets.archived == (OPERATOR.org_id, dataset_id)
    assert files.removed == []


def test_open_and_photo_report_not_found():
    service = DatasetService(FakeDatasets(), FakeFiles())
    with pytest.raises(NotFound, match="Dataset not found"):
        run(service.open(OPERATOR, uuid4()))
    with pytest.raises(NotFound, match="Photo not found"):
        run(service.photo_file(OPERATOR, uuid4(), uuid4()))


def test_snapshot_rules():
    source = TrainingSource(part_name="Cap", revision=1, classes=[])
    good = [photo_row(str(index) * 64, [box()] if index < 2 else []) for index in range(4)]
    snapshot = policies.build_snapshot(ORG, source, good, None)
    assert snapshot["org_id"] == str(ORG) and len(snapshot["photos"]) == 4

    with pytest.raises(InvalidInput, match="Review all photos"):
        policies.build_snapshot(ORG, source, good + [photo_row("9" * 64, [], False)], None)
    conflict = good + [photo_row("0" * 64, [])]
    with pytest.raises(InvalidInput, match="Identical photos"):
        policies.build_snapshot(ORG, source, conflict, None)
    with pytest.raises(InvalidInput, match="at least four"):
        policies.build_snapshot(ORG, source, good[:3], None)
    with pytest.raises(InvalidInput, match="each project class"):
        policies.build_snapshot(ORG, replace(source, classes=["Cap", "Lid"]), good, None)
    small = {"min_box_px": 128, "imgsz": 320}
    with pytest.raises(InvalidInput, match="at least four"):
        policies.build_snapshot(ORG, source, good, small)


class FakeJobs:
    def __init__(self, created=True, snapshot=None):
        self.created = created
        self.snapshot = snapshot
        self.built = None

    async def start(self, org_id, dataset_id, revision, build_snapshot):
        source = TrainingSource(part_name="Cap", revision=revision, classes=[])
        rows = [photo_row(str(index) * 64, [box()] if index < 2 else []) for index in range(4)]
        self.built = build_snapshot(source, rows)
        return StartedJob(JobRecord(uuid4(), revision, "queued", None, NOW, None), self.created)

    async def cancel(self, org_id, dataset_id, job_id):
        return False

    async def latest(self, org_id, dataset_id):
        return JobRecord(uuid4(), 2, "succeeded", None, NOW, NOW, options={"epochs": 50})

    async def completed(self, org_id, dataset_id):
        return [JobRecord(uuid4(), 2, "succeeded", None, NOW, NOW, snapshot=self.snapshot)]

    async def completed_snapshot(self, org_id, dataset_id, job_id):
        return self.snapshot


class FakePreview:
    async def preview(self, org_id, job_id, image, confidence):
        detections = [{"label": "Cap", "x1": 0.1, "y1": 0.1, "x2": 0.3, "y2": 0.3}]
        return json.dumps(detections).encode()


SNAPSHOT = {"part_name": "Cap", "photos": [{"id": str(uuid4()), "boxes": [box()]}],
            "options": {"version_name": "v1"}}


def test_start_attaches_options_only_to_new_jobs():
    options = {"version_name": "v2", "notes": "night shift", "min_box_px": 0}
    service = TrainingJobService(FakeJobs(), FakeFiles(), FakePreview())
    view = run(service.start(OPERATOR, uuid4(), 2, options))
    assert view.version_name == "v2" and view.options == options
    assert service.jobs.built["options"] == options

    reused = TrainingJobService(FakeJobs(created=False), FakeFiles(), FakePreview())
    view = run(reused.start(OPERATOR, uuid4(), 2, options))
    assert view.version_name == "" and view.options is None
    with pytest.raises(PermissionDenied):
        run(service.start(VIEWER, uuid4(), 2, None))


def test_latest_completed_cancel_and_checkpoint():
    service = TrainingJobService(FakeJobs(snapshot=SNAPSHOT), FakeFiles(), FakePreview())
    latest = run(service.latest(OPERATOR, uuid4()))
    assert latest.progress.epochs == 50 and latest.evaluation == {"precision": 0.9}
    completed = run(service.completed(OPERATOR, uuid4()))
    assert completed[0].version_name == "v1" and completed[0].reference_views[0]["counts"]
    with pytest.raises(Conflict):
        run(service.cancel(OPERATOR, uuid4(), uuid4()))
    assert run(service.checkpoint(OPERATOR, uuid4(), uuid4(), "last")) == Path("/last.pt")
    missing = TrainingJobService(FakeJobs(snapshot=None), FakeFiles(), FakePreview())
    with pytest.raises(NotFound, match="checkpoint unavailable"):
        run(missing.checkpoint(OPERATOR, uuid4(), uuid4(), "best"))


def test_preview_returns_raw_detections_or_decision():
    service = TrainingJobService(FakeJobs(snapshot=SNAPSHOT), FakeFiles(), FakePreview())
    raw = run(service.preview(OPERATOR, uuid4(), uuid4(), b"jpg", 0.5, False, None))
    assert json.loads(raw)[0]["label"] == "Cap"
    checked = run(service.preview(OPERATOR, uuid4(), uuid4(), b"jpg", 0.5, True, None))
    assert checked["decision"] == "PASS"


@pytest.fixture
def client(monkeypatch):
    user = CurrentUser(uuid4(), "Operator", None, [OPERATOR])
    monkeypatch.setitem(app.dependency_overrides, get_current_user, lambda: user)
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client


def test_http_maps_domain_errors_and_checks_origin(client, monkeypatch):
    monkeypatch.setitem(
        app.dependency_overrides,
        get_dataset_service,
        lambda: DatasetService(FakeDatasets(), FakeFiles()),
    )
    url = f"/api/v1/organisations/{ORG}/training-datasets/{uuid4()}"
    response = client.get(url)
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "dataset_not_found", "message": "Dataset not found"}
    }
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Request-ID"]
    assert client.delete(url).status_code == 403
    assert client.delete(url, headers={"Origin": ORIGIN}).status_code == 204
    other_org = f"/api/v1/organisations/{uuid4()}/training-datasets"
    assert client.get(other_org).status_code == 403


def test_http_start_training_returns_job(client, monkeypatch):
    monkeypatch.setitem(
        app.dependency_overrides,
        get_training_job_service,
        lambda: TrainingJobService(FakeJobs(), FakeFiles(), FakePreview()),
    )
    url = f"/api/v1/organisations/{ORG}/training-datasets/{uuid4()}/jobs"
    response = client.post(
        url,
        headers={"Origin": ORIGIN, "X-Request-ID": "trace-1"},
        json={"revision": 2, "options": {"version_name": "v2"}},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["options"]["version_name"] == "v2"
    assert response.headers["X-Request-ID"] == "trace-1"
