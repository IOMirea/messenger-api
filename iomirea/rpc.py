"""
IOMirea-API - API for IOMirea messenger
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

import os

from copy import copy

from aiohttp import web
from iomirea_rpc import Server

from utils.helpers import clean_exit


RPC_COMMAND_RESTART_ALL = 100
RPC_COMMAND_RESTART_UPDATER = 101
RPC_COMMAND_RESTART_API = 102

RPC_COMMAND_PULL_ALL = 200
RPC_COMMAND_PULL_UPDATER = 201
RPC_COMMAND_PULL_API = 202

RPC_COMMAND_EVAL_ALL = 300
RPC_COMMAND_EVAL_UPDATER = 301
RPC_COMMAND_EVAL_API = 302


async def restart_api(srv: Server, address: str) -> None:
    clean_exit()


async def eval_api(srv: Server, address: str, code: str) -> None:
    await srv.respond(address, "Eval is not implemented yet")


async def init_rpc(app: web.Application) -> None:
    config = copy(app["config"]["redis"])
    host = config.pop("host")
    port = config.pop("port")

    node = (
        f"api-{os.environ.get('DATACENTER', 0)}-{os.environ.get('WORKER', 0)}"
    )
    app["rpc_server"] = Server("api", loop=app.loop, node=node)

    await app["rpc_server"].run((host, port), **config)

    app["rpc_server"].register_command(RPC_COMMAND_RESTART_API, restart_api)
    app["rpc_server"].register_command(RPC_COMMAND_EVAL_API, eval_api)


async def stop_rpc(app: web.Application) -> None:
    # await app["rpc_server"].stop()
    pass
