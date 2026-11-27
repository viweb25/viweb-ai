import json
from uuid import UUID

from vi_api.domain.errors import Conflict, InvalidInput, NotFound, PermissionDenied
from vi_api.domain.identity.models import Membership
from vi_api.domain.inspection_programs import policies
from vi_api.domain.inspection_programs.models import (
    DatasetContext,
    GoldenLayout,
    Program,
    ProgramDraft,
    ProgramSummary,
    program_snapshot,
)
from vi_api.domain.inspection_programs.ports import ProgramRepository
from vi_api.domain.training.ports import TrainedModelPreview, TrainingFileStore

PROGRAM_NOT_FOUND = "Inspection program not found"


class ProgramService:
    """Create and edit inspection programs: zones, golden layout and thresholds."""

    def __init__(
        self,
        programs: ProgramRepository,
        files: TrainingFileStore,
        previews: TrainedModelPreview,
    ):
        self.programs = programs
        self.files = files
        self.previews = previews

    async def list_programs(self, member: Membership) -> list[ProgramSummary]:
        return await self.programs.list_for_org(member.org_id)

    async def create(
        self, member: Membership, dataset_id: UUID, name: str
    ) -> tuple[Program, DatasetContext]:
        """Create an empty program for a project; return it with the project's classes."""
        policies.require_editor(member)
        if not name.strip():
            raise InvalidInput("Give the program a name.", "invalid_program")
        program = await self.programs.create(member.org_id, dataset_id, name.strip())
        return program, await self.classes(member, program)

    async def get(self, member: Membership, program_id: UUID) -> Program:
        program = await self.programs.get(member.org_id, program_id)
        if program is None:
            raise NotFound(PROGRAM_NOT_FOUND, "program_not_found")
        return program

    async def open(self, member: Membership, program_id: UUID) -> tuple[Program, DatasetContext]:
        """The program with its project's classes, for the editor."""
        program = await self.get(member, program_id)
        return program, await self.classes(member, program)

    async def classes(self, member: Membership, program: Program) -> DatasetContext:
        context = await self.programs.dataset_context(member.org_id, program.dataset_id)
        if context is None:
            raise NotFound("The program's project no longer exists.", "dataset_not_found")
        return context

    async def save(self, member: Membership, program_id: UUID, draft: ProgramDraft) -> int:
        policies.require_editor(member)
        program = await self.get(member, program_id)
        context = await self.classes(member, program)
        policies.check_draft(draft, context.classes)
        if draft.model_job_id is not None:
            await self._require_model(member, program.dataset_id, draft.model_job_id)
        return await self.programs.save(member.org_id, program_id, draft)

    async def versions(self, member: Membership, program_id: UUID) -> list[int]:
        await self.get(member, program_id)
        return await self.programs.versions(member.org_id, program_id)

    async def publish(self, member: Membership, program_id: UUID, revision: int) -> None:
        self._require_publisher(member)
        program, context = await self.open(member, program_id)
        if program.revision != revision:
            raise Conflict("Reopen the latest draft before publishing.", "stale_revision")
        if program.model_job_id is None or not any(zone.expected for zone in program.zones):
            raise InvalidInput("Choose a model and set expected counts before publishing.")
        policies.check_draft(
            ProgramDraft(
                program.name, program.model_job_id, program.confidence, program.review_margin,
                program.revision, program.zones,
            ),
            context.classes,
        )
        await self._require_model(member, program.dataset_id, program.model_job_id)
        await self.programs.activate(
            member.org_id, program_id, revision, program.model_job_id,
            program_snapshot(program, context),
        )

    async def rollback(self, member: Membership, program_id: UUID, revision: int) -> None:
        self._require_publisher(member)
        program = await self.get(member, program_id)
        published = await self.programs.publication(member.org_id, program_id, revision)
        if published is None:
            raise NotFound("Published revision not found.", "version_not_found")
        await self._require_model(member, program.dataset_id, published[0])
        await self.programs.activate(member.org_id, program_id, revision)

    @staticmethod
    def _require_publisher(member: Membership) -> None:
        if member.role not in ("owner", "admin"):
            raise PermissionDenied(
                "Only workspace owners and admins can publish inspection programs"
            )

    async def delete(self, member: Membership, program_id: UUID) -> None:
        policies.require_editor(member)
        await self.programs.archive(member.org_id, program_id)

    async def capture_golden(
        self, member: Membership, program_id: UUID, image: bytes
    ) -> GoldenLayout:
        """Run the program's model on a known-good board and propose expected counts per zone.

        Uses the saved zones and model. Nothing is stored: the editor shows the proposal and
        the person saves it.
        """
        policies.require_editor(member)
        program = await self.get(member, program_id)
        if program.model_job_id is None:
            raise InvalidInput("Choose a trained model first.", "model_required")
        await self._require_model(member, program.dataset_id, program.model_job_id)
        content = await self.previews.preview(
            member.org_id, program.model_job_id, image, program.confidence
        )
        detections = policies.parse_detections(json.loads(content))
        context = await self.classes(member, program)
        return policies.golden_layout(
            program.zones, detections, program.confidence, context.classes
        )

    async def _require_model(self, member: Membership, dataset_id: UUID, job_id: UUID) -> None:
        completed = await self.programs.is_completed_job(member.org_id, dataset_id, job_id)
        if not completed or await self.files.checkpoint(member.org_id, job_id, "best") is None:
            raise InvalidInput("Choose a finished model of this project.", "model_unavailable")
