import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vi_api.domain.errors import Conflict, NotFound
from vi_api.domain.training.models import (
    Dataset,
    DatasetDraft,
    DatasetSummary,
    DatasetWithPhotos,
    Photo,
    PhotoFile,
)

DATASET_NOT_FOUND = "Dataset not found"


class PostgresDatasetRepository:
    def __init__(self, sessions: async_sessionmaker):
        self.sessions = sessions

    async def list_for_org(self, org_id: UUID) -> list[DatasetSummary]:
        async with self.sessions() as session:
            rows = await session.execute(
                text("""
                    SELECT d.id, d.part_name, d.classes, d.class_info, d.updated_at,
                        (SELECT count(*) FROM training_photos p
                            WHERE p.dataset_id = d.id) AS photo_count,
                        (SELECT count(*) FROM training_photos p
                            WHERE p.dataset_id = d.id AND p.reviewed) AS labeled_count,
                        (SELECT count(*) FROM training_jobs j
                            WHERE j.dataset_id = d.id AND j.status = 'succeeded') AS model_count,
                        (SELECT j.status FROM training_jobs j WHERE j.dataset_id = d.id
                            ORDER BY j.created_at DESC, j.id DESC LIMIT 1) AS latest_status
                    FROM training_datasets d WHERE d.org_id = :org_id AND d.archived_at IS NULL
                    ORDER BY d.updated_at DESC, d.id
                """),
                {"org_id": org_id},
            )
            return [DatasetSummary(**row) for row in rows.mappings()]

    async def open(self, org_id: UUID, dataset_id: UUID) -> DatasetWithPhotos | None:
        async with self.sessions.begin() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            dataset = await self._find(session, org_id, dataset_id)
            if dataset is None:
                return None
            rows = await session.execute(
                text("""
                    SELECT id, filename, media_type, digest, reviewed, boxes FROM training_photos
                    WHERE dataset_id = :id ORDER BY position
                """),
                {"id": dataset_id},
            )
            return DatasetWithPhotos(dataset, [Photo(**row) for row in rows.mappings()])

    async def save(self, org_id: UUID, dataset_id: UUID, draft: DatasetDraft) -> int:
        values = {
            "id": dataset_id,
            "org_id": org_id,
            "part": draft.part_name,
            "note": draft.inspection_note,
            "revision": draft.revision,
            "classes": json.dumps(draft.classes) if draft.classes is not None else None,
            "class_info": json.dumps(draft.class_info) if draft.class_info is not None else None,
        }
        if draft.revision == 0:
            statement = """
                INSERT INTO training_datasets
                    (id, org_id, part_name, inspection_note, classes, class_info)
                VALUES (:id, :org_id, :part, :note,
                    COALESCE(CAST(:classes AS jsonb), '[]'::jsonb),
                    COALESCE(CAST(:class_info AS jsonb), '{}'::jsonb))
                ON CONFLICT (id) DO NOTHING RETURNING revision
            """
        else:
            statement = """
                UPDATE training_datasets SET part_name = :part, inspection_note = :note,
                    classes = COALESCE(CAST(:classes AS jsonb), classes),
                    class_info = COALESCE(CAST(:class_info AS jsonb), class_info),
                    revision = revision + 1, updated_at = now()
                WHERE id = :id AND org_id = :org_id AND archived_at IS NULL AND revision = :revision
                RETURNING revision
            """
        async with self.sessions.begin() as session:
            revision = await session.scalar(text(statement), values)
            if revision is None:
                if await self._find(session, org_id, dataset_id) is None:
                    raise NotFound(DATASET_NOT_FOUND, "dataset_not_found")
                raise Conflict(
                    "A newer saved version exists. Reopen the dataset first.", "stale_revision"
                )
            await session.execute(
                text("DELETE FROM training_photos WHERE dataset_id = :id"), {"id": dataset_id}
            )
            if draft.photos:
                await session.execute(
                    text("""
                        INSERT INTO training_photos
                            (dataset_id, id, filename, media_type, digest, reviewed, boxes,
                             position)
                        VALUES (:dataset_id, :id, :filename, :media_type, :digest,
                            :reviewed, CAST(:boxes AS jsonb), :position)
                    """),
                    [
                        {
                            "dataset_id": dataset_id,
                            "id": photo.id,
                            "filename": photo.filename,
                            "media_type": photo.media_type,
                            "digest": photo.digest,
                            "reviewed": photo.reviewed,
                            "boxes": json.dumps(photo.boxes),
                            "position": position,
                        }
                        for position, photo in enumerate(draft.photos)
                    ],
                )
        return revision

    async def archive_idle(self, org_id: UUID, dataset_id: UUID) -> None:
        async with self.sessions.begin() as session:
            dataset = await session.scalar(
                text("""
                    SELECT id FROM training_datasets WHERE id = :id AND org_id = :org FOR UPDATE
                """),
                {"id": dataset_id, "org": org_id},
            )
            if dataset is None:
                raise NotFound(DATASET_NOT_FOUND, "dataset_not_found")
            active = await session.scalar(
                text("""
                    SELECT 1 FROM training_jobs WHERE dataset_id = :id
                    AND status IN ('queued', 'running') LIMIT 1
                """),
                {"id": dataset_id},
            )
            if active:
                raise Conflict(
                    "Stop the running training before archiving this project.", "training_active"
                )
            await session.execute(
                text("""
                    UPDATE training_datasets SET archived_at = COALESCE(archived_at, now())
                    WHERE id = :id
                """),
                {"id": dataset_id},
            )

    async def find_photo(
        self, org_id: UUID, dataset_id: UUID, photo_id: UUID
    ) -> PhotoFile | None:
        async with self.sessions() as session:
            result = await session.execute(
                text("""
                    SELECT p.id, p.digest, p.media_type FROM training_photos p
                    JOIN training_datasets d ON d.id = p.dataset_id
                    WHERE d.org_id = :org_id AND d.archived_at IS NULL
                      AND d.id = :dataset_id AND p.id = :photo_id
                """),
                {"org_id": org_id, "dataset_id": dataset_id, "photo_id": photo_id},
            )
            row = result.mappings().one_or_none()
        return PhotoFile(**row) if row else None

    @staticmethod
    async def _find(session: AsyncSession, org_id: UUID, dataset_id: UUID) -> Dataset | None:
        row = await session.execute(
            text("""
                SELECT id, part_name, inspection_note, revision, classes, class_info
                FROM training_datasets WHERE id = :id AND org_id = :org_id AND archived_at IS NULL
            """),
            {"id": dataset_id, "org_id": org_id},
        )
        found = row.mappings().one_or_none()
        return Dataset(**found) if found else None
