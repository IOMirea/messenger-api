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

import os
import json
import signal

from typing import (
    Iterable,
    Optional,
    Dict,
    Any,
    Set,
    Callable,
    Awaitable,
    NoReturn,
    List,
)

import asyncpg

from aiohttp import web

from constants import ContentType
from log import server_log
from models import converters
from models.access_token import Token
from enums import Permissions


_Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]
_Decorator = Callable[[_Handler], _Handler]


def get_repeating(iterable: Iterable[Any]) -> Optional[Any]:
    seen: Set[Any] = set()
    for x in iterable:
        if x in seen:
            return x
        seen.add(x)

    return None


async def ensure_permissions(
    *permissions: Permissions,
    request: web.Request,
    user_id: Optional[int] = None,
    channel_id: Optional[int] = None,
) -> None:
    """
    Checks that user with given id has given permissions in channel with given
    id. Raises HTTPForbidden if not.
    Function will treat invalid user/channel id as if permission was missing.
    These checks shoud be performed beforehand.

    Arguments:
        user_id:
            id of user to check permissions. If not passed, user id from
            access token is used.

        channel_id:
            id of channel to check permissions in. If not passed, channel id
            from match info is used.
    """

    def check_permissions(stored: int, recieved: int) -> bool:
        return (stored & recieved) == recieved

    all_permissions = sum([p.value for p in permissions])

    if user_id is None:
        user_id = request["access_token"].user_id

    if channel_id is None:
        channel_id = request["match_info"]["channel_id"]

    cache_key = f"permissions:{channel_id}:{user_id}"

    cached_permissions = await request.config_dict["rd_conn"].execute(
        "GET", cache_key
    )

    if cached_permissions is not None:
        await request.config_dict["rd_conn"].execute("EXPIRE", cache_key, 3600)

        has_permissions = check_permissions(
            int(cached_permissions), all_permissions
        )
    else:
        db_permissions = await request.config_dict["pg_conn"].fetchval(
            "SELECT permissions FROM channel_settings WHERE user_id = $1 AND channel_id = $2",
            user_id,
            channel_id,
        )

        db_permissions_int = asyncpg.BitString(db_permissions).to_int()

        await request.config_dict["rd_conn"].execute(
            "SETEX", cache_key, 3600, db_permissions_int
        )

        has_permissions = check_permissions(
            db_permissions_int, all_permissions
        )

    if not has_permissions:
        raise web.HTTPForbidden(
            reason=f"You need the following permissions to perform this action: [{' '.join(p.name for p in permissions)}]"
        )


def query_params(
    params: Dict[str, converters.Converter],
    unique: bool = False,
    json_response: bool = True,
) -> _Decorator:
    def deco(endpoint: _Handler) -> _Handler:
        async def wrapper(req: web.Request) -> web.StreamResponse:
            query = req.query

            if unique:
                repeating = get_repeating(query.keys())

                if repeating is not None:
                    if json_response:
                        return web.json_response(
                            {repeating: "Repeats in query"}, status=400
                        )

                    raise web.HTTPBadRequest(
                        reason=f"{repeating}: Repeats in query"
                    )

            req["query"] = req.get("query", {})

            try:
                req["query"].update(
                    **await converters.convert_map(
                        params, query, req.app, location="query"
                    )
                )
            except converters.ConvertError as e:
                return e.to_bad_request(json_response)

            return await endpoint(req)

        return wrapper

    return deco


def body_params(
    params: Dict[str, converters.Converter],
    unique: bool = False,
    content_types: List[ContentType] = [ContentType.JSON],
    json_response: bool = True,
) -> _Decorator:
    def deco(endpoint: _Handler) -> _Handler:
        async def wrapper(req: web.Request) -> web.StreamResponse:
            content_type_matches = False
            for content_type in content_types:
                if content_type.value == req.content_type:
                    content_type_matches = True
                    break

            if not content_type_matches:
                return web.json_response(
                    {
                        "message": f"Bad content type. Expected: {[c.value for c in content_types]}"
                    },
                    status=400,
                )

            if content_type == ContentType.JSON:
                try:
                    query = await req.json()
                except json.JSONDecodeError as e:
                    return web.json_response(
                        {"message": f"Error parsing json from body: {e}"},
                        status=400,
                    )
            elif content_type in (
                ContentType.URLENCODED,
                ContentType.FORM_DATA,
            ):
                query = await req.post()
            else:
                server_log.debug(
                    f"body_params: unknown content type: {content_type}"
                )

            if unique:
                repeating = get_repeating(query.keys())

                if repeating is not None:
                    if json_response:
                        return web.json_response(
                            {repeating: "Repeats in body"}, status=400
                        )

                    raise web.HTTPBadRequest(
                        reason=f"{repeating}: Repeats in body"
                    )

            req["body"] = req.get("body", {})

            try:
                req["body"].update(
                    **await converters.convert_map(params, query, req.app)
                )
            except converters.ConvertError as e:
                return e.to_bad_request(json_response)

            return await endpoint(req)

        return wrapper

    return deco


def parse_token(endpoint: _Handler) -> _Handler:
    async def wrapper(req: web.Request) -> web.StreamResponse:
        try:
            token_header = req.headers["Authorization"]
        except KeyError:
            raise web.HTTPUnauthorized(reason="No access token passed")

        try:
            token = Token.from_string(token_header, req.config_dict["pg_conn"])
            if not await token.verify():  # ValueError possible
                raise ValueError
        except ValueError:
            raise web.HTTPUnauthorized(reason="Bad access token passed")

        req["access_token"] = token

        return await endpoint(req)

    return wrapper


def redirect(req: web.Request, router_name: str) -> NoReturn:
    raise web.HTTPFound(req.app.router[router_name].url_for())


def clean_exit() -> None:
    # avoid traceback
    os.kill(os.getpid(), signal.SIGINT)
