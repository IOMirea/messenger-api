from aiohttp import web


def channel_access(endpoint):
    async def wrapper(req):
        # TODO: check token
        channel_id = int(req.match_info["channel_id"])
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
