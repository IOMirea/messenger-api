from copy import copy

import aioredis

from aiohttp import web

from log import server_log


async def create_redis_pool(app: web.Application) -> None:
    server_log.info("Creating redis connection")

    config = copy(app["config"].redis)
    host = config.pop("host")
    port = config.pop("port")

    pool = await aioredis.create_pool((host, port), **config)

    app["rd_conn"] = pool


async def close_redis_pool(app: web.Application) -> None:
    server_log.info("Closing redis connection")

    app["rd_conn"].close()
    await app["rd_conn"].wait_closed()


with open("redis_scripts/remove_expired_cookies.lua") as f:
    REMOVE_EXPIRED_COOKIES = f.read()

with open("redis_scripts/has_permissions.lua") as f:
    HAS_PERMISSIONS = f.read()
