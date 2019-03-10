from typing import Callable, Awaitable

from aiohttp import web


HandlerType = Callable[[web.Request], Awaitable[web.Response]]


def channel(endpoint: HandlerType) -> HandlerType:
    async def wrapper(req: web.Request) -> web.Response:
        # TODO: check token
        channel_id = req["match_info"]["channel_id"]
        user_id = 0  # TODO: get from token

        result = await req.config_dict["pg_conn"].fetchrow(
            "SELECT 1 FROM users WHERE id=$1 AND $2=ANY(channel_ids);",
            user_id,
            channel_id,
        )

        if result is None:
            raise web.HTTPForbidden

        return await endpoint(req)

    return wrapper
