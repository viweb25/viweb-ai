"""PostgreSQL storage for inspection programs, zones and runs.

Every query is scoped by ``org_id``. Writes that touch several rows run in one transaction.
"""

import json
from dataclasses import replace
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vi_api.domain.errors import Conflict, NotFound
from vi_api.domain.inspection_programs.models import (
    DatasetContext,
    Program,
    ProgramDraft,
    ProgramSummary,
    Region,
    ReviewStatus,
    Run,
    RunFilter,
    Zone,
)
from vi_api.domain.training.models import Photo

PROGRAM_NOT_FOUND = "Inspection program not found"
MAX_DATASET_PHOTOS = 200

PROGRAM_COLUMNS = """
    p.id, p.name, p.dataset_id, p.model_job_id, p.confidence, p.review_margin, p.revision,
    p.updated_at
"""
RUN_COLUMNS = """
    r.id, r.program_id, r.model_job_id, r.decision, r.zone_results, r.detections, r.confidence,
    r.image_digest, r.created_by, r.review_status, r.created_at, p.name AS program_name,
    p.dataset_id, r.review_note, r.reviewed_at, r.sent_to_dataset_at
"""


def _zone(row: Any) -> Zone:
    return Zone(
        id=row["id"],
        name=row["name"],
        region=Region(row["x1"], row["y1"], row["x2"], row["y2"]),
        expected={label: int(count) for label, count in (row["expected"] or {}).items()},
        critical=row["critical"],
    )


