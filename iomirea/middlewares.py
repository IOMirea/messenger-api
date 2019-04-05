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


import asyncio
import binascii

from typing import Callable, Awaitable
from aiohttp import web

from log import server_log
from models import converters
from models.access_token import Token

HandlerType = Callable[[web.Request], Awaitable[web.Response]]


@web.middleware
async def error_handler(
    req: web.Request, handler: HandlerType
) -> web.Response:
    try:
        return await handler(req)
    except (web.HTTPSuccessful, web.HTTPRedirection):
        raise
    except web.HTTPException as e:
        status = e.status
        message = e.text
    except asyncio.CancelledError:
        if req.config_dict["args"].debug:
            raise

        status = 500
        message = f"{status} Internal server error"
    except Exception as e:
        server_log.exception(
            "Error handling request", exc_info=e, extra={"request": req}
        )
        status = 500
        message = f"{status}: Internal server error"

    return web.json_response({"message": message}, status=status)


@web.middleware
async def match_info_validator(
    req: web.Request, handler: HandlerType
) -> web.Response:
    req["match_info"] = {}

    for key, value in req.match_info.items():
        if not key.endswith("_id"):
            continue

        if value == "@me":
            try:
                token_header = req.headers["Authorization"]
            except KeyError:
                raise web.HTTPUnauthorized(
                    reason="No access token passed, unable to decode @me"
                )

            try:
                # not doing propper token checks here, not even token structure
                if token_header.startswith("Bearer "):
                    token_header = token_header[7:]

                value = Token.decode_user_id(token_header.partition(".")[0])
            except (ValueError, binascii.Error):
                raise web.HTTPUnauthorized(reason="Bad access token passed")

        try:
            req["match_info"][key] = await converters.ID().convert(
                value, req.app
            )
        except (converters.ConvertError, converters.CheckError) as e:
            server_log.debug(f"match_validator: {value}: {e}")
            raise web.HTTPNotFound

    return await handler(req)
