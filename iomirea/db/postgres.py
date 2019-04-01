from typing import Dict

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


class DBObject:
    """
    Basic database object container, adds id to keys
    """

    # mapping of database keys to pretty keys
    _keys: Dict[str, str] = {}

    def __init__(self, data: Dict[str, str]):
        self._keys.update({"id": "id"})

        self._data = {pk: data[dk] for dk, pk in self._keys.items()}

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> "DBObject":
        return cls(dict(record))

    @classmethod
    def from_json(cls, data: Dict[str, str]) -> "DBObject":
        return cls(data)

    @property
    def json(self) -> Dict[str, str]:
        return self._data


# just a quick sketch, not full list of properties
class User(DBObject):
    _keys = {"name": "name", "bot": "bot"}


class Channel(DBObject):
    _keys = {
        "name": "name",
        "user_ids": "user_ids",
        "pinned_ids": "pinned_ids",
    }


class Message(DBObject):
    _keys = {
        "author_id": "author_id",
        "content": "content",
        "edited": "edited",
        "pinned": "pinned",
    }


class File(DBObject):
    _keys = {
        "name": "name",
        "message_id": "message_id",
        "channel_id": "channel_id",
        "mime": "mime",
    }


class BugReport(DBObject):
    _keys = {
        "user_id": "user_id",
        "report_body": "body",
        "device_info": "device_info",
        "automatic": "automatic",
    }
