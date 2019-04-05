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


from typing import Dict, Tuple, Any

import asyncpg
import aiohttp

from log import server_log


async def create_postgres_connection(app: aiohttp.web.Application) -> None:
    server_log.info("Creating postgres connection")

    connection = await asyncpg.connect(**app["config"].postgresql)

    app["pg_conn"] = connection


async def close_postgres_connection(app: aiohttp.web.Application) -> None:
    server_log.info("Closing postgres connection")

    await app["pg_conn"].close()


class IDObject:
    _keys: Tuple[str, ...] = ()

    def __init__(self) -> None:
        """!!!Should be called at the end when overloaded!!!"""

        self._keys = ("id",) + self._keys

    @property
    def keys(self) -> str:
        try:
            return self._keys_str  # type: ignore
        except AttributeError:
            self._keys_str = ",".join(self._keys)

        return self._keys_str

    def to_json(self, record: asyncpg.Record) -> Dict[str, Any]:
        return {k: record[k] for k in self._keys}

    def __str__(self) -> str:
        return self.keys


class User(IDObject):
    _keys = ("name", "bot")


class SelfUser(User):
    def __init__(self) -> None:
        self._keys += ("email",)  # type: ignore

        super().__init__()


class Channel(IDObject):
    _keys = ("name", "user_ids", "pinned_ids")


class Message(IDObject):
    _keys = ("author_id", "channel_id", "content", "edited", "pinned")


class File(IDObject):
    _keys = ("name", "message_id", "channel_id", "mime")


class BugReport(IDObject):
    _keys = ("user_id", "report_body", "device_info", "automatic")


# singletons
USER = User()
SELF_USER = SelfUser()
CHANNEL = Channel()
MESSAGE = Message()
FILE = File()
BUGREPORT = BugReport()
