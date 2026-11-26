from vi_api.domain.errors import PermissionDenied
from vi_api.domain.identity.models import CurrentUser
from vi_api.domain.inspection.ports import Engine, InspectionGateway, InspectionResult


def require_workspace(user: CurrentUser) -> None:
    if not user.organisations:
        raise PermissionDenied("Workspace access is required", "organisation_access_denied")


class InspectionService:
    def __init__(self, gateway: InspectionGateway):
        self.gateway = gateway

    async def inspect(
        self,
        user: CurrentUser,
        engine: Engine,
        image: bytes,
        params: list[tuple[str, str]],
    ) -> InspectionResult:
        require_workspace(user)
        return await self.gateway.inspect(engine, image, params)

    async def detection_model(self, user: CurrentUser) -> bytes:
        require_workspace(user)
        return await self.gateway.detection_model()
