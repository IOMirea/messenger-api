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

import json

from typing import Dict, List
from aiohttp import web

import asyncpg

from routes.api import v0_endpoints_public as endpoints_public
from db.postgres import USER, SELF_USER, CHANNEL, MESSAGE, FILE, BUGREPORT
from utils import helpers
from utils.db import ensure_existance
from models import converters, checks
from models import events
from security import access
from enums import Permissions, MessageTypes


routes = web.RouteTableDef()


@routes.post(endpoints_public.CHANNELS)
@helpers.parse_token
@helpers.body_params(
    {
        "name": converters.String(
            strip=True, checks=[checks.LengthBetween(1, 128)]
        ),
        "recipients": converters.List(
            converters.ID(), max_len=100, default=[]
        ),
    }
)
async def create_channel(req: web.Request) -> web.Response:
    query = req["body"]

    user_id = req["access_token"].user_id

    recipients = set(query["recipients"] + [user_id])

    channel_id = req.config_dict["sf_gen"].gen_id()

    async with req.config_dict["pg_conn"].acquire() as conn:
        async with conn.transaction():
            channel = await conn.fetchrow(
                f"INSERT INTO channels (id, owner_id, name, user_ids)"
                f"VALUES ($1, $2, $3, $4) RETURNING {CHANNEL}",
                channel_id,
                user_id,
                query["name"],
                recipients,
            )

            await conn.fetch(
                "SELECT FROM add_channel_user($1, $2)", channel_id, user_id
            )

            await conn.fetch(
                "INSERT INTO messages (id, author_id, channel_id, content, type)"
                "VALUES ($1, $2, $3, $4, $5)",
                req.config_dict["sf_gen"].gen_id(),
                user_id,
                channel_id,
                "",
                MessageTypes.CHANNEL_CREATE.value,
            )

    return web.json_response(CHANNEL.to_json(channel))


@routes.put(endpoints_public.CHANNEL)
@helpers.parse_token
@access.channel
@helpers.body_params(
    {
        "name": converters.String(
            strip=True, checks=[checks.LengthBetween(1, 128)]
        )
    }
)
async def edit_channel(req: web.Request) -> web.Response:
    channel_id = req["match_info"]["channel_id"]

    async with req.config_dict["pg_conn"].acquire() as conn:
        async with conn.transaction():
            old_channel = await conn.fetchrow(
                f"SELECT {CHANNEL} FROM channels WHERE id = $1", channel_id
            )

            channel = await req.config_dict["pg_conn"].fetchrow(
                CHANNEL.update_query_for(
                    "channels", channel_id, req["body"].keys()
                ),
                req["body"]["name"],
            )

            if channel is None:
                raise web.HTTPNotModified

            message_id = req.config_dict["sf_gen"].gen_id()

            # TODO: use function to create messages
            await conn.fetch(
                f"INSERT INTO messages (id, author_id, channel_id, content, type)"
                f"VALUES ($1, $2, $3, $4, $5)",
                message_id,
                req["access_token"].user_id,
                channel_id,
                "",
                MessageTypes.CHANNEL_NAME_UPDATE.value,
            )

            message = await conn.fetchrow(
                f"SELECT {MESSAGE} from messages_with_author WHERE id = $1",
                message_id,
            )

    diff = CHANNEL.diff_to_json(old_channel, channel)

    req.config_dict["emitter"].emit(events.CHANNEL_UPDATE(payload=diff))
    req.config_dict["emitter"].emit(
        events.MESSAGE_CREATE(payload=MESSAGE.to_json(message))
    )

    return web.json_response(diff)


@routes.get(endpoints_public.CHANNEL)
@helpers.parse_token
@access.channel
async def get_channel(req: web.Request) -> web.Response:
    channel_id = req["match_info"]["channel_id"]

    record = await req.config_dict["pg_conn"].fetchrow(
        f"SELECT {CHANNEL} FROM channels WHERE id=$1", channel_id
    )

    if record is None:
        raise web.HTTPNotFound(reason="Channel not found")

    return web.json_response(CHANNEL.to_json(record))


@routes.put(endpoints_public.CHANNEL_RECIPIENT)
@helpers.parse_token
@access.channel
async def add_channel_recipient(req: web.Request) -> web.Response:
    channel_id = req["match_info"]["channel_id"]
    user_id = req["match_info"]["user_id"]

    await ensure_existance(req, "users", user_id, "User")

    async with req.config_dict["pg_conn"].acquire() as conn:
        async with conn.transaction():
            success = await conn.fetchval(
                "SELECT * FROM add_channel_user($1, $2)", channel_id, user_id
            )

            if not success:
                raise web.HTTPNotModified(reason="Is user already in channel?")

    raise web.HTTPNoContent()


