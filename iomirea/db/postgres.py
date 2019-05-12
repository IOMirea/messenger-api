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

from typing import Dict, Any, Optional, List, Mapping, Tuple, Iterable

import asyncpg
import aiohttp

from log import server_log


async def create_postgres_connection(app: aiohttp.web.Application) -> None:
    server_log.info("Creating postgres connection")

    connection = await asyncpg.create_pool(**app["config"]["postgres"])

    app["pg_conn"] = connection


async def close_postgres_connection(app: aiohttp.web.Application) -> None:
    server_log.info("Closing postgres connection")

    await app["pg_conn"].close()


class IDObject:
    """
    Represents an object from database.
    Has utility functionality allowing to fetch object from database and
    expose required fields to user via json.
    """

    def __init__(self) -> None:
        # keys to be fetched from database and sent to user
        self._keys: Tuple[str, ...] = ("id",)

        # objects to be embedded into keys
        # embedded objects are flattened using syntax:
        # "_{dict_key}_{actual_variable}"
        # the number of nested objects is not limited
        self._embedded: Dict[str, Any] = {}

        # keys that should always be present in diff calculation
        # note: if there is no diff, empty dict will be returned
        self._diff_reserved: Tuple[str, ...] = ("id",)

        # keys that should be ignored while checking if object was modified or
        # not. They are still included into result unless mentioned in
        # _diff_reserved. For exaple, message edit snowflake
        self._diff_ignored: Tuple[str, ...] = ()

    @property
    def keys(self) -> str:
        """
        Generates a string representing list of keys that should be used in
        query.

        Example:
            record = await connection.fetchrow(
                f"SELECT {MESSAGE.keys} FROM messages_with_author WHERE id = $1", 0
            )
        """

        try:
            return self._keys_str  # type: ignore
        except AttributeError:
            self._keys_str = ",".join(self.get_keys())

        return self._keys_str

    def get_keys(self, *, embedded: Optional[str] = None) -> List[str]:
        """
        Returns a flattened list of keys that should be used in query.
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

    def update_query_for(
        self,
        table_name: str,
        object_id: int,
        update_keys: Iterable[str],
        *,
        returning: bool = True,
    ) -> str:
        """
        Generates a postgresql update query for given table with id field
        matching object_id parameter.

        Resulting query updates columns if any of provided values differ.
        Query returns 1 or self fields (depending on returning flag).
        Otherwise query returns nothing.

        Example:
            channel_id = 0
            keys = ["name"]

            row = await req.config_dict["pg_conn"].fetchrow(
                CHANNEL.update_query_for(
                    "channels", channel_id, keys
                ),
                "new channel name",
            )
        """

        keys = []

        for key in update_keys:
            if key not in self._keys:
                raise ValueError(f"Unknown key: {key}")

            keys.append(key)

        to_set_keys = keys + list(self._diff_ignored)
        to_set = ",".join(f"{k}=${i + 1}" for i, k in enumerate(to_set_keys))

        conditions = " OR ".join(f"{k}!=${i + 1}" for i, k in enumerate(keys))

        return (
            f"UPDATE {table_name} "
            f"SET {to_set} "
            f"WHERE id={object_id} AND {conditions} "
            f"RETURNING {self if returning else 1}"
        )

    def to_json(
        self, record: Mapping[str, Any], *, _embedded: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Converts database record into dictionary managing nested objects.

        Note: requires all keys defined by class to be present in record.

        Parameters:
            record: object to extract data from.
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
        self, old: Mapping[str, Any], new: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """
        Works similarly to to_json, but returns only different fields between
        old and new mapping. Values from new mapping are applied.
        Always returns several reserved fields such as object id.
        If objects do not differ, returns empty dictionary ignoring reserved
        fields. Changes in embedded objects are not tracked and are taken from
        new mapping.

        Parameters:
            old: old mapping.
            new: new mapping, values are taken from it.

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
                if k not in self._diff_ignored:
                    modified = True

            obj[k] = new[k]

        if not modified:
            return {}

        for e_name, e_cls in self._embedded.items():
            obj[e_name] = e_cls.to_json(new, _embedded=e_name)

        return obj

    def __str__(self) -> str:
        """A shortcut for keys property."""

        return self.keys

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} _embedded={self._embedded}>"


class User(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys += ("name", "bot")


class SelfUser(User):
    def __init__(self) -> None:
        super().__init__()

        self._keys += ("email",)


class Channel(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys += ("name", "owner_id", "user_ids", "pinned_ids")
        self._diff_reserved += ("owner_id",)


class PlainMessage(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys += (
            "author_id",
            "channel_id",
            "content",
            "edit_id",
            "pinned",
            "type",
        )
        self._diff_reserved += ("channel_id",)
        self._diff_ignored = ("edit_id",)


class Message(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys += ("edit_id", "channel_id", "content", "pinned", "type")
        self._embedded = {"author": User()}
        self._diff_reserved += ("channel_id",)
        self._diff_ignored = ("edit_id",)


class File(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys += ("name", "message_id", "channel_id", "mime")


class BugReport(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys += ("user_id", "report_body", "device_info", "automatic")


class PlainApplication(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys += ("name", "redirect_uri")


class Application(IDObject):
    def __init__(self) -> None:
        super().__init__()

        self._keys += ("name", "redirect_uri")
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
