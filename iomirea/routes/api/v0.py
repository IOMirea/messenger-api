import json

import asyncio

from aiohttp import web

from routes.api import v0_endpoints_public as endpoints_public
from db import User, Channel, Message, File
from utils.db import ensure_existance
from utils import checks, converters
from security import access_checks


routes = web.RouteTableDef()


@routes.get(endpoints_public.MESSAGE)
@access_checks.channel_access
async def get_message(req):
    channel_id = req["match_info"]["channel_id"]
    message_id = req["match_info"]["message_id"]

    await ensure_existance(req, "channels", channel_id, "Channel")

    record = await req.config_dict["pg_conn"].fetchrow(
        "SELECT * FROM messages WHERE channel_id=$1 AND id=$2;", channel_id, message_id
    )

    if record is None:
        raise web.HTTPNotFound(reason="Message not found")

    return web.json_response(Message.from_record(record).json)


@routes.get(endpoints_public.MESSAGES)
@access_checks.channel_access
@checks.query_params(
    {
        "offset": converters.Integer(
            default=0, checks=[converters.BetweenXAndInt64(0)]
        ),
        "limit": converters.Integer(default=200, checks=[converters.Between(0, 200)]),
    }
)
async def get_messages(req):
    channel_id = req["match_info"]["channel_id"]

    offset = req["query"]["offset"]
    limit = req["query"]["limit"]

    await ensure_existance(req, "channels", channel_id, "Channel")

    records = await req.config_dict["pg_conn"].fetch(
        "SELECT * FROM messages WHERE channel_id=$1 ORDER BY id DESC LIMIT $2 OFFSET $3;",
        channel_id,
        limit,
        offset,
    )

    return web.json_response([Message.from_record(record).json for record in records])


@routes.get(endpoints_public.CHANNEL)
@access_checks.channel_access
async def get_channel(req):
    channel_id = req["match_info"]["channel_id"]

    record = await req.config_dict["pg_conn"].fetchrow(
        "SELECT * FROM channels WHERE id=$1;", channel_id
    )

    if record is None:
        raise web.HTTPNotFound(reason="Channel not found")

    return web.json_response(Channel.from_record(record).json)


@routes.get(endpoints_public.USER)
async def get_user(req):
    user_id = req["match_info"]["user_id"]

    record = await req.config_dict["pg_conn"].fetchrow(
        "SELECT * FROM users WHERE id=$1;", user_id
    )

    if record is None:
        raise web.HTTPNotFound(reason="User not found")

    return web.json_response(User.from_record(record).json)


@routes.get(endpoints_public.FILE)
async def get_file(req):
    file_id = req["match_info"]["file_id"]

    record = await req.config_dict["pg_conn"].fetchrow(
        "SELECT * FROM files WHERE id=$1", file_id
    )

    if record is None:
        raise web.HTTPNotFound(reason="File not found")

    return web.json_response(File.from_record(record).json)


@routes.get(endpoints_public.ENDPOINTS)
async def get_public_endpoints(req):
    values = [
        getattr(endpoints_public, k)
        for k in dir(endpoints_public)
        if not k.startswith("__")
    ]
    values.sort()

    return web.Response(text=json.dumps(values, indent=4))
