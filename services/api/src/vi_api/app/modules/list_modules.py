from vi_api.domain.modules.catalogue import MODULES, Module


class ListModules:
    """Return the product modules for the app menu."""

    async def execute(self) -> list[Module]:
        return list(MODULES)
