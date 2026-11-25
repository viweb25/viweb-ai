import csv
import json
import math
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

import httpx
from fastapi import HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from vi_api.infrastructure.database.session import Session
from vi_api.interfaces.http.controllers.auth import BrowserOrigin
from vi_api.interfaces.http.controllers.training_datasets import OrgMember, require_editor, router
from vi_api.interfaces.http.dependencies.identity import SettingsDependency
from vi_api.interfaces.http.validation import read_jpeg


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


@router.post("/{dataset_id}/jobs", status_code=202)
async def start_training(
    dataset_id: UUID,
    data: StartTraining,
    member: OrgMember,
    _: BrowserOrigin,
) -> TrainingJob:
    require_editor(member)
    ids = {"id": dataset_id, "org": member.org_id}
    async with Session.begin() as session:
        result = await session.execute(
            text("""
                SELECT part_name, revision, classes FROM training_datasets
                WHERE id = :id AND org_id = :org FOR UPDATE
            """),
            ids,
        )
        dataset = result.mappings().one_or_none()
        if dataset is None:
            raise HTTPException(404, "Dataset not found")
        if dataset["revision"] != data.revision:
            raise HTTPException(409, "Open the latest saved version before training.")
        active = await session.execute(
            text("""
                SELECT id, dataset_revision, status, error, created_at, finished_at
                FROM training_jobs WHERE dataset_id = :id AND status IN ('queued', 'running')
            """),
            ids,
        )
        job = active.mappings().one_or_none()
        if job is not None:
            if job["dataset_revision"] != data.revision:
                raise HTTPException(409, "An earlier revision is still training.")
            return TrainingJob.model_validate(dict(job))
        result = await session.execute(
            text("""
                SELECT id, filename, digest, media_type, reviewed, boxes FROM training_photos
                WHERE dataset_id = :id ORDER BY position
            """),
            ids,
        )
        photos = [dict(photo) for photo in result.mappings()]
        if not all(photo["reviewed"] for photo in photos):
            raise HTTPException(422, "Review all photos before starting training.")
        unique = {}
        for photo in photos:
            previous = unique.setdefault(photo["digest"], photo)
            if previous["boxes"] != photo["boxes"]:
                raise HTTPException(422, "Identical photos have different labels. Check the boxes.")
        if data.options and data.options.min_box_px:
            minimum = data.options.min_box_px / data.options.imgsz
            for photo in unique.values():
                photo["boxes"] = [
                    box for box in photo["boxes"]
                    if all(abs(box["start"][axis] - box["end"][axis]) >= minimum for axis in ("x", "y"))
                ]
        if len(unique) < 4 or sum(bool(photo["boxes"]) for photo in unique.values()) < 2:
            raise HTTPException(422, "Add at least four different photos, with the part in two.")
        label_coverage = Counter(
            label
            for photo in unique.values()
            for label in {box.get("label") or dataset["part_name"] for box in photo["boxes"]}
        )
        if dataset["classes"] and set(dataset["classes"]) != set(label_coverage):
            raise HTTPException(422, "Label examples of each project class before training.")
        if min(label_coverage.values()) < 2:
            raise HTTPException(422, "Include each part label in at least two different photos.")
        snapshot = {
            "org_id": str(member.org_id),
            "part_name": dataset["part_name"],
            "photos": list(unique.values()),
            "options": data.options.model_dump() if data.options else None,
        }
        job = await session.execute(
            text("""
                INSERT INTO training_jobs (dataset_id, dataset_revision, snapshot)
                VALUES (:id, :revision, CAST(:snapshot AS jsonb))
                RETURNING id, dataset_revision, status, error, created_at, finished_at
            """),
            {
                "id": dataset_id,
                "revision": data.revision,
                "snapshot": json.dumps(snapshot, default=str),
            },
        )
        return TrainingJob.model_validate(dict(
            job.mappings().one(), version_name=data.options.version_name if data.options else "",
            notes=data.options.notes if data.options else "", options=data.options,
        ))