@routes.delete(endpoints_public.CHANNEL_RECIPIENT)
@helpers.parse_token
@access.channel
async def remove_channel_recipient(req: web.Request) -> web.Response:
    channel_id = req["match_info"]["channel_id"]
    user_id = req["match_info"]["user_id"]

    await ensure_existance(req, "users", user_id, "User")

    async with req.config_dict["pg_conn"].acquire() as conn:
        async with conn.transaction():
            # TODO: unify this
            if req["access_token"].user_id != user_id:  # user kicks other user
                has_permission = await conn.fetchval(
                    "SELECT * FROM has_permissions($1, $2, $3)",
                    channel_id,
                    req["access_token"].user_id,
                    asyncpg.BitString.from_int(
                        Permissions.KICK_MEMBERS.value, 16
                    ),
                )

                if not has_permission:
                    raise web.HTTPForbidden(
                        reason="You do not have permission to kick members"
                    )

            success = await conn.fetchval(
                "SELECT * FROM remove_channel_user($1, $2)",
                channel_id,
                user_id,
            )

            if not success:
                raise web.HTTPNotModified(reason="Is user in channel?")

    raise web.HTTPNoContent()


@routes.get(endpoints_public.CHANNEL_PINS)
@helpers.parse_token
@access.channel
async def get_pins(req: web.Request) -> web.Response:
    channel_id = req["match_info"]["channel_id"]

    async with req.config_dict["pg_conn"].acquire() as conn:
        async with conn.transaction():
            pin_ids = await conn.fetchval(
                "SELECT pinned_ids FROM channels WHERE id = $1", channel_id
            )

        records = await conn.fetch(
            f"SELECT {MESSAGE} FROM messages_with_author WHERE id = ANY($1)",
            pin_ids,
        )

    return web.json_response([MESSAGE.to_json(record) for record in records])


@routes.put(endpoints_public.CHANNEL_PIN)
@helpers.parse_token
@access.channel
async def add_pin(req: web.Request) -> web.Response:
    channel_id = req["match_info"]["channel_id"]
    message_id = req["match_info"]["message_id"]

    await ensure_existance(req, "messages", message_id, "Message")

    async with req.config_dict["pg_conn"].acquire() as conn:
        async with conn.transaction():
            if (
                await conn.fetchval(
                    "SELECT cardinality(pinned_ids) FROM channels WHERE id = $1",
                    channel_id,
                )
                >= 50
            ):

                raise web.HTTPBadRequest(reason="Too many pins (>= 50)")

            # TODO: use function to pin/unpin message
            await conn.fetch(
                "UPDATE channels SET pinned_ids = array_append(pinned_ids, $1) WHERE id = $2 AND NOT $1 = ANY(pinned_ids)",
                message_id,
                channel_id,
            )
            await conn.fetch(
                "UPDATE messages SET pinned = true WHERE id = $1", message_id
            )

            pin_message_id = req.config_dict["sf_gen"].gen_id()

            # TODO: use function to create messages
            await conn.fetch(
                f"INSERT INTO messages (id, author_id, channel_id, content, type)"
                f"VALUES ($1, $2, $3, $4, $5)",
                pin_message_id,
                req["access_token"].user_id,
                channel_id,
                "",
                MessageTypes.CHANNEL_PIN_ADD.value,
            )

            message = await conn.fetchrow(
                f"SELECT {MESSAGE} from messages_with_author WHERE id = $1",
                pin_message_id,
            )

    req.config_dict["emitter"].emit(
        events.MESSAGE_CREATE(payload=MESSAGE.to_json(message))
    )

    raise web.HTTPNoContent()


