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


import hmac
import base64
import secrets

from urllib.parse import urlencode
from typing import Any, Union, Dict, List

import aiohttp_jinja2

from aiohttp_session import get_session
from aiohttp import web

from models import converters
from models.access_token import Token
from utils import helpers
from constants import EXISTING_SCOPES
from db.postgres import APPLICATION

routes = web.RouteTableDef()


class Scope(converters.Converter):
    async def _convert(self, value: str, app: web.Application) -> List[str]:
        scopes: List[str] = []

        for i, scope in enumerate(value.split(" ")):
            if scope not in EXISTING_SCOPES:
                raise ValueError
            if scope not in scopes:
                scopes.append(scope)

        return scopes


@routes.get("/authorize")
@aiohttp_jinja2.template("auth/oauth_confirmation.html")
async def authorize(
    req: web.Request
) -> Union[Dict[str, Any], web.StreamResponse]:

    query = req.query

    if "response_type" not in query:
        return web.json_response(
            {
                "error": "invalid_request",
                "error_description": "The request is missing a required parameter: response_type",
            },
            status=400,
        )

    elif query["response_type"] == "code":
        # TODO: check scope items
        # TODO: check redirect_uri

        for p in ("client_id", "scope", "response_type"):
            if p not in query:
                return web.json_response(
                    {
                        "error": "invalid_request",
                        "error_description": f"The request is missing a required parameter: {p}",
                    },
                    status=400,
                )
        try:
            scope = await Scope().convert(query["scope"], req.app)
        except ValueError:
            return web.json_response(
                {
                    "error": "value_error",
                    "error_description": "Bad argument for parameter scope",
                },
                status=400,
            )

        try:
            client_id = await converters.ID().convert(
                query["client_id"], req.app
            )
        except ValueError:
            return web.json_response(
                {
                    "error": "value_error",
                    "error_description": "Bad argument for parameter client_id",
                },
                status=400,
            )

        record = await req.config_dict["pg_conn"].fetchrow(
            f"SELECT {APPLICATION} FROM applications_with_owner WHERE id = $1",
            client_id,
        )

        if record is None:
            return web.json_response(
                {
                    "error": "invalid_client",
                    "error_description": "Unknown client",
                },
                status=400,
            )

        if record["redirect_uri"] != query["redirect_uri"]:
            return web.json_response(
                {
                    "error": "error_uri",
                    "error_description": "Redirect uri does not match the client",
                },
                status=400,
            )

        session = await get_session(req)
        if "user_id" not in session:
            # TODO: figure out how to avoid hardcoding login path
            return web.HTTPFound(
                f"{req.scheme}://{req.host}/login?{urlencode({'redirect': req.url})}"
            )

        app = APPLICATION.to_json(record)

        return {
            "redirect_uri": record["redirect_uri"],
            "scope": " ".join(scope),
            "state": query.get("state", ""),
            "app_name": app["name"],
            "app_author_id": app["owner"]["id"],
            "app_author_name": app["owner"]["name"],
        }

    elif query["response_type"] == "token":
        return web.json_response(
            {
                "error": "unsupported_grant_type",
                "error_description": "response_type=token is not supported yet",
            },
            status=400,
        )

    else:
        return web.json_response(
            {
                "error": "unsupported_grant_type",
                "error_description": "The authorization grant type is not supported by the authorization server.",
            },
            status=400,
        )


@routes.post("/authorize")
async def post_authorize(req: web.Request) -> web.Response:
    session = await get_session(req)
    try:
        user_id = session["user_id"]
    except KeyError:
        raise web.HTTPUnauthorized(reason="Bad cookie")

    query = req.query
    post_data = await req.post()

    if not post_data.get("confirm_btn"):
        return web.HTTPFound(
            query["redirect_uri"] + "&error=user has denied access"
        )

    message = ".".join([str(query["client_id"]), query["redirect_uri"]])
    key = secrets.token_bytes(20)
    code = hmac.new(key, msg=message.encode(), digestmod="sha1").hexdigest()

    encoded_key = base64.b64encode(key).decode()

    await req.config_dict["rd_conn"].execute(
        "SETEX",
        f"auth_code:{code}",
        10 * 60,
        f"{user_id}:{encoded_key}:{query['scope']}",
    )

    return web.HTTPFound(query["redirect_uri"] + f"&code={code}")


@routes.post("/token")
async def token(req: web.Request) -> web.Response:
    query = await req.post()  # TODO: handle errors

    if "grant_type" not in query:
        return web.json_response(
            {
                "error": "invalid_request",
                "error_description": "The request is missing a required parameter: grant_type",
            },
            status=400,
        )

    elif query["grant_type"] == "authorization_code":
        # TODO: check client_secret
        # TODO: The identity of the authorization code to the client

        for p in ("client_id", "code", "redirect_uri", "client_secret"):
            if p not in query:
                return web.json_response(
                    {
                        "error": "invalid_request",
                        "error_description": f"The request is missing a required parameter: {p}",
                    },
                    status=400,
                )

        record_key = f"auth_code:{query['code']}"

        record = await req.config_dict["rd_conn"].execute("GET", record_key)
        if record is None:
            return web.json_response(
                {
                    "error": "invalid_grant",
                    "error_description": "Wrong or expired authorization code passed",
                },
                status=400,
            )

        await req.config_dict["rd_conn"].execute("DEL", record_key)

        user_id, encoded_key, scope = record.decode().split(":")

        user_id = int(user_id)
        key = base64.b64decode(encoded_key)

        message = ".".join([str(query["client_id"]), query["redirect_uri"]])
        calculated_code = hmac.new(
            key, msg=message.encode(), digestmod="sha1"
        ).hexdigest()

        if not hmac.compare_digest(calculated_code, query["code"]):
            return web.json_response(
                {
                    "error": " unauthorized_client",
                    "error_description": "Bad authorization code passed",
                },
                status=400,
            )

        user_password = await req.config_dict["pg_conn"].fetchval(
            "SELECT password FROM users WHERE id = $1", user_id
        )

        if user_password is None:
            raise web.HTTPBadRequest(reason="User does not exist")

        token = await Token.from_data(
            user_id,
            user_password,
            int(query["client_id"]),  # TODO: check client_id
            scope.split(" "),
            req.config_dict["pg_conn"],
        )

        # TODO: refresh_token
        # TODO: expires_in
        return web.json_response(
            {
                "access_token": str(token),
                "token_type": "Bearer",
                "scope": scope,
            }
        )
    elif query["grant_type"] == "refresh_token":
        return web.json_response(
            {
                "error": "unsupported_grant_type",
                "error_description": "grant_type=refresh_token is not supported yet",
            },
            status=400,
        )

    else:
        return web.json_response(
            {
                "error": "unsupported_grant_type",
                "error_description": "The authorization grant type is not supported by the authorization server.",
            },
            status=400,
        )


@routes.post("/token/revoke")
@helpers.parse_token
async def revoke(req: web.Request) -> web.Response:
    await req["access_token"].revoke()

    return web.json_response({"message": "Deleted access token"})