@router.post("/{dataset_id}/jobs/{job_id}/cancel", status_code=204)
async def cancel_training(dataset_id: UUID, job_id: UUID, member: OrgMember, _: BrowserOrigin):
    require_editor(member)
    async with Session.begin() as session:
        stopped = await session.scalar(
            text("""
                UPDATE training_jobs j SET status = 'cancelled', finished_at = now()
                FROM training_datasets d
                WHERE j.id = :job AND j.dataset_id = d.id AND d.id = :id AND d.org_id = :org
                    AND j.status IN ('queued', 'running')
                RETURNING j.id
            """),
            {"job": job_id, "id": dataset_id, "org": member.org_id},
        )
    if stopped is None:
        raise HTTPException(409, "This training run is no longer active.")
    return Response(status_code=204)


@router.get("/{dataset_id}/jobs/latest")
async def latest_job(dataset_id: UUID, member: OrgMember, response: Response) -> TrainingJob | None:
    response.headers["Cache-Control"] = "no-store"
    async with Session() as session:
        result = await session.execute(
            text("""
                SELECT j.id, j.dataset_revision, j.status, j.error, j.created_at, j.finished_at,
                    j.snapshot -> 'options' AS options
                FROM training_jobs j JOIN training_datasets d ON d.id = j.dataset_id
                WHERE d.id = :id AND d.org_id = :org
                ORDER BY j.created_at DESC, j.id DESC LIMIT 1
            """),
            {"id": dataset_id, "org": member.org_id},
        )
        row = result.mappings().one_or_none()
    if row is None:
        return None
    options = row["options"] or {}
    job = TrainingJob.model_validate(dict(
        row, version_name=options.get("version_name", ""), notes=options.get("notes", ""),
    ))
    if job.status == "succeeded":
        job.evaluation = await run_in_threadpool(read_evaluation, member.org_id, job.id)
    if job.status in {"running", "succeeded"}:
        job.progress = await run_in_threadpool(read_progress, member.org_id, job.id, options.get("epochs"))
    return job


def read_progress(org_id: UUID, job_id: UUID, epochs: int | None) -> TrainingProgress:
    progress = TrainingProgress(phase="preparing", epochs=epochs)
    directory = os.getenv("VI_TRAINING_RUN_DIR")
    if not directory:
        return progress
    root = Path(directory) / str(org_id) / str(job_id)
    if (root / "checking").is_file():
        progress.phase = "checking"
    try:
        with (root / "object-detection" / "results.csv").open() as file:
            for row in csv.DictReader(file, skipinitialspace=True):
                try:
                    epoch = int(row["epoch"])
                    score = float(row["metrics/mAP50-95(B)"])
                    elapsed = float(row["time"])
                except (KeyError, TypeError, ValueError):
                    continue
                if epoch < 1 or not math.isfinite(score) or not math.isfinite(elapsed) or elapsed < 0:
                    continue
                progress.epoch = epoch
                progress.score = max(0, min(score, 1))
                if epochs and epoch >= 2 and progress.phase != "checking":
                    progress.eta_seconds = int(max(0, epochs - epoch) * elapsed / epoch)
    except OSError:
        pass
    if progress.epoch and progress.phase != "checking":
        progress.phase = "learning"
    return progress


def read_evaluation(org_id: UUID, job_id: UUID) -> dict[str, float] | None:
    directory = os.getenv("VI_TRAINING_RUN_DIR")
    if directory is None:
        return None
    try:
        return json.loads((Path(directory) / str(org_id) / str(job_id) / "evaluation.json").read_text())
    except (OSError, ValueError):
        return None


async def completed_checkpoint(dataset_id: UUID, job_id: UUID, member: OrgMember) -> tuple[Path, dict]:
    async with Session() as session:
        snapshot = await session.scalar(
            text("""
                SELECT j.snapshot FROM training_jobs j JOIN training_datasets d ON d.id = j.dataset_id
                WHERE j.id = :job AND d.id = :id AND d.org_id = :org AND j.status = 'succeeded'
            """),
            {"job": job_id, "id": dataset_id, "org": member.org_id},
        )
    directory = os.getenv("VI_TRAINING_RUN_DIR")
    if snapshot is None or not directory:
        raise HTTPException(404, "Trained checkpoint unavailable")
    checkpoint = Path(directory) / str(member.org_id) / str(job_id) / "best.pt"
    if not checkpoint.is_file():
        raise HTTPException(404, "Trained checkpoint unavailable")
    return checkpoint, snapshot


