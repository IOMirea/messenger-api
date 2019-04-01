from typing import Callable, Awaitable

from aiohttp import web

from log import server_log


HandlerType = Callable[[web.Request], Awaitable[web.Response]]


def channel(endpoint: HandlerType) -> HandlerType:
    async def wrapper(req: web.Request) -> web.Response:
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
            "SELECT EXISTS(SELECT 1 FROM users WHERE id=$1 AND $2=ANY(channel_ids))",
            user_id,
            channel_id,
        )

        if not user_in_channel:
            raise web.HTTPForbidden

        return await endpoint(req)

    return wrapper


def user(endpoint: HandlerType) -> HandlerType:
    async def wrapper(req: web.Request) -> web.Response:
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


def create_reports(endpoint: HandlerType) -> HandlerType:
    async def wrapper(req: web.Request) -> web.Response:
        # TODO: actual check
        return await endpoint(req)

    return wrapper


def access_reports(endpoint: HandlerType) -> HandlerType:
    async def wrapper(req: web.Request) -> web.Response:
        # TODO: actual check
        return await endpoint(req)

    return wrapper
