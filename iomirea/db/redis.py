from copy import copy

import aioredis

from aiohttp import web

from log import server_log


async def create_redis_connection(app: web.Application) -> None:
    server_log.info("Creating redis connection")

    config = copy(app["config"].redis)
    host = config.pop("host")
    port = config.pop("port")

    connection = await aioredis.create_connection((host, port), **config)

    app["rd_conn"] = connection


async def close_redis_connection(app: web.Application) -> None:
    server_log.info("Closing redis connection")

    app["rd_conn"].close()
    await app["rd_conn"].wait_closed()
