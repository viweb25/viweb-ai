"""Local-disk storage for the photo of every inspection run.

Layout: ``<image_dir>/<org_id>/inspection-runs/<run_id>.jpg``. Paths are built only from
UUIDs, so a request can never reach another organisation's files.
"""

from pathlib import Path
from uuid import UUID

from anyio import to_thread

from vi_api.domain.errors import Unavailable
from vi_api.infrastructure.storage.training_files import _write_once

RUNS_FOLDER = "inspection-runs"


class LocalRunImageStore:
    def __init__(self, image_dir: str):
        self.root = Path(image_dir) if image_dir else None

    def _path(self, org_id: UUID, run_id: UUID) -> Path:
        if not self.root:
            raise Unavailable("Inspection photo storage is unavailable", "storage_unavailable")
        return self.root / str(org_id) / RUNS_FOLDER / f"{run_id}.jpg"

    async def write(self, org_id: UUID, run_id: UUID, image: bytes) -> None:
        await to_thread.run_sync(_write_once, self._path(org_id, run_id), image)

    async def path(self, org_id: UUID, run_id: UUID) -> Path | None:
        if not self.root:
            return None
        path = self._path(org_id, run_id)
        return path if await to_thread.run_sync(path.is_file) else None

    async def read(self, org_id: UUID, run_id: UUID) -> bytes | None:
        path = await self.path(org_id, run_id)
        return await to_thread.run_sync(path.read_bytes) if path else None

    async def remove(self, org_id: UUID, run_ids: list[UUID]) -> None:
        if not self.root or not run_ids:
            return
        paths = [self._path(org_id, run_id) for run_id in run_ids]

        def remove():
            for path in paths:
                path.unlink(missing_ok=True)

        await to_thread.run_sync(remove)