class PostgresProgramRepository:
    def __init__(self, sessions: async_sessionmaker):
        self.sessions = sessions

    async def list_for_org(self, org_id: UUID) -> list[ProgramSummary]:
        async with self.sessions() as session:
            rows = await session.execute(
                text("""
                    SELECT p.id, p.name, p.dataset_id, d.part_name AS dataset_name,
                        p.model_job_id, p.updated_at,
                        (SELECT count(*) FROM inspection_zones z
                            WHERE z.program_id = p.id) AS zone_count,
                        r.run_count, r.pass_count, r.pending_reviews, r.last_run_at
                    FROM inspection_programs p
                    JOIN training_datasets d ON d.id = p.dataset_id
                    LEFT JOIN LATERAL (
                        SELECT count(*) AS run_count,
                            count(*) FILTER (WHERE decision = 'PASS') AS pass_count,
                            count(*) FILTER (WHERE review_status = 'pending') AS pending_reviews,
                            max(created_at) AS last_run_at
                        FROM inspection_runs WHERE program_id = p.id
                    ) r ON true
                    WHERE p.org_id = :org_id
                    ORDER BY p.updated_at DESC, p.id
                """),
                {"org_id": org_id},
            )
            return [ProgramSummary(**row) for row in rows.mappings()]

    async def create(self, org_id: UUID, dataset_id: UUID, name: str) -> Program:
        async with self.sessions.begin() as session:
            program_id = await session.scalar(
                text("""
                    INSERT INTO inspection_programs (org_id, dataset_id, name)
                    SELECT :org_id, d.id, :name FROM training_datasets d
                    WHERE d.id = :dataset_id AND d.org_id = :org_id
                    RETURNING id
                """),
                {"org_id": org_id, "dataset_id": dataset_id, "name": name},
            )
            if program_id is None:
                raise NotFound("Project not found", "dataset_not_found")
            program = await self._find(session, org_id, program_id)
        assert program is not None
        return program

    async def get(self, org_id: UUID, program_id: UUID) -> Program | None:
        async with self.sessions() as session:
            return await self._find(session, org_id, program_id)

    async def save(self, org_id: UUID, program_id: UUID, draft: ProgramDraft) -> int:
        async with self.sessions.begin() as session:
            revision = await session.scalar(
                text("""
                    UPDATE inspection_programs SET name = :name, model_job_id = :model_job_id,
                        confidence = :confidence, review_margin = :review_margin,
                        revision = revision + 1, updated_at = now()
                    WHERE id = :id AND org_id = :org_id AND revision = :revision
                    RETURNING revision
                """),
                {
                    "id": program_id,
                    "org_id": org_id,
                    "name": draft.name.strip(),
                    "model_job_id": draft.model_job_id,
                    "confidence": draft.confidence,
                    "review_margin": draft.review_margin,
                    "revision": draft.revision,
                },
            )
            if revision is None:
                if await self._find(session, org_id, program_id) is None:
                    raise NotFound(PROGRAM_NOT_FOUND, "program_not_found")
                raise Conflict(
                    "Someone saved this program in the meantime. Reload it first.", "stale_revision"
                )
            await session.execute(
                text("DELETE FROM inspection_zones WHERE program_id = :id"), {"id": program_id}
            )
            if draft.zones:
                await session.execute(
                    text("""
                        INSERT INTO inspection_zones
                            (program_id, id, name, position, x1, y1, x2, y2, expected, critical)
                        VALUES (:program_id, :id, :name, :position, :x1, :y1, :x2, :y2,
                            CAST(:expected AS jsonb), :critical)
                    """),
                    [
                        {
                            "program_id": program_id,
                            "id": zone.id,
                            "name": zone.name.strip(),
                            "position": position,
                            "x1": zone.region.x1,
                            "y1": zone.region.y1,
                            "x2": zone.region.x2,
                            "y2": zone.region.y2,
                            "expected": json.dumps(zone.expected),
                            "critical": zone.critical,
                        }
                        for position, zone in enumerate(draft.zones)
                    ],
                )
        return revision

    async def delete(self, org_id: UUID, program_id: UUID) -> list[UUID]:
        async with self.sessions.begin() as session:
            found = await session.scalar(
                text("""
                    SELECT id FROM inspection_programs
                    WHERE id = :id AND org_id = :org_id FOR UPDATE
                """),
                {"id": program_id, "org_id": org_id},
            )
            if found is None:
                raise NotFound(PROGRAM_NOT_FOUND, "program_not_found")
            run_ids = await session.scalars(
                text("SELECT id FROM inspection_runs WHERE program_id = :id"), {"id": program_id}
            )
            deleted = list(run_ids)
            await session.execute(
                text("DELETE FROM inspection_programs WHERE id = :id"), {"id": program_id}
            )
        return deleted

    async def dataset_context(self, org_id: UUID, dataset_id: UUID) -> DatasetContext | None:
        async with self.sessions() as session:
            result = await session.execute(
                text("""
                    SELECT part_name, classes, class_info FROM training_datasets
                    WHERE id = :id AND org_id = :org_id
                """),
                {"id": dataset_id, "org_id": org_id},
            )
            row = result.mappings().one_or_none()
        if row is None:
            return None
        info = row["class_info"] or {}
        return DatasetContext(
            part_name=row["part_name"],
            classes=list(row["classes"] or []) or [row["part_name"]],
            defect_classes=frozenset(
                label for label, value in info.items() if (value or {}).get("kind") == "defect"
            ),
        )

    async def is_completed_job(self, org_id: UUID, dataset_id: UUID, job_id: UUID) -> bool:
        async with self.sessions() as session:
            found = await session.scalar(
                text("""
                    SELECT 1 FROM training_jobs j
                    JOIN training_datasets d ON d.id = j.dataset_id
                    WHERE j.id = :job_id AND j.dataset_id = :dataset_id
                      AND d.org_id = :org_id AND j.status = 'succeeded'
                """),
                {"job_id": job_id, "dataset_id": dataset_id, "org_id": org_id},
            )
        return found is not None

    @staticmethod
    async def _find(session: AsyncSession, org_id: UUID, program_id: UUID) -> Program | None:
        result = await session.execute(
            text(
                f"SELECT {PROGRAM_COLUMNS} FROM inspection_programs p "
                "WHERE p.id = :id AND p.org_id = :org_id"
            ),
            {"id": program_id, "org_id": org_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        zones = await session.execute(
            text("""
                SELECT id, name, x1, y1, x2, y2, expected, critical FROM inspection_zones
                WHERE program_id = :id ORDER BY position
            """),
            {"id": program_id},
        )
        return Program(**row, zones=[_zone(zone) for zone in zones.mappings()])


class PostgresRunRepository:
    def __init__(self, sessions: async_sessionmaker):
        self.sessions = sessions

    async def add(self, org_id: UUID, run: Run) -> Run:
        async with self.sessions.begin() as session:
            created_at = await session.scalar(
                text("""
                    INSERT INTO inspection_runs
                        (id, org_id, program_id, model_job_id, decision, zone_results,
                         detections, confidence, image_digest, created_by, review_status)
                    SELECT :id, :org_id, p.id, :model_job_id, :decision,
                        CAST(:zone_results AS jsonb), CAST(:detections AS jsonb), :confidence,
                        :image_digest, :created_by, :review_status
                    FROM inspection_programs p WHERE p.id = :program_id AND p.org_id = :org_id
                    RETURNING created_at
                """),
                {
                    "id": run.id,
                    "org_id": org_id,
                    "program_id": run.program_id,
                    "model_job_id": run.model_job_id,
                    "decision": run.decision,
                    "zone_results": json.dumps(run.zone_results),
                    "detections": json.dumps(run.detections),
                    "confidence": run.confidence,
                    "image_digest": run.image_digest,
                    "created_by": run.created_by,
                    "review_status": run.review_status,
                },
            )
        if created_at is None:
            raise NotFound(PROGRAM_NOT_FOUND, "program_not_found")
        return replace(run, created_at=created_at)

    async def list_for_org(self, org_id: UUID, filters: RunFilter) -> list[Run]:
        async with self.sessions() as session:
            rows = await session.execute(
                text(f"""
                    SELECT {RUN_COLUMNS}
                    FROM inspection_runs r JOIN inspection_programs p ON p.id = r.program_id
                    WHERE r.org_id = :org_id
                      AND (CAST(:program_id AS uuid) IS NULL OR r.program_id = :program_id)
                      AND (CAST(:decision AS text) IS NULL OR r.decision = :decision)
                      AND (CAST(:review_status AS text) IS NULL
                           OR r.review_status = :review_status)
                    ORDER BY r.created_at DESC, r.id DESC
                    LIMIT :limit
                """),
                {
                    "org_id": org_id,
                    "program_id": filters.program_id,
                    "decision": filters.decision,
                    "review_status": filters.review_status,
                    "limit": filters.limit,
                },
            )
            return [Run(**row) for row in rows.mappings()]

    async def get(self, org_id: UUID, run_id: UUID) -> Run | None:
        async with self.sessions() as session:
            result = await session.execute(
                text(f"""
                    SELECT {RUN_COLUMNS}
                    FROM inspection_runs r JOIN inspection_programs p ON p.id = r.program_id
                    WHERE r.id = :id AND r.org_id = :org_id
                """),
                {"id": run_id, "org_id": org_id},
            )
            row = result.mappings().one_or_none()
        return Run(**row) if row else None

    async def review(
        self, org_id: UUID, run_id: UUID, user_id: UUID, status: ReviewStatus, note: str
    ) -> bool:
        reviewed = status != "pending"
        async with self.sessions.begin() as session:
            found = await session.scalar(
                text("""
                    UPDATE inspection_runs SET review_status = :status, review_note = :note,
                        reviewed_by = :reviewer,
                        reviewed_at = CASE WHEN :reviewed THEN now() ELSE NULL END
                    WHERE id = :id AND org_id = :org_id
                    RETURNING id
                """),
                {
                    "status": status,
                    "note": note,
                    "reviewer": user_id if reviewed else None,
                    "reviewed": reviewed,
                    "id": run_id,
                    "org_id": org_id,
                },
            )
        return found is not None

    async def send_to_dataset(self, org_id: UUID, run_id: UUID, photo: Photo) -> None:
        async with self.sessions.begin() as session:
            result = await session.execute(
                text("""
                    SELECT r.sent_to_dataset_at, p.dataset_id
                    FROM inspection_runs r JOIN inspection_programs p ON p.id = r.program_id
                    WHERE r.id = :id AND r.org_id = :org_id
                    FOR UPDATE OF r
                """),
                {"id": run_id, "org_id": org_id},
            )
            row = result.mappings().one_or_none()
            if row is None:
                raise NotFound("Inspection result not found", "run_not_found")
            if row["sent_to_dataset_at"] is not None:
                raise Conflict("This photo is already in the project.", "already_sent")
            dataset_id = row["dataset_id"]
            await session.execute(
                text("SELECT 1 FROM training_datasets WHERE id = :id FOR UPDATE"),
                {"id": dataset_id},
            )
            count = await session.scalar(
                text("""
                    SELECT count(*) FROM training_photos p
                    JOIN training_datasets d ON d.id = p.dataset_id
                    WHERE d.id = :dataset_id AND d.org_id = :org_id
                """),
                {"dataset_id": dataset_id, "org_id": org_id},
            )
            if count >= MAX_DATASET_PHOTOS:
                raise Conflict(
                    f"The project already has {MAX_DATASET_PHOTOS} photos. Remove some first.",
                    "dataset_full",
                )
            await session.execute(
                text("""
                    INSERT INTO training_photos
                        (dataset_id, id, filename, media_type, digest, reviewed, boxes, position)
                    VALUES (:dataset_id, :id, :filename, :media_type, :digest, :reviewed,
                        CAST(:boxes AS jsonb),
                        (SELECT COALESCE(max(position) + 1, 0) FROM training_photos
                            WHERE dataset_id = :dataset_id))
                """),
                {
                    "dataset_id": dataset_id,
                    "id": photo.id,
                    "filename": photo.filename,
                    "media_type": photo.media_type,
                    "digest": photo.digest,
                    "reviewed": photo.reviewed,
                    "boxes": json.dumps(photo.boxes),
                },
            )
            await session.execute(
                text("""
                    UPDATE training_datasets SET revision = revision + 1, updated_at = now()
                    WHERE id = :id
                """),
                {"id": dataset_id},
            )
            await session.execute(
                text("UPDATE inspection_runs SET sent_to_dataset_at = now() WHERE id = :id"),
                {"id": run_id},
            )
