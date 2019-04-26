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

from typing import Dict, Any, Optional, List, Mapping

import asyncpg
import aiohttp

from log import server_log


async def create_postgres_connection(app: aiohttp.web.Application) -> None:
    server_log.info("Creating postgres connection")

    connection = await asyncpg.create_pool(**app["config"].postgresql)

    app["pg_conn"] = connection


async def close_postgres_connection(app: aiohttp.web.Application) -> None:
    server_log.info("Closing postgres connection")

    await app["pg_conn"].close()


class IDObject:
    def __init__(self) -> None:
        # keys to be fetched from database
        self._keys = {"id"}

        # objects to be embedded into keys
        # embedded objects are flattened using syntax:
        # "_{dict_key}_{actual_variable}"
        # the number of nested objects is not limited
        self._embedded: Dict[str, Any] = {}  # objects to be embedded

        # keys that should always be present in diff calculation
        # note: if there is no diff, empty dict will be returned
        self._diff_reserved = {"id"}

    @property
    def keys(self) -> str:
        """Generates a list of database query keys"""

        try:
            return self._keys_str  # type: ignore
        except AttributeError:
            self._keys_str = ",".join(self.get_keys())

        return self._keys_str

    def get_keys(self, *, embedded: Optional[str] = None) -> List[str]:
        """
        Returns a flattened list of keys.
        Unlike keys property does not save state.
        """

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
        self, record: asyncpg.Record, *, _embedded: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Converts database record into dictionary managing nested objects.
        Note: requires all keys defined by class to be present in record.

        Parameters:
            record: record object to extract data from.
            _embedded: internal parameter used for recursion. Do not use it.

        Example:
            # str(MESSAGE) tells database which keys to fetch managing all
            # nested objects.
            # str(MESSAGE) is a shortcut for MESSAGE.keys.
            #
            # Note: fetchrow is used. to_json will not work with multiple rows.
            record = await connection.fetchrow(
                f"SELECT {MESSAGE} FROM messages_with_author WHERE id = $1", 0
            )
            message = MESSAGE.to_json(record)
        """

        obj: Dict[str, Any] = {}

        for k in self._keys:
            if _embedded is None:
                obj[k] = record[k]
            else:
                obj[k] = record[f"_{_embedded}_{k}"]

        for e_name, e_cls in self._embedded.items():
            obj[e_name] = e_cls.to_json(record, _embedded=e_name)

        return obj

    def diff_to_json(
        self,
        old: Mapping[str, Any],
        new: Mapping[str, Any],
        *,
        embedded: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Works similarly to to_json, but returns only different fields between
        old and new mapping. Values from new mapping are returned.
        Always returns several reserved fields such as object id.
        If objects do not differ, returns empty dictionary ignoring reserved
        fields.
        Manages nested objects like to_json.

        Example:
            channel_id = 0

            # str(CHANNEL) tells database which keys to fetch managing all
            # nested objects.
            # str(CHANNEL) is a shortcut for CHANNEL.keys.
            #
            # Note: fetchrow is used. diff_to_json will not work with multiple
            # rows.
            old_row = await connection.fetchrow(
                f"SELECT {CHANNEL} FROM channels WHERE id = $1", channel_id
            )

            new_row = await connection.fetchrow(
                f"UPDATE channels SET name = $1 WHERE id = $2 RETURNING {CHANNEL}",
                "new funny name",
                channel_id,
            )

            diff = CHANNEL.diff_to_json(old_row, new_row)
        """

        obj: Dict[str, Any] = {}

        modified = False

        for k in self._keys:
            if old[k] == new[k]:
                if k not in self._diff_reserved:
                    continue
            else:
                modified = True

            if embedded is None:
                obj[k] = new[k]
            else:
                obj[k] = new[f"_{embedded}_{k}"]

        for e_name, e_cls in self._embedded.items():
            embedded = e_cls.diff_to_json(old, new, embedded=e_name)
            if embedded:  # will be empty with no diff
                obj[e_name] = embedded

        if modified:
            return obj

        return {}

    def __str__(self) -> str:
        """A shortcut for keys property"""

        return self.keys

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} _embedded={self._embedded}>"


class User(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys |= {"name", "bot"}


class SelfUser(User):
    def __init__(self) -> None:
        super().__init__()

        self._keys |= {"email"}


class Channel(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys |= {"name", "user_ids", "pinned_ids"}


class PlainMessage(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys |= {
            "author_id",
            "channel_id",
            "content",
            "edit_id",
            "pinned",
        }


class Message(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys |= {"edit_id", "channel_id", "content", "pinned"}
        self._embedded = {"author": User()}


class File(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys |= {"name", "message_id", "channel_id", "mime"}


class BugReport(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys |= {"user_id", "report_body", "device_info", "automatic"}


class PlainApplication(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys |= {"name", "redirect_uri"}


class Application(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys |= {"name", "redirect_uri"}
        self._embedded = {"owner": User()}


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
