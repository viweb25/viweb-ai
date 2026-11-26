import json
from pathlib import Path
from uuid import UUID

from vi_api.domain.errors import Conflict, NotFound
from vi_api.domain.identity.models import Membership
from vi_api.domain.training import policies
from vi_api.domain.training.models import JobView, JsonObject
from vi_api.domain.training.ports import (
    CheckpointVariant,
    TrainedModelPreview,
    TrainingFileStore,
    TrainingJobRepository,
)

CHECKPOINT_UNAVAILABLE = "Trained checkpoint unavailable"


class TrainingJobService:
    """Start, follow, download and test training runs."""

    def __init__(
        self,
        jobs: TrainingJobRepository,
        files: TrainingFileStore,
        previews: TrainedModelPreview,
    ):
        self.jobs = jobs
        self.files = files
        self.previews = previews

    async def start(
        self,
        member: Membership,
        dataset_id: UUID,
        revision: int,
        options: JsonObject | None,
    ) -> JobView:
        policies.require_editor(member)
        started = await self.jobs.start(
            member.org_id,
            dataset_id,
            revision,
            lambda source, photos: policies.build_snapshot(member.org_id, source, photos, options),
        )
        if not started.created:
            return JobView.from_record(started.job)
        return JobView.from_record(
            started.job,
            version_name=(options or {}).get("version_name", ""),
            notes=(options or {}).get("notes", ""),
            options=options,
        )

    async def cancel(self, member: Membership, dataset_id: UUID, job_id: UUID) -> None:
        policies.require_editor(member)
        if not await self.jobs.cancel(member.org_id, dataset_id, job_id):
            raise Conflict("This training run is no longer active.", "training_not_active")

    async def latest(self, member: Membership, dataset_id: UUID) -> JobView | None:
        record = await self.jobs.latest(member.org_id, dataset_id)
        if record is None:
            return None
        options = record.options or {}
        view = JobView.from_record(
            record,
            version_name=options.get("version_name", ""),
            notes=options.get("notes", ""),
            options=record.options,
        )
        if view.status == "succeeded":
            view.evaluation = await self.files.read_evaluation(member.org_id, record.id)
        if view.status in {"running", "succeeded"}:
            view.progress = await self.files.read_progress(
                member.org_id, record.id, options.get("epochs")
            )
        return view

    async def completed(self, member: Membership, dataset_id: UUID) -> list[JobView]:
        views = []
        for record in await self.jobs.completed(member.org_id, dataset_id):
            snapshot = record.snapshot or {}
            options = snapshot.get("options") or {}
            views.append(
                JobView.from_record(
                    record,
                    reference_views=policies.reference_views(snapshot),
                    evaluation=await self.files.read_evaluation(member.org_id, record.id),
                    version_name=options.get("version_name", ""),
                    notes=options.get("notes", ""),
                )
            )
        return views

    async def checkpoint(
        self, member: Membership, dataset_id: UUID, job_id: UUID, variant: CheckpointVariant
    ) -> Path:
        await self._completed_snapshot(member, dataset_id, job_id)
        if variant == "best":
            path = await self.files.checkpoint(member.org_id, job_id, "best")
            if path is None:
                raise NotFound(CHECKPOINT_UNAVAILABLE, "checkpoint_unavailable")
            return path
        path = await self.files.checkpoint(member.org_id, job_id, "last")
        if path is None:
            raise NotFound("Last checkpoint unavailable.", "checkpoint_unavailable")
        return path

    async def preview(
        self,
        member: Membership,
        dataset_id: UUID,
        job_id: UUID,
        image: bytes,
        confidence: float,
        check: bool,
        reference: UUID | None,
    ) -> JsonObject | bytes:
        """Run a trained model on a photo.

        With ``check``, return a PASS/FAIL decision against the chosen training
        view. Otherwise return the raw detections JSON.
        """
        snapshot = await self._completed_snapshot(member, dataset_id, job_id)
        expected = policies.expected_parts(snapshot, reference) if check else None
        content = await self.previews.preview(member.org_id, job_id, image, confidence)
        if expected is None:
            return content
        detections = policies.resolve_label_conflicts(snapshot, expected, json.loads(content))
        return policies.evaluate_parts(expected, detections)

    async def _completed_snapshot(
        self, member: Membership, dataset_id: UUID, job_id: UUID
    ) -> JsonObject:
        snapshot = await self.jobs.completed_snapshot(member.org_id, dataset_id, job_id)
        if snapshot is None or await self.files.checkpoint(member.org_id, job_id, "best") is None:
            raise NotFound(CHECKPOINT_UNAVAILABLE, "checkpoint_unavailable")
        return snapshot
