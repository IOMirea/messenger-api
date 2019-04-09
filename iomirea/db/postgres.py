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


from typing import Dict, Tuple, Any, Optional, List

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
    _embedded: Dict[str, "IDObject"] = {}

    def __init__(self) -> None:
        """!!!Should be called at the end when overloaded!!!"""

        self._keys = ("id",) + self._keys

    @property
    def keys(self) -> str:
        try:
            return self._keys_str  # type: ignore
        except AttributeError:
            self._keys_str = ",".join(self.get_keys())

        return self._keys_str

    def get_keys(self, *, embedded: Optional[str] = None) -> List[str]:
        keys = []
        for k in self._keys:
            if embedded is None:
                key = k
            else:
                key = f"_{embedded}_{k}"

            keys.append(key)

        for e_name, e_cls in self._embedded.items():
            for k in e_cls.get_keys(embedded=e_name):
                if embedded is None:
                    key = k
                else:
                    key = f"_{embedded}{k}"

                keys.append(key)

        return keys

    def to_json(
        self, record: asyncpg.Record, *, embedded: Optional[str] = None
    ) -> Dict[str, Any]:
        obj: Dict[str, Any] = {}

        for k in self._keys:
            if embedded is None:
                obj[k] = record[k]
            else:
                obj[k] = record[f"_{embedded}_{k}"]

        for e_name, e_cls in self._embedded.items():
            obj[e_name] = e_cls.to_json(record, embedded=e_name)

        return obj

    def __str__(self) -> str:
        return self.keys

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} _embedded={self._embedded}>"


class User(IDObject):
    _keys = ("name", "bot")


class SelfUser(User):
    _keys = User._keys + ("email",)  # type: ignore
    _embedded = {"test": User()}


class Channel(IDObject):
    _keys = ("name", "user_ids", "pinned_ids")


class PlainMessage(IDObject):
    _keys = ("author_id", "channel_id", "content", "edit_id", "pinned")


class Message(IDObject):
    _keys = ("edit_id", "channel_id", "content", "pinned")
    _embedded = {"author": User()}


class File(IDObject):
    _keys = ("name", "message_id", "channel_id", "mime")


class BugReport(IDObject):
    _keys = ("user_id", "report_body", "device_info", "automatic")


class PlainApplication(IDObject):
    _keys = ("name", "redirect_uri")


class Application(IDObject):
    _keys = ("name", "redirect_uri")
    _embedded = {"owner": User()}


# singletons
USER = User()
SELF_USER = SelfUser()
CHANNEL = Channel()
PLAIN_MESSAGE = PlainMessage()
MESSAGE = Message()
FILE = File()
BUGREPORT = BugReport()
PLAIN_APPLICATION = PlainApplication()
APPLICATION = Application()
