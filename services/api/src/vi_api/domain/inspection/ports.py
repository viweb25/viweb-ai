from dataclasses import dataclass
from typing import Literal, Protocol

Engine = Literal["inspect", "detect", "analyze"]


@dataclass(frozen=True)
class InspectionResult:
    status_code: int
    content: bytes


class InspectionGateway(Protocol):
    async def inspect(
        self, engine: Engine, image: bytes, params: list[tuple[str, str]]
    ) -> InspectionResult:
        """Return a 200 or 422 result, or raise Unavailable."""

    async def detection_model(self) -> bytes: ...
