import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from uuid import UUID, uuid4

from vi_api.domain.errors import Conflict, InvalidInput, NotFound
from vi_api.domain.identity.models import Membership
from vi_api.domain.inspection_programs import policies
from vi_api.domain.inspection_programs.models import ReviewStatus, Run, RunFilter
from vi_api.domain.inspection_programs.ports import ProgramRepository, RunImageStore, RunRepository
from vi_api.domain.training.models import Photo, PhotoFile
from vi_api.domain.training.ports import TrainedModelPreview, TrainingFileStore

RUN_NOT_FOUND = "Inspection result not found"


def _json_ready(value):
    """Dataclass → JSON-compatible dict (UUIDs become strings)."""
    return json.loads(json.dumps(value, default=str))


class RunService:
    """Inspect boards with a program, keep the result log, and feed mistakes back."""

    def __init__(
        self,
        programs: ProgramRepository,
        runs: RunRepository,
        images: RunImageStore,
        files: TrainingFileStore,
        previews: TrainedModelPreview,
    ):
        self.programs = programs
        self.runs = runs
        self.images = images
        self.files = files
        self.previews = previews

    async def inspect(
        self, member: Membership, user_id: UUID, program_id: UUID, image: bytes
    ) -> Run:
        policies.require_inspector(member)
        program = await self.programs.get(member.org_id, program_id)
        if program is None:
            raise NotFound("Inspection program not found", "program_not_found")
        if program.model_job_id is None:
            raise InvalidInput("Choose a trained model for this program first.", "model_required")
        if await self.files.checkpoint(member.org_id, program.model_job_id, "best") is None:
            raise InvalidInput("The program's model is no longer available.", "model_unavailable")
        context = await self.programs.dataset_context(member.org_id, program.dataset_id)
        defect_classes = context.defect_classes if context else frozenset()

        floor = policies.detection_floor(program.confidence, program.review_margin)
        content = await self.previews.preview(member.org_id, program.model_job_id, image, floor)
        detections = policies.parse_detections(json.loads(content))
        evaluation = policies.evaluate(
            program.zones, detections, program.confidence, program.review_margin, defect_classes
        )

        run_id = uuid4()
        await self.images.write(member.org_id, run_id, image)
        run = Run(
            id=run_id,
            program_id=program.id,
            model_job_id=program.model_job_id,
            decision=evaluation.decision,
            zone_results=_json_ready([asdict(result) for result in evaluation.zones]),
            detections=_json_ready([asdict(detection) for detection in detections]),
            confidence=program.confidence,
            image_digest=hashlib.sha256(image).hexdigest(),
            created_by=user_id,
            review_status=policies.initial_review_status(evaluation.decision),
            program_name=program.name,
            dataset_id=program.dataset_id,
        )
        return await self.runs.add(member.org_id, run)

    async def list_runs(self, member: Membership, filters: RunFilter) -> list[Run]:
        return await self.runs.list_for_org(member.org_id, filters)

    async def get(self, member: Membership, run_id: UUID) -> Run:
        run = await self.runs.get(member.org_id, run_id)
        if run is None:
            raise NotFound(RUN_NOT_FOUND, "run_not_found")
        return run

    async def image_path(self, member: Membership, run_id: UUID) -> Path:
        await self.get(member, run_id)
        path = await self.images.path(member.org_id, run_id)
        if path is None:
            raise NotFound("The photo of this result is no longer stored.", "run_image_unavailable")
        return path

    async def review(
        self, member: Membership, user_id: UUID, run_id: UUID, status: ReviewStatus, note: str
    ) -> None:
        """Record a person's verdict: ``confirmed`` (model right) or ``corrected`` (model wrong)."""
        policies.require_inspector(member)
        if status not in ("confirmed", "corrected", "pending"):
            raise InvalidInput("Choose confirmed, corrected or pending.", "invalid_review")
        if not await self.runs.review(member.org_id, run_id, user_id, status, note.strip()[:400]):
            raise NotFound(RUN_NOT_FOUND, "run_not_found")

    async def send_to_dataset(self, member: Membership, run_id: UUID) -> UUID:
        """Add the run's photo to its project as a new photo to label, with suggested boxes.

        Returns the new photo ID. The photo is unreviewed, so the Label step asks a person
        to check the suggested boxes before the next training.
        """
        policies.require_editor(member)
        run = await self.get(member, run_id)
        if run.sent_to_dataset_at is not None:
            raise Conflict("This photo is already in the project.", "already_sent")
        if run.dataset_id is None:
            raise NotFound("The program's project no longer exists.", "dataset_not_found")
        context = await self.programs.dataset_context(member.org_id, run.dataset_id)
        if context is None:
            raise NotFound("The program's project no longer exists.", "dataset_not_found")
        image = await self.images.read(member.org_id, run_id)
        if image is None:
            raise NotFound("The photo of this result is no longer stored.", "run_image_unavailable")
        photo_id = uuid4()
        await self.files.write_photo(
            member.org_id,
            run.dataset_id,
            PhotoFile(photo_id, run.image_digest, "image/jpeg"),
            image,
        )
        stamp = run.created_at.strftime("%Y%m%d-%H%M%S") if run.created_at else str(run_id)[:8]
        photo = Photo(
            id=photo_id,
            filename=f"inspection-{stamp}.jpg",
            media_type="image/jpeg",
            digest=run.image_digest,
            reviewed=False,
            boxes=policies.suggested_boxes(run.detections, run.confidence, context.classes),
        )
        await self.runs.send_to_dataset(member.org_id, run_id, photo)
        return photo_id
