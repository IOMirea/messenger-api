import asyncio

from aiohttp import web

from db import User, Channel, Message, File
from utils import ensure_existance
from security import access_checks


routes = web.RouteTableDef()


@routes.get(r'/channels/{channel_id:\d+}/messages/{message_id:\d+}')
@access_checks.channel_access
async def get_message(req):
    channel_id = int(req.match_info['channel_id'])
    message_id = int(req.match_info['message_id'])

    await ensure_existance(req.app, 'channels', channel_id, 'Channel')

    record = await req.app['pg_conn'].fetchrow(
        'SELECT * FROM messages WHERE channel_id=$1 AND id=$2;',
        channel_id, message_id
    )

    if record is None:
        raise web.HTTPNotFound(reason='Message not found')

    return web.json_response(Message.from_record(record).json)


@routes.get(r'/channels/{channel_id:\d+}/messages')
@access_checks.channel_access
async def get_messages(req):
    channel_id = int(req.match_info['channel_id'])
    offset = int(req.query.get('offset', 0))  # TODO: handle ValueError
    limit = int(req.query.get('limit', 200))  # TODO: handle ValueError; set max value

    await ensure_existance(req.app, 'channels', channel_id, 'Channel')

    records = await req.app['pg_conn'].fetch(
        'SELECT * FROM messages WHERE channel_id=$1 ORDER BY id DESC LIMIT $2 OFFSET $3;',
        channel_id, limit, offset
    )

    return web.json_response([Message.from_record(record).json for record in records])


@routes.get(r'/channels/{channel_id:\d+}')
@access_checks.channel_access
async def get_channel(req):
    channel_id = int(req.match_info['channel_id'])

    record = await req.app['pg_conn'].fetchrow(
        'SELECT * FROM channels WHERE id=$1;', channel_id)

    if record is None:
        raise web.HTTPNotFound(reason='Channel not found')

    return web.json_response(Channel.from_record(record).json)


@routes.get(r'/users/{user_id:\d+}')
async def get_user(req):
    user_id = int(req.match_info['user_id'])

    record = await req.app['pg_conn'].fetchrow(
        'SELECT * FROM users WHERE id=$1;', user_id)

    if record is None:
        raise web.HTTPNotFound(reason='User not found')

    return web.json_response(User.from_record(record).json)


@routes.get(r'/files/{file_id:\d+}')
async def get_file(req):
    file_id = int(req.match_info['file_id'])

    record = await req.app['pg_conn'].fetchrow(
        'SELECT * FROM files WHERE id=$1', file_id)

    if record is None:
        raise web.HTTPNotFound(text='File not found')

    return web.json_response(File.from_record(record).json)
