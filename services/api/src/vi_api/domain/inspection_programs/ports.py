from pathlib import Path
from typing import Protocol
from uuid import UUID

from vi_api.domain.inspection_programs.models import (
    DatasetContext,
    JsonObject,
    Program,
    ProgramDraft,
    ProgramSummary,
    ReviewStatus,
    Run,
    RunFilter,
)
from vi_api.domain.training.models import Photo


class ProgramRepository(Protocol):
    async def list_for_org(self, org_id: UUID) -> list[ProgramSummary]: ...

    async def create(self, org_id: UUID, dataset_id: UUID, name: str) -> Program:
        """Raises NotFound when the dataset is not in the organisation."""

    async def get(self, org_id: UUID, program_id: UUID) -> Program | None: ...

    async def save(self, org_id: UUID, program_id: UUID, draft: ProgramDraft) -> int:
        """Replace settings and zones; return the new revision. Raises NotFound or Conflict."""

    async def publication(
        self, org_id: UUID, program_id: UUID, revision: int | None = None
    ) -> tuple[UUID, JsonObject] | None: ...

    async def versions(self, org_id: UUID, program_id: UUID) -> list[int]: ...

    async def activate(
        self, org_id: UUID, program_id: UUID, revision: int,
        model_job_id: UUID | None = None, snapshot: JsonObject | None = None,
    ) -> None: ...

    async def archive(self, org_id: UUID, program_id: UUID) -> None:
        """Archive the program. Raises NotFound."""

    async def dataset_context(self, org_id: UUID, dataset_id: UUID) -> DatasetContext | None: ...

    async def is_completed_job(self, org_id: UUID, dataset_id: UUID, job_id: UUID) -> bool: ...


class RunRepository(Protocol):
    async def add(self, org_id: UUID, run: Run) -> Run:
        """Store a run and return it with its timestamps."""

    async def list_for_org(self, org_id: UUID, filters: RunFilter) -> list[Run]: ...

    async def program_options(self, org_id: UUID) -> list[tuple[UUID, str]]: ...

    async def get(self, org_id: UUID, run_id: UUID) -> Run | None: ...

    async def review(
        self, org_id: UUID, run_id: UUID, user_id: UUID, status: ReviewStatus, note: str
    ) -> bool: ...

    async def send_to_dataset(self, org_id: UUID, run_id: UUID, photo: Photo) -> None:
        """Append the photo to the run's dataset and mark the run as sent, atomically.

        Raises Conflict when it was already sent or the dataset is full.
        """


class RunImageStore(Protocol):
    async def write(self, org_id: UUID, run_id: UUID, image: bytes) -> None: ...

    async def path(self, org_id: UUID, run_id: UUID) -> Path | None: ...

    async def read(self, org_id: UUID, run_id: UUID) -> bytes | None: ...

    async def remove(self, org_id: UUID, run_ids: list[UUID]) -> None: ...
