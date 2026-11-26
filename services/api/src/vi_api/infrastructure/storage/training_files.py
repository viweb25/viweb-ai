"""Local-disk storage for training photos and trainer run output.

Every path is built from UUIDs and a validated hex digest, and is always
scoped under the organisation's own directory.
"""

import csv
import json
import math
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from anyio import to_thread

from vi_api.domain.errors import Unavailable
from vi_api.domain.training.models import PhotoFile, TrainingProgress
from vi_api.domain.training.ports import CheckpointVariant

RESULTS_CSV = Path("object-detection") / "results.csv"
LAST_CHECKPOINT = Path("object-detection") / "weights" / "last.pt"
SCORE_COLUMN = "metrics/mAP50-95(B)"


class LocalTrainingFileStore:
    def __init__(self, image_dir: str, run_dir: str):
        self.image_root = Path(image_dir) if image_dir else None
        self.run_root = Path(run_dir) if run_dir else None

    async def write_photo(
        self, org_id: UUID, dataset_id: UUID, photo: PhotoFile, image: bytes
    ) -> None:
        path = self._photo_path(org_id, dataset_id, photo)
        await to_thread.run_sync(_write_once, path, image)

    async def photo_path(self, org_id: UUID, dataset_id: UUID, photo: PhotoFile) -> Path | None:
        path = self._photo_path(org_id, dataset_id, photo)
        return path if await to_thread.run_sync(path.is_file) else None

    async def all_photos_exist(
        self, org_id: UUID, dataset_id: UUID, photos: list[PhotoFile]
    ) -> bool:
        paths = [self._photo_path(org_id, dataset_id, photo) for photo in photos]
        return await to_thread.run_sync(lambda: all(path.is_file() for path in paths))

    async def remove_dataset(self, org_id: UUID, dataset_id: UUID, job_ids: list[UUID]) -> None:
        targets = []
        if self.image_root:
            targets.append(self.image_root / str(org_id) / str(dataset_id))
        if self.run_root:
            targets.extend(self.run_root / str(org_id) / str(job_id) for job_id in job_ids)

        def remove():
            for target in targets:
                shutil.rmtree(target, ignore_errors=True)

        await to_thread.run_sync(remove)

    async def read_progress(
        self, org_id: UUID, job_id: UUID, epochs: int | None
    ) -> TrainingProgress:
        if not self.run_root:
            return TrainingProgress(epochs=epochs)
        return await to_thread.run_sync(_read_progress, self._run(org_id, job_id), epochs)

    async def read_evaluation(self, org_id: UUID, job_id: UUID) -> dict[str, float] | None:
        if not self.run_root:
            return None
        return await to_thread.run_sync(_read_json, self._run(org_id, job_id) / "evaluation.json")

    async def checkpoint(
        self, org_id: UUID, job_id: UUID, variant: CheckpointVariant
    ) -> Path | None:
        if not self.run_root:
            return None
        run = self._run(org_id, job_id)
        path = run / "best.pt" if variant == "best" else run / LAST_CHECKPOINT
        return path if await to_thread.run_sync(path.is_file) else None

    def _run(self, org_id: UUID, job_id: UUID) -> Path:
        return self.run_root / str(org_id) / str(job_id)

    def _photo_path(self, org_id: UUID, dataset_id: UUID, photo: PhotoFile) -> Path:
        if not self.image_root:
            raise Unavailable("Training photo storage is unavailable", "storage_unavailable")
        suffix = "jpg" if photo.media_type == "image/jpeg" else "png"
        return (
            self.image_root
            / str(org_id)
            / str(dataset_id)
            / str(photo.id)
            / f"{photo.digest}.{suffix}"
        )


def _write_once(path: Path, image: bytes) -> None:
    """Write atomically. A file named by its digest never needs rewriting."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent) as temporary:
        temporary.write(image)
        temporary.flush()
        os.fsync(temporary.fileno())
        try:
            os.link(temporary.name, path)
        except FileExistsError:
            pass


def _read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _read_progress(root: Path, epochs: int | None) -> TrainingProgress:
    progress = TrainingProgress(phase="preparing", epochs=epochs)
    if (root / "checking").is_file():
        progress.phase = "checking"
    try:
        with (root / RESULTS_CSV).open() as file:
            for row in csv.DictReader(file, skipinitialspace=True):
                try:
                    epoch = int(row["epoch"])
                    score = float(row[SCORE_COLUMN])
                    elapsed = float(row["time"])
                except (KeyError, TypeError, ValueError):
                    continue
                if epoch < 1 or not math.isfinite(score) or not math.isfinite(elapsed):
                    continue
                if elapsed < 0:
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
