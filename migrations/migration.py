from typing import Dict, Any

import asyncpg


class BaseMigration:
    def __init__(self, version: int):
        self.version = version

    async def _up(self, latest: int) -> Any:
        raise NotImplementedError

    async def up(self, latest: int) -> None:
        raise NotImplementedError(
            f"Migration {self.version}: Not possible to go up"
        )

    async def _down(self) -> Any:
        raise NotImplementedError

    async def down(self) -> None:
        raise NotImplementedError(
            f"Migration {self.version}: Not possible to go down"
        )


class DBMigration(BaseMigration):
    def __init__(self, version: int, connection: asyncpg.Connection):
        super().__init__(version)

        self.conn = connection

    async def _up(self, latest: int) -> None:
        await self.up(latest)

        await self.conn.fetch(
            f"UPDATE versions SET version={self.version} WHERE name='database'"
        )

    async def _down(self) -> None:
        await self.down()


class ConfigMigration(BaseMigration):
    def __init__(self, version: int, config: Dict[str, Any]):
        super().__init__(version)

        self.config = config

    async def _up(self, latest: int) -> Dict[str, Any]:
        await self.up(latest)

        self.config["config-version"] = self.version

        return self.config

    async def _down(self) -> Dict[str, Any]:
        await self.down()

        self.config["config_version"] = self.version

        return self.config
