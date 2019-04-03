import hmac
import secrets

from typing import Any, Union, Dict, List

import aiohttp_jinja2

from aiohttp import web

from models import converters, checks
from utils import helpers
from constants import EXISTING_SCOPES
from security.security_checks import check_user_password


class Scope(converters.Converter):
    async def _convert(self, value: str, app: web.Application) -> List[str]:
        scopes: List[str] = []

        for i, scope in enumerate(value.split(" ")):
            if scope not in EXISTING_SCOPES:
                raise ValueError
            if scope not in scopes:
                scopes.append(scope)

        return scopes


routes = web.RouteTableDef()


@routes.get("/authorize")
@helpers.query_params(
    {
        "response_type": converters.String(),
        "client_id": converters.ID(),
        "scope": Scope(default=["user"]),
        "redirect_uri": converters.String(),
        "state": converters.String(default=""),
    },
    unique=True,
)
@aiohttp_jinja2.template("authorize.html")
async def authorize(
    req: web.Request
) -> Union[Dict[str, Any], web.StreamResponse]:

    query = req["query"]

    if query["response_type"] == "code":
        # TODO: check scope items
        # TODO: check redirect_uri

        record = await req.config_dict["pg_conn"].fetchval(
            "SELECT (name, redirect_uri) FROM applications WHERE id = $1",
            query["client_id"],
        )

        if record is None:
            raise web.HTTPBadRequest(reason="Application not found in database")

        if record[1] != query["redirect_uri"]:
            raise web.HTTPBadRequest(reason="Bad redirect_uri passed")

        return {
            "redirect_uri": record[1],
            "app_name": record[0],
            "scope": " ".join(query["scope"]),
            "state": query["state"],
        }
    else:
        raise web.HTTPBadRequest(
            reason="Currently only response_type of type code supported"
        )


@routes.post("/authorize")
@helpers.query_params(
    {
        "response_type": converters.String(checks=[checks.Equals("code")]),
        "client_id": converters.ID(),
        "scope": Scope(default=["user"]),
        "redirect_uri": converters.String(),
        "state": converters.String(default=""),
    },
    unique=True,
)
@helpers.query_params(
    {"login": converters.String(), "password": converters.String()},
    unique=True,
    from_body=True,
)
async def post_authorize(req: web.Request) -> web.Response:
    query = req["query"]

    record = await req.config_dict["pg_conn"].fetchval(
        # NOTICE: do we need id here?
        "SELECT (id, password) FROM users WHERE email = $1",
        query["login"],
    )

    if record is None:
        raise web.HTTPUnauthorized()

    if not await check_user_password(query["password"], record[1]):
        raise web.HTTPUnauthorized()

    message = ".".join(
        [
            str(query["client_id"]),
            ".".join(query["scope"]),
            query["redirect_uri"],
        ]
    )
    key = secrets.token_bytes(20)
    code = hmac.new(
        key, msg=message.encode(), digestmod="sha1"
    ).hexdigest()

    await req.config_dict["rd_conn"].execute("SETEX", f"auth_code_{query['client_id']}_{record[0]}_{code}", 10 * 60, key)

    return web.Response(text=code)


@routes.post("/token")
async def token(req: web.Request) -> web.Response:
    # TODO: get values
    user_id = 0
    client_id = 0
    code = ""
    scope = []
    redirect_uri = ""
    # TODO: get values

    code_key = f"auth_code_{client_id}_{user_id}_{code}"

    key = await req.config_dict["rd_conn"].execute("GET", code_key)
    if key is None:
        raise web.HTTPUnauthorized(reason="Wrong or expired key passed")

    await req.config_dict["rd_conn"].execute("DEL", code_key)

    message = ".".join(
        [
            str(client_id),
            ".".join(scope),
            redirect_uri,
        ]
    )
    calculated_code = hmac.new(
        key, msg=message.encode(), digestmod="sha1"
    ).hexdigest()

    hmac.compare_digest(calculated_code, code)

    return web.json_response({"message": "token: WIP"})


@routes.post("/revoke")
async def revoke(req: web.Request) -> web.Response:
    return web.json_response({"message": "revoke: WIP"})