@routes.delete(endpoints_public.CHANNEL_PIN)
@helpers.parse_token
@access.channel
async def remove_pin(req: web.Request) -> web.Response:
    channel_id = req["match_info"]["channel_id"]
    message_id = req["match_info"]["message_id"]

    await ensure_existance(req, "messages", message_id, "Message")

    async with req.config_dict["pg_conn"].acquire() as conn:
        async with conn.transaction():
            # TODO: use function to pin/unpin message
            await conn.fetch(
                "UPDATE channels SET pinned_ids = array_remove(pinned_ids, $1) WHERE id = $2",
                message_id,
                channel_id,
            )
            await conn.fetch(
                "UPDATE messages SET pinned = false WHERE id = $1", message_id
            )

            pin_message_id = req.config_dict["sf_gen"].gen_id()

            # TODO: use function to create messages
            await conn.fetch(
                f"INSERT INTO messages (id, author_id, channel_id, content, type)"
                f"VALUES ($1, $2, $3, $4, $5)",
                pin_message_id,
                req["access_token"].user_id,
                channel_id,
                "",
                MessageTypes.CHANNEL_PIN_REMOVE.value,
            )

            message = await conn.fetchrow(
                f"SELECT {MESSAGE} from messages_with_author WHERE id = $1",
                pin_message_id,
            )

    req.config_dict["emitter"].emit(
        events.MESSAGE_CREATE(payload=MESSAGE.to_json(message))
    )

    raise web.HTTPNoContent()


@routes.post(endpoints_public.MESSAGES)
@helpers.parse_token
@access.channel
@helpers.body_params(
    {
        "content": converters.String(
            strip=True, checks=[checks.LengthBetween(1, 2048)]
        )
    },
    # TODO: support ContentType.FORM_DATA for file uploads
    # content_types=[ContentType.JSON, ContentType.FORM_DATA],
)
async def create_message(req: web.Request) -> web.Response:
    snowflake = req.config_dict["sf_gen"].gen_id()

    await req.config_dict["pg_conn"].fetch(
        f"INSERT INTO messages (id, author_id, channel_id, content) VALUES ($1, $2, $3, $4)",
        snowflake,
        req["access_token"].user_id,
        req["match_info"]["channel_id"],
        req["body"]["content"],
    )

    message = await req.config_dict["pg_conn"].fetchrow(
        f"SELECT {MESSAGE} FROM messages_with_author WHERE id = $1", snowflake
    )

    data = MESSAGE.to_json(message)

    req.config_dict["emitter"].emit(events.MESSAGE_CREATE(payload=data))

    return web.json_response(data)


@routes.patch(endpoints_public.MESSAGE)
@helpers.parse_token
@access.channel
@access.edit_message
@helpers.body_params(
    {
        "content": converters.String(
            strip=True, checks=[checks.LengthBetween(1, 2048)], default=None
        )
    }
)
async def patch_message(req: web.Request) -> web.Response:
    message_id = req["match_info"]["message_id"]

    params = {k: v for k, v in req["body"].items() if v is not None}
    if not params:
        raise web.HTTPNotModified()

    record = await req.config_dict["pg_conn"].fetchval(
        MESSAGE.update_query_for(
            "messages", message_id, params.keys(), returning=False
        ),
        *params.values(),
        req.config_dict["sf_gen"].gen_id(),
    )

    if record is None:
        raise web.HTTPNotModified

    # FIXME: reduce number of queries!!! (3 here)
    new_row = await req.config_dict["pg_conn"].fetchrow(
        f"SELECT {MESSAGE} FROM messages_with_author WHERE id = $1", message_id
    )

    diff = MESSAGE.diff_to_json(req["message"], new_row)

    req.config_dict["emitter"].emit(events.MESSAGE_UPDATE(payload=diff))

    return web.json_response(diff)


@routes.get(endpoints_public.MESSAGE)
@helpers.parse_token
@access.channel
async def get_message(req: web.Request) -> web.Response:
    channel_id = req["match_info"]["channel_id"]
    message_id = req["match_info"]["message_id"]

    record = await req.config_dict["pg_conn"].fetchrow(
        f"SELECT {MESSAGE} FROM messages_with_author WHERE channel_id=$1 AND id=$2",
        channel_id,
        message_id,
    )

    if record is None:
        raise web.HTTPNotFound(reason="Message not found")

    return web.json_response(MESSAGE.to_json(record))


@routes.get(endpoints_public.MESSAGES)
@helpers.parse_token
@access.channel
@helpers.query_params(
    {
        "offset": converters.Integer(
            default=0, checks=[checks.BetweenXAndInt64(0)]
        ),
        "limit": converters.Integer(
            default=200, checks=[checks.Between(0, 200)]
        ),
    }
)
async def get_messages(req: web.Request) -> web.Response:
    channel_id = req["match_info"]["channel_id"]

    offset = req["query"]["offset"]
    limit = req["query"]["limit"]

    records = await req.config_dict["pg_conn"].fetch(
        f"SELECT {MESSAGE} FROM messages_with_author WHERE channel_id=$1 ORDER BY id LIMIT $2 OFFSET $3",
        channel_id,
        limit,
        offset,
    )

    return web.json_response([MESSAGE.to_json(record) for record in records])


