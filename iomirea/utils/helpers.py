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


from typing import Iterable, Optional, Dict, Any, Set, Callable, Awaitable

from aiohttp import web

from log import server_log
from models import converters
from models.access_token import Token
from errors import ConvertError, CheckError


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
    from_body: bool = False,
) -> _Decorator:
    def deco(endpoint: _Handler) -> _Handler:
        async def wrapper(req: web.Request) -> web.StreamResponse:
            # TODO: check encoding

            if from_body:
                query = await req.post()
                query_name = "body"  # used in error messages
            else:
                query = req.query
                query_name = "query"  # used in error messages

            if unique:
                repeating = get_repeating(query.keys())

                if repeating is not None:
                    return web.json_response(
                        {repeating: f"Repeats in {query_name}"}, status=400
                    )

            req["query"] = req.get("query", {})

            for name, converter in params.items():
                if name not in query:
                    try:
                        # not converting default value to type, be careful
                        req["query"][name] = converter.get_default()
                        continue
                    except KeyError:  # no default value
                        return web.json_response(
                            {name: f"Missing from {query_name}"}, status=400
                        )

                try:
                    req["query"][name] = await converter.convert(
                        query[name], req.app
                    )
                except ConvertError as e:
                    server_log.debug(f"Parameter {name}: {e}")

                    if e.overwrite_response:
                        error = str(e)
                    else:
                        error = f"Should be of type {converter}"

                    return web.json_response({name: error}, status=400)
                except CheckError as e:
                    server_log.debug(f"Parameter {name}: check failed: {e}")

                    return web.json_response({name: str(e)}, status=400)

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
