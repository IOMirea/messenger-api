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

from __future__ import annotations

import uuid

import aiohttp
import aioredis


class ConfirmationCode:
    """A base confirmation code."""

    __slots__ = ("user_id", "_code", "_conn")

    def __init__(
        self, user_id: int, code: str, conn: aioredis.ConnectionsPool
    ):
        self.user_id = user_id

        self._code = code
        self._conn = conn

    @staticmethod
    def code_type() -> str:
        """Returns a string used as prefix to store token in database."""

        raise NotImplementedError

    @staticmethod
    def life_time() -> int:
        """Returns token life time in seconds."""

        raise NotImplementedError

    @classmethod
    async def from_string(
        cls, string: str, conn: aioredis.ConnectionsPool
    ) -> ConfirmationCode:
        """Constructs code object from string and checks it."""

        stored = await conn.execute("GET", f"{cls.code_type()}_code:{string}")

        if stored is None:
            raise aiohttp.web.HTTPUnauthorized(reason="Bad or expired code")

        return cls(int(stored), string, conn)

    @classmethod
    async def from_data(
        cls, user_id: int, conn: aioredis.ConnectionsPool
    ) -> ConfirmationCode:
        """Constructs code object from data and saves it."""

        code = cls(user_id, uuid.uuid4().hex, conn)

        await code._save()

        return code

    async def _save(self) -> None:
        """Writes code to database (overwrites if called several times)."""

        await self._conn.execute(
            "SETEX",
            f"{self.code_type()}_code:{self._code}",
            self.life_time(),
            self.user_id,
        )

    async def delete(self) -> None:
        """Deletes code from database if exists."""

        await self._conn.execute(
            "DEL", f"{self.code_type()}_code:{self._code}"
        )

    def __str__(self) -> str:
        return self._code

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} user_id={self.user_id}>"


class EmailConfirmationCode(ConfirmationCode):
    """Email confirmation code."""

    @staticmethod
    def code_type() -> str:
        return "email_confirm"

    @staticmethod
    def life_time() -> int:
        return 86400


class PasswordResetCode(ConfirmationCode):
    """Password restore confirmation code."""

    @staticmethod
    def code_type() -> str:
        return "password_reset"

    @staticmethod
    def life_time() -> int:
        return 43200
