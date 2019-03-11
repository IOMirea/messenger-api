from typing import Dict, Optional, Any

import asyncpg


# TODO: separate to ConfigMigartion and DBMigration


class Migration:
    def __init__(
        self,
        config: Dict[str, Any],
        version: int,
        connection: Optional[asyncpg.Connection] = None,
    ):
        self.config = config
        self.version = version
        self.conn = connection

    async def _up(self, latest: int, config: bool) -> Dict[str, Any]:
        await self.up(latest)
        if config:
            self.config["config-version"] = self.version
            return self.config

        if self.conn is None:
            raise RuntimeError(
                "migration does not have database connection to use"
            )

        await self.conn.execute(
            f"UPDATE versions SET version={self.version} WHERE name='database';"
        )

        return self.config

    async def up(self, latest: int) -> None:
        raise NotImplementedError(
            f"Migration {self.version}: Not possible to go up"
        )

    async def _down(self, config: bool) -> Dict[str, Any]:
        await self.down()
        if config:
            self.config["config_version"] = self.version
            return self.config

        if self.conn is None:
            raise RuntimeError(
                "migration does not have database connection to use"
            )

        await self.conn.execute(
            f"UPDATE versions SET version={self.version} WHERE name='database';"
        )

        return self.config

    async def down(self) -> None:
        raise NotImplementedError(
            f"Migration {self.version}: Not possible to go down"
        )
