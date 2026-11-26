import json
from uuid import UUID

from vi_api.domain.errors import InvalidInput, NotFound
from vi_api.domain.identity.models import Membership
from vi_api.domain.inspection_programs import policies
from vi_api.domain.inspection_programs.models import (
    DatasetContext,
    GoldenLayout,
    Program,
    ProgramDraft,
    ProgramSummary,
)
from vi_api.domain.inspection_programs.ports import ProgramRepository, RunImageStore
from vi_api.domain.training.ports import TrainedModelPreview, TrainingFileStore

PROGRAM_NOT_FOUND = "Inspection program not found"


class ProgramService:
    """Create and edit inspection programs: zones, golden layout and thresholds."""

    def __init__(
        self,
        programs: ProgramRepository,
        files: TrainingFileStore,
        previews: TrainedModelPreview,
        images: RunImageStore,
    ):
        self.programs = programs
        self.files = files
        self.previews = previews
        self.images = images

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

    async def delete(self, member: Membership, program_id: UUID) -> None:
        policies.require_editor(member)
        run_ids = await self.programs.delete(member.org_id, program_id)
        await self.images.remove(member.org_id, run_ids)

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