@router.get("/{dataset_id}/jobs", response_model=list[TrainingJob])
async def completed_jobs(dataset_id: UUID, member: OrgMember, response: Response):
    response.headers["Cache-Control"] = "no-store"
    async with Session() as session:
        result = await session.execute(
            text("""
                SELECT j.id, j.dataset_revision, j.status, j.error, j.created_at, j.finished_at, j.snapshot
                FROM training_jobs j JOIN training_datasets d ON d.id = j.dataset_id
                WHERE d.id = :id AND d.org_id = :org AND j.status = 'succeeded'
                ORDER BY j.created_at DESC, j.id DESC
            """),
            {"id": dataset_id, "org": member.org_id},
        )
        rows = list(result.mappings())

    def attach_reports():
        return [
            dict(
                row,
                reference_views=reference_views(row["snapshot"]),
                evaluation=read_evaluation(member.org_id, row["id"]),
                version_name=(row["snapshot"].get("options") or {}).get("version_name", ""),
                notes=(row["snapshot"].get("options") or {}).get("notes", ""),
            )
            for row in rows
        ]

    return await run_in_threadpool(attach_reports)


@router.get("/{dataset_id}/jobs/{job_id}/checkpoint", response_class=FileResponse)
async def download_checkpoint(
    dataset_id: UUID, job_id: UUID, member: OrgMember, variant: Literal["best", "last"] = "best",
):
    checkpoint, _ = await completed_checkpoint(dataset_id, job_id, member)
    if variant == "last":
        checkpoint = checkpoint.parent / "object-detection" / "weights" / "last.pt"
        if not await run_in_threadpool(checkpoint.is_file):
            raise HTTPException(404, "Last checkpoint unavailable.")
    return FileResponse(
        checkpoint,
        filename=f"{variant}.pt",
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/{dataset_id}/jobs/{job_id}/preview")
async def test_trained_model(
    dataset_id: UUID,
    job_id: UUID,
    request: Request,
    member: OrgMember,
    settings: SettingsDependency,
    _: BrowserOrigin,
    confidence: Annotated[float, Query(ge=0.01, le=1)] = 0.5,
    check: bool = False,
    reference: UUID | None = None,
):
    _, snapshot = await completed_checkpoint(dataset_id, job_id, member)
    expected = expected_parts(snapshot, reference) if check else None
    image = await read_jpeg(request)
    try:
        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            result = await client.post(
                f"{settings.inference_url.rstrip('/')}/api/v1/demo/trained-models/"
                f"{member.org_id}/{job_id}/preview",
                params={"confidence": confidence},
                content=image,
                headers={"Content-Type": "image/jpeg"},
            )
            result.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 422:
            raise HTTPException(422, "The model could not read this photo") from exc
        raise HTTPException(503, "Trained model preview unavailable") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Trained model preview unavailable") from exc
    if expected is not None:
        detections = resolve_label_conflicts(snapshot, expected, result.json())
        return JSONResponse(evaluate_parts(expected, detections), headers={"Cache-Control": "no-store"})
    return Response(
        result.content,
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )


def reference_views(snapshot):
    views = {}
    for index, photo in enumerate(snapshot["photos"], start=1):
        counts = Counter(box.get("label") or snapshot["part_name"] for box in photo["boxes"])
        if counts:
            views.setdefault(tuple(sorted(counts.items())), {
                "id": photo["id"],
                "name": photo.get("filename") or f"Training photo {index}",
                "counts": dict(counts),
            })
    return list(views.values())


def expected_parts(snapshot, reference):
    views = reference_views(snapshot)
    if reference is None and len(views) == 1:
        return views[0]["counts"]
    for view in views:
        if str(view["id"]) == str(reference):
            return view["counts"]
    raise HTTPException(422, "Choose the training view that matches the new photo.")


def overlap(first, second, *, containment=False):
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
        detection for detection, bounds, agreement in candidates
        if not (
            agreement < 0.45 and any(
                other_agreement >= 0.45
                and other_agreement - agreement >= 0.20
                and overlap(bounds, other_bounds, containment=True) >= 0.70
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
