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


import re
import hmac
import base64
import secrets

from urllib.parse import urlencode
from typing import Any, Union, Dict, List

import aiohttp_jinja2

from aiohttp_session import get_session
from aiohttp import web

from models import converters, checks
from models.access_token import Token
from utils import helpers
from errors import ConvertError
from constants import EXISTING_SCOPES
from db.postgres import APPLICATION


class Scope(converters.Converter):
    async def _convert(self, value: str, app: web.Application) -> List[str]:
        scopes: List[str] = []

        for i, scope in enumerate(value.split(" ")):
            if scope not in EXISTING_SCOPES:
                raise ValueError
            if scope not in scopes:
                scopes.append(scope)

        return scopes


class RedirectURI(converters.Converter):
    URI_REGEX = re.compile(r"[a-z]+://\w+[^#]*", re.IGNORECASE | re.UNICODE)

    def __init__(self, verify: bool = True, **kwargs: Any):
        super().__init__(**kwargs)

        self.verify = verify

    async def _convert(self, value: str, app: web.Application) -> str:
        if self.verify:
            if self.URI_REGEX.fullmatch(value) is None:
                raise ConvertError("Bad format", overwrite_response=True)

        return value


authorize_query_params = {
    "client_id": converters.ID(),
    "scope": Scope(default=["user"]),
    "redirect_uri": RedirectURI(),
    "state": converters.String(default=""),
    "response_type": converters.String(
        checks=[checks.OneOf(["code", "token"])]
    ),
}

routes = web.RouteTableDef()


@routes.get("/authorize")
@helpers.query_params(authorize_query_params, unique=True)
@aiohttp_jinja2.template("auth/oauth_confirmation.html")
async def authorize(
    req: web.Request
) -> Union[Dict[str, Any], web.StreamResponse]:

    query = req["query"]

    if query["response_type"] == "code":
        # TODO: check scope items
        # TODO: check redirect_uri

        record = await req.config_dict["pg_conn"].fetchrow(
            f"SELECT {APPLICATION} FROM applications_with_owner WHERE id = $1",
            query["client_id"],
        )

        if record is None:
            raise web.HTTPBadRequest(
                reason="Application not found in database"
            )

        if record["redirect_uri"] != query["redirect_uri"]:
            raise web.HTTPBadRequest(reason="Bad redirect_uri passed")

        session = await get_session(req)
        if "user_id" not in session:
            # TODO: figure out how to avoid hardcoding login path
            return web.HTTPFound(
                f"{req.scheme}://{req.host}/login?{urlencode({'redirect': req.url})}"
            )

        app = APPLICATION.to_json(record)

        return {
            "redirect_uri": record["redirect_uri"],
            "scope": " ".join(query["scope"]),
            "state": query["state"],
            "app_name": app["name"],
            "app_author_id": app["owner"]["id"],
            "app_author_name": app["owner"]["name"],
        }

    elif query["response_type"] == "token":
        raise web.HTTPNotImplemented(
            reason="response_type=token is not supported yet"
        )

    else:
        raise RuntimeError(
            f"Unknown response_type received: {query['response_type']}"
        )


@routes.post("/authorize")
@helpers.query_params(authorize_query_params, unique=True)
async def post_authorize(req: web.Request) -> web.Response:
    session = await get_session(req)
    try:
        user_id = session["user_id"]
    except KeyError:
        raise web.HTTPUnauthorized(reason="Bad cookie")

    query = req["query"]
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
        f"{user_id}:{encoded_key}:{' '.join(query['scope'])}",
    )

    return web.HTTPFound(query["redirect_uri"] + f"&code={code}")


@routes.post("/token")
@helpers.query_params(
    {
        "grant_type": converters.String(
            checks=[checks.OneOf(["authorization_code", "refresh_token"])]
        ),
        "code": converters.String(),
        "redirect_uri": RedirectURI(verify=False),
        "client_id": converters.ID(),
        "client_secret": converters.String(),
    },
    unique=True,
    from_body=True,
)
async def token(req: web.Request) -> web.Response:
    query = req["query"]

    if query["grant_type"] == "authorization_code":
        # TODO: check client_secret

        record_key = f"auth_code:{query['code']}"

        record = await req.config_dict["rd_conn"].execute("GET", record_key)
        if record is None:
            raise web.HTTPUnauthorized(
                reason="Wrong or expired authorization code passed"
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
            raise web.HTTPUnauthorized(reason="Bad authorization code passed")

        user_password = await req.config_dict["pg_conn"].fetchval(
            "SELECT password FROM users WHERE id = $1", user_id
        )

        if user_password is None:
            raise web.HTTPBadRequest(reason="User does not exist")

        token = await Token.from_data(
            user_id,
            user_password,
            query["client_id"],
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
        raise web.HTTPNotImplemented(
            reason="grant_type=refresh_token is not supported yet"
        )

    else:
        raise RuntimeError(
            f"Unknown grant_type received: {query['grant_type']}"
        )


@routes.post("/token/revoke")
@helpers.parse_token
async def revoke(req: web.Request) -> web.Response:
    await req["access_token"].revoke()

    return web.json_response({"message": "Deleted access token"})
