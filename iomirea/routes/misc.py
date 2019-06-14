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
import asyncio

from typing import Dict, Any

import aiohttp_jinja2

from aiohttp import web


routes = web.RouteTableDef()


@routes.get("/")
@aiohttp_jinja2.template("index.html")
async def index(req: web.Request) -> Dict[str, Any]:
    return {}


@routes.get("/version")
@aiohttp_jinja2.template("version.html")
async def get_version(req: web.Request) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    program = f'git show -s HEAD --format="Currently on commit made %cr by %cn: %s|%H"'
    output = await loop.run_in_executor(None, os.popen, program)
    message, _, commit_hash = output.read().rpartition("|")

    return {"version": message, "commit_hash": commit_hash}
