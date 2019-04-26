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

from typing import Callable, Awaitable

from aiohttp import web

from log import server_log
from db.postgres import MESSAGE

_Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


def channel(endpoint: _Handler) -> _Handler:
    async def wrapper(req: web.Request) -> web.StreamResponse:
        try:
            channel_id = req["match_info"]["channel_id"]
        except KeyError:
            server_log.critical(
                "Channel id not found. Did you set correct url for endpoint?"
            )

            raise web.HTTPInternalServerError()

        try:
            user_id = req["access_token"].user_id
        except KeyError:
            server_log.critical(
                "Access token not in request fields. Did you forget to place parse_token wrapper above check?"
            )

            raise web.HTTPInternalServerError()

        user_in_channel = await req.config_dict["pg_conn"].fetchval(
            f"SELECT EXISTS(SELECT 1 FROM users WHERE id = $1 AND $2 = ANY(channel_ids))",
            user_id,
            channel_id,
        )

        if not user_in_channel:
            raise web.HTTPForbidden(
                reason="You do not have access to this channel"
            )

        return await endpoint(req)

    return wrapper


def edit_message(endpoint: _Handler) -> _Handler:
    async def wrapper(req: web.Request) -> web.StreamResponse:
        try:
            message_id = req["match_info"]["message_id"]
        except KeyError:
            server_log.critical(
                "Message id not found. Did you set correct url for endpoint?"
            )

            raise web.HTTPInternalServerError()

        try:
            user_id = req["access_token"].user_id
        except KeyError:
            server_log.critical(
                "Access token not in request fields. Did you forget to place parse_token wrapper above check?"
            )

            raise web.HTTPInternalServerError()

        message = await req.config_dict["pg_conn"].fetchrow(
            f"SELECT {MESSAGE} FROM messages_with_author WHERE id = $1 AND _author_id = $2",
            message_id,
            user_id,
        )

        if message is None:
            raise web.HTTPForbidden(
                reason="You do not have access to modify this message"
            )

        req["message"] = message

        return await endpoint(req)

    return wrapper


def user(endpoint: _Handler) -> _Handler:
    async def wrapper(req: web.Request) -> web.StreamResponse:
        try:
            user_id = req["match_info"]["user_id"]
        except KeyError:
            server_log.critical(
                "User id not found. Did you set correct url for endpoint?"
            )

        try:
            request_user_id = req["access_token"].user_id
        except KeyError:
            server_log.critical(
                "Access token not in request fields. Did you forget to place parse_token wrapper above check?"
            )

            raise web.HTTPInternalServerError()

        if user_id != request_user_id:
            raise web.HTTPForbidden

        return await endpoint(req)

    return wrapper


def create_reports(endpoint: _Handler) -> _Handler:
    async def wrapper(req: web.Request) -> web.StreamResponse:
        # TODO: actual check
        return await endpoint(req)

    return wrapper


def access_reports(endpoint: _Handler) -> _Handler:
    async def wrapper(req: web.Request) -> web.StreamResponse:
        # TODO: actual check
        return await endpoint(req)

    return wrapper
