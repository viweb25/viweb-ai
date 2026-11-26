"""HTTP client for the private inference service."""

from uuid import UUID

import httpx

from vi_api.domain.errors import InvalidInput, Unavailable
from vi_api.domain.inspection.ports import Engine, InspectionResult

INSPECT_TIMEOUT = 95
MODEL_INFO_TIMEOUT = 30
PREVIEW_TIMEOUT = 60
JPEG = {"Content-Type": "image/jpeg"}


def inspection_unavailable() -> Unavailable:
    return Unavailable("Inspection service unavailable", "inference_unavailable")


class HttpInferenceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def inspect(
        self, engine: Engine, image: bytes, params: list[tuple[str, str]]
    ) -> InspectionResult:
        try:
            async with httpx.AsyncClient(timeout=INSPECT_TIMEOUT, trust_env=False) as client:
                result = await client.post(
                    f"{self.base_url}/api/v1/demo/{engine}",
                    params=params,
                    content=image,
                    headers=JPEG,
                )
        except httpx.HTTPError as exc:
            raise inspection_unavailable() from exc
        if result.status_code not in (200, 422):
            raise inspection_unavailable()
        return InspectionResult(result.status_code, result.content)

    async def detection_model(self) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=MODEL_INFO_TIMEOUT, trust_env=False) as client:
                result = await client.get(f"{self.base_url}/api/v1/demo/detection-model")
                result.raise_for_status()
        except httpx.HTTPError as exc:
            raise inspection_unavailable() from exc
        return result.content

    async def preview(self, org_id: UUID, job_id: UUID, image: bytes, confidence: float) -> bytes:
        unavailable = Unavailable("Trained model preview unavailable", "preview_unavailable")
        try:
            async with httpx.AsyncClient(timeout=PREVIEW_TIMEOUT, trust_env=False) as client:
                result = await client.post(
                    f"{self.base_url}/api/v1/demo/trained-models/{org_id}/{job_id}/preview",
                    params={"confidence": confidence},
                    content=image,
                    headers=JPEG,
                )
                result.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 422:
                raise InvalidInput(
                    "The model could not read this photo", "unreadable_photo"
                ) from exc
            raise unavailable from exc
        except httpx.HTTPError as exc:
            raise unavailable from exc
        return result.content
