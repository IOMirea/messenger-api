"""
IOMirea-server - A server for IOMirea messenger
Copyright (C) 2019  Eugene Ershov

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Dict, Any

import asyncpg


class BaseMigration:
    """Base migration."""

    def __init__(self, version: int):
        self.version = version

    async def _up(self, latest: int) -> Any:
        """Manages internal version updating."""

        raise NotImplementedError

    async def up(self, latest: int) -> None:
        """Performs migration forward."""

        raise NotImplementedError(
            f"Migration {self.version}: Not possible to go up"
        )

    async def _down(self) -> Any:
        """Manages internal version updating."""

        raise NotImplementedError

    async def down(self) -> None:
        """Performs backwards migration."""

        raise NotImplementedError(
            f"Migration {self.version}: Not possible to go down"
        )


class PGMigration(BaseMigration):
    """Postgresql migration."""

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
    """Config migration."""

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


# TODO: RedisMigration
