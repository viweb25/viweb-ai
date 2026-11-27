import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from vi_api.domain.errors import Conflict, NotFound
from vi_api.domain.training.models import JobRecord, JsonObject, StartedJob, TrainingSource
from vi_api.domain.training.ports import SnapshotBuilder

JOB_COLUMNS = "j.id, j.dataset_revision, j.status, j.error, j.created_at, j.finished_at"


class PostgresTrainingJobRepository:
    def __init__(self, sessions: async_sessionmaker):
        self.sessions = sessions

    async def start(
        self, org_id: UUID, dataset_id: UUID, revision: int, build_snapshot: SnapshotBuilder
    ) -> StartedJob:
        ids = {"id": dataset_id, "org": org_id}
        async with self.sessions.begin() as session:
            result = await session.execute(
                text("""
                    SELECT part_name, revision, classes FROM training_datasets
                    WHERE id = :id AND org_id = :org AND archived_at IS NULL FOR UPDATE
                """),
                ids,
            )
            dataset = result.mappings().one_or_none()
            if dataset is None:
                raise NotFound("Dataset not found", "dataset_not_found")
            if dataset["revision"] != revision:
                raise Conflict("Open the latest saved version before training.", "stale_revision")
            active = await session.execute(
                text(f"""
                    SELECT {JOB_COLUMNS} FROM training_jobs j
                    WHERE j.dataset_id = :id AND j.status IN ('queued', 'running')
                """),
                ids,
            )
            job = active.mappings().one_or_none()
            if job is not None:
                if job["dataset_revision"] != revision:
                    raise Conflict("An earlier revision is still training.", "training_active")
                return StartedJob(JobRecord(**job), created=False)
            result = await session.execute(
                text("""
                    SELECT id, filename, digest, media_type, reviewed, boxes FROM training_photos
                    WHERE dataset_id = :id ORDER BY position
                """),
                ids,
            )
            photos = [dict(photo) for photo in result.mappings()]
            snapshot = build_snapshot(TrainingSource(**dataset), photos)
            inserted = await session.execute(
                text("""
                    INSERT INTO training_jobs (dataset_id, dataset_revision, snapshot)
                    VALUES (:id, :revision, CAST(:snapshot AS jsonb))
                    RETURNING id, dataset_revision, status, error, created_at, finished_at
                """),
                {
                    "id": dataset_id,
                    "revision": revision,
                    "snapshot": json.dumps(snapshot, default=str),
                },
            )
            return StartedJob(JobRecord(**inserted.mappings().one()), created=True)

    async def cancel(self, org_id: UUID, dataset_id: UUID, job_id: UUID) -> bool:
        async with self.sessions.begin() as session:
            stopped = await session.scalar(
                text("""
                    UPDATE training_jobs j SET status = 'cancelled', finished_at = now()
                    FROM training_datasets d
                    WHERE j.id = :job AND j.dataset_id = d.id AND d.id = :id AND d.org_id = :org
                        AND d.archived_at IS NULL AND j.status IN ('queued', 'running')
                    RETURNING j.id
                """),
                {"job": job_id, "id": dataset_id, "org": org_id},
            )
        return stopped is not None

    async def latest(self, org_id: UUID, dataset_id: UUID) -> JobRecord | None:
        async with self.sessions() as session:
            result = await session.execute(
                text(f"""
                    SELECT {JOB_COLUMNS}, j.snapshot -> 'options' AS options
                    FROM training_jobs j JOIN training_datasets d ON d.id = j.dataset_id
                    WHERE d.id = :id AND d.org_id = :org AND d.archived_at IS NULL
                    ORDER BY j.created_at DESC, j.id DESC LIMIT 1
                """),
                {"id": dataset_id, "org": org_id},
            )
            row = result.mappings().one_or_none()
        return JobRecord(**row) if row else None

    async def completed(self, org_id: UUID, dataset_id: UUID) -> list[JobRecord]:
        async with self.sessions() as session:
            result = await session.execute(
                text(f"""
                    SELECT {JOB_COLUMNS}, j.snapshot
                    FROM training_jobs j JOIN training_datasets d ON d.id = j.dataset_id
                    WHERE d.id = :id AND d.org_id = :org AND d.archived_at IS NULL
                      AND j.status = 'succeeded'
                    ORDER BY j.created_at DESC, j.id DESC
                """),
                {"id": dataset_id, "org": org_id},
            )
            return [JobRecord(**row) for row in result.mappings()]

    async def completed_snapshot(
        self, org_id: UUID, dataset_id: UUID, job_id: UUID
    ) -> JsonObject | None:
        async with self.sessions() as session:
            return await session.scalar(
                text("""
                    SELECT j.snapshot FROM training_jobs j
                    JOIN training_datasets d ON d.id = j.dataset_id
                    WHERE j.id = :job AND d.id = :id AND d.org_id = :org
                        AND d.archived_at IS NULL
                      AND j.status = 'succeeded'
                """),
                {"job": job_id, "id": dataset_id, "org": org_id},
            )