@routes.get(endpoints_public.USER)
@helpers.parse_token
async def get_user(req: web.Request) -> web.Response:
    user_id = req["match_info"]["user_id"]

    fetch_cls = SELF_USER if req["access_token"].user_id == user_id else USER

    record = await req.config_dict["pg_conn"].fetchrow(
        f"SELECT {fetch_cls} FROM users WHERE id=$1;", user_id
    )

    if record is None:
        raise web.HTTPNotFound(reason="User not found")

    return web.json_response(fetch_cls.to_json(record))


@routes.get(endpoints_public.USER_CHANNELS)
@helpers.parse_token
@access.user
async def get_user_channels(req: web.Request) -> web.Response:
    user_id = req["match_info"]["user_id"]

    records = await req.config_dict["pg_conn"].fetch(
        f"SELECT {CHANNEL} FROM channels WHERE id=ANY((SELECT channel_ids FROM users WHERE id=$1)[:])",
        user_id,
    )

    return web.json_response([CHANNEL.to_json(record) for record in records])


@routes.get(endpoints_public.FILE)
@helpers.parse_token
async def get_file(req: web.Request) -> web.Response:
    file_id = req["match_info"]["file_id"]

    record = await req.config_dict["pg_conn"].fetchrow(
        f"SELECT {FILE} FROM files WHERE id=$1", file_id
    )

    if record is None:
        raise web.HTTPNotFound(reason="File not found")

    return web.json_response(FILE.to_json(record))


@routes.post(endpoints_public.BUGREPORTS)
@access.create_reports
@helpers.body_params(
    {
        "user_id": converters.ID(default=None),
        "body": converters.String(checks=[checks.LengthBetween(0, 4096)]),
        "device_info": converters.String(
            checks=[checks.LengthBetween(0, 4096)]
        ),
        "automatic": converters.Boolean(),
    }
)
async def post_bugreport(req: web.Request) -> web.Response:
    query = req["body"]

    record = await req.config_dict["pg_conn"].fetchrow(
        f"INSERT INTO bugreports (user_id, report_body, device_info, automatic) VALUES ($1, $2, $3, $4) RETURNING {BUGREPORT}",
        query["user_id"],
        query["body"],
        query["device_info"],
        query["automatic"],
    )

    return web.json_response(BUGREPORT.to_json(record))


@routes.get(endpoints_public.BUGREPORTS)
@access.access_reports
@helpers.query_params(
    {
        "offset": converters.Integer(
            default=0, checks=[checks.BetweenXAndInt64(0)]
        ),
        "limit": converters.Integer(
            default=200, checks=[checks.Between(0, 200)]
        ),
    }
)
async def get_bugreports(req: web.Request) -> web.Response:
    query = req["query"]

    records = await req.config_dict["pg_conn"].fetch(
        f"SELECT {BUGREPORT} FROM bugreports ORDER BY id LIMIT $1 OFFSET $2",
        query["limit"],
        query["offset"],
    )

    return web.json_response([BUGREPORT.to_json(record) for record in records])


@routes.get(endpoints_public.BUGREPORT)
@access.access_reports
async def get_bugreport(req: web.Request) -> web.Response:
    try:
        record = await ensure_existance(
            req,
            "bugreports",
            req["match_info"]["report_id"],
            "BugReport",
            keys=BUGREPORT.keys,
        )
    except asyncpg.exceptions.DataError:  # INT overflow
        raise web.HTTPBadRequest(reason="Report id is too big")

    return web.json_response(BUGREPORT.to_json(record))


@routes.get(endpoints_public.ENDPOINTS)
async def get_public_endpoints(req: web.Request) -> web.Response:
    endpoints: Dict[str, List[str]] = {}

    for route in req.app.router.routes():
        method = route.method
        if method == "HEAD":
            continue

        if route.resource is None:
            raise RuntimeError(
                f"No canonical url for resource {route.resource!r}"
            )

        path = route.resource.canonical

        endpoints[path] = endpoints.get(path, []) + [method]

    return web.json_response(
        text=json.dumps(endpoints, indent=4, sort_keys=True)
    )
