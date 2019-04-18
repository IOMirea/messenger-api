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

from aiohttp import web

from constants import ContentType
from log import server_log
from models import converters
from models.access_token import Token


_Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]
_Decorator = Callable[[_Handler], _Handler]


def get_repeating(iterable: Iterable[Any]) -> Optional[Any]:
    seen: Set[Any] = set()
    for x in iterable:
        if x in seen:
            return x
        seen.add(x)

    return None


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
                if content_type in set(item for item in ContentType):
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
        except ValueError:
            raise web.HTTPUnauthorized(reason="Bad access token passed")

        password = await req.config_dict["pg_conn"].fetchval(
            "SELECT password FROM users WHERE id = $1", token.user_id
        )

        if password is None:
            raise web.HTTPUnauthorized(
                reason="Bad access token passed (no such user)"
            )

        if not await token.verify(password):
            raise web.HTTPUnauthorized(reason="Bad access token passed")

        req["access_token"] = token

        return await endpoint(req)

    return wrapper


def redirect(req: web.Request, router_name: str) -> NoReturn:
    raise web.HTTPFound(req.app.router[router_name].url_for())
