import json

from typing import Any, Union, Dict

import aiohttp
import aiohttp_jinja2

from aiohttp import web

from log import server_log
from security.security_checks import check_user_password


routes = web.RouteTableDef()


@routes.get("/authorize")
@aiohttp_jinja2.template("authorize.html")
async def authorize(
    req: web.Request
) -> Union[Dict[str, Any], web.StreamResponse]:
    ws_current = web.WebSocketResponse()
    ws_ready = ws_current.can_prepare(req)
    if not ws_ready.ok:
        return {}

    await ws_current.prepare(req)

    # TODO: get app_id from parameters
    app_id = 0

    session_key = f"{req.host}-{app_id}"
    req.app["auth_sessions"][session_key] = ws_current

    async for msg in ws_current:
        if msg.type != aiohttp.WSMsgType.text:
            server_log.info(
                f"authorize: Unknown websocket message type received: {msg.type}."
                f"Closing session {session_key}"
            )
            break

        try:
            json_data = json.loads(msg.data)
            login, password = json_data["login"], json_data["password"]
        except (KeyError, json.JSONDecodeError):
            server_log.info(
                f"authorize: Bad json received."
                f"Closing session {session_key}"
            )
            await ws_current.close()
            break

        record = await req.config_dict["pg_conn"].fetchval(
            # NOTICE: do we need id here?
            "SELECT (id, password) FROM users WHERE email = $1",
            login,
        )

        if record is None:
            await ws_current.send_str("auth_fail")
            continue

        if not await check_user_password(password, record[1]):
            await ws_current.send_str("auth_fail")
            continue

        await ws_current.send_str("auth_success")
        await ws_current.close()

    del req.app["auth_sessions"][session_key]

    return ws_current


@routes.post("/token")
async def token(req: web.Request) -> web.Response:
    return web.json_response({"message": "token: WIP"})


@routes.post("/revoke")
async def revoke(req: web.Request) -> web.Response:
    return web.json_response({"message": "revoke: WIP"})
