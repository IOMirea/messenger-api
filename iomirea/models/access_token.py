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

import hmac
import time
import math
import codecs
import base64
import binascii

from typing import List, Optional

import asyncpg

from constants import EPOCH_OFFSET


class Token:
    __slots__ = (
        "user_id",
        "create_offset",
        "_scope",
        "_app_id",
        "_parts",
        "_conn",
    )

    def __init__(
        self,
        user_id: int,
        create_offset: int,
        parts: List[str],
        conn: asyncpg.Connection,
        scope: Optional[List[str]] = None,
        app_id: Optional[int] = None,
    ):
        self.user_id = user_id
        self.create_offset = create_offset

        self._scope = scope
        self._app_id = app_id

        self._parts = parts

        self._conn = conn

    @classmethod
    def from_string(cls, input_str: str, conn: asyncpg.Connection) -> "Token":
        if input_str.lower().startswith("bearer "):
            input_str = input_str[7:]

        parts = input_str.split(".")
        if len(parts) != 3:
            raise ValueError("Wrong number of token parts")

        try:
            user_id = cls.decode_user_id(
                parts[0]
            )  # ValueError, binascii.Error
            create_offset = cls.decode_create_offset(
                parts[1]
            )  # ValueError, binascii.Error
        except (ValueError, binascii.Error) as e:
            raise ValueError(f"Unable to decode token base64 parts: {e}")

        return cls(user_id, create_offset, parts, conn)

    @classmethod
    async def from_data(
        cls,
        user_id: int,
        secret: bytes,
        app_id: int,
        scope: List[str],
        conn: asyncpg.Connection,
        write: bool = True,
    ) -> "Token":

        parts = []
        parts.append(cls.encode_user_id(user_id))

        create_offset = math.floor(time.time()) - EPOCH_OFFSET

        parts.append(cls.encode_create_offset(create_offset))
        parts.append(cls.encode_hmac_component(secret, user_id, create_offset))

        token = cls(user_id, create_offset, parts, conn, scope, app_id)

        if write:
            await token._write_db()

        return token

    async def _write_db(self) -> None:
        await self._conn.fetch(
            "INSERT INTO tokens (hmac_component, user_id, app_id, create_offset, scope)"
            "   VALUES ($1, $2, $3, $4, $5)",
            self._parts[2],
            self.user_id,
            self._app_id,
            self.create_offset,
            self._scope,
        )

    async def verify(self) -> bool:
        password = await self._conn.fetchval(
            "SELECT password FROM users WHERE id = $1", self.user_id
        )

        if password is None:
            raise ValueError("User does not exist in db")

        hmac_calculated = self.encode_hmac_component(
            password, self.user_id, self.create_offset
        )

        return hmac_calculated == self._parts[2] and await self.exists()

    async def exists(self) -> bool:
        record = await self._conn.fetchval(
            "SELECT (scope, app_id) FROM tokens WHERE hmac_component = $1 AND user_id = $2",
            self._parts[2],
            self.user_id,
        )

        if record is None:
            return False

        self._scope = record[0]
        self._app_id = record[1]

        return True

    async def get_scope(self) -> List[str]:
        if self._scope is None:
            if not await self.exists():  # fetch scope
                raise RuntimeError("Token does not exist in database")

        # ignoring type because checking self.exists() output verifies scope
        return self._scope  # type: ignore

    async def get_app_id(self) -> int:
        if self._app_id is None:
            if not await self.exists():  # fetch app_id
                raise RuntimeError("Token does not exist in database")

        # ignoring type because checking self.exists() output verifies app_id
        return self._app_id  # type: ignore

    async def revoke(self) -> None:
        await self._conn.fetchval(
            "DELETE FROM Tokens WHERE user_id = $1 AND hmac_component = $2",
            self.user_id,
            self._parts[2],
        )

    @staticmethod
    def encode_user_id(user_id: int) -> str:
        return base64.urlsafe_b64encode(str(user_id).encode()).decode()

    @staticmethod
    def decode_user_id(token_start: str) -> int:
        return int(base64.urlsafe_b64decode(token_start.encode()))

    @staticmethod
    def encode_create_offset(offset: int) -> str:
        hex_bytes = codecs.decode(f"{offset:x}".encode(), "hex")

        # weird mypy behaviour, bytes and str type conflict
        return base64.urlsafe_b64encode(hex_bytes).decode()  # type: ignore

    @staticmethod
    def decode_create_offset(token_middle: str) -> int:
        hex_bytes = base64.urlsafe_b64decode(token_middle.encode())

        # weird mypy behaviour, bytes and str type conflict
        return int(codecs.encode(hex_bytes, "hex"), 16)  # type: ignore

    @staticmethod
    def encode_hmac_component(
        secret: bytes, user_id: int, create_offset: int
    ) -> str:
        to_encrypt = ".".join([str(user_id), str(create_offset)])

        hmac_component = hmac.new(
            secret, msg=to_encrypt.encode(), digestmod="sha1"
        ).digest()

        # removing '=' from the end of the line
        return base64.urlsafe_b64encode(hmac_component).decode()[:-1]

    def __str__(self) -> str:
        return ".".join(self._parts)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} user_id={self.user_id} app_id={self._app_id} scope={self._scope}>"
