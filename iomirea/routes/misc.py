import os
import hmac
import asyncio

from typing import Dict, Any

import aiohttp_jinja2

from aiohttp import web

from log import git_log
from updater import updater


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


@routes.post("/github-webhook")
async def github_webhook(req: web.Request) -> web.Response:
    header_signature = req.headers.get("X-Hub-Signature")
    if not header_signature:
        raise web.HTTPUnauthorized(reason="Missing signature header")

    secret = req.app["config"]["github-webhook-token"]

    sha_name, delim, signature = header_signature.partition("=")
    if not (sha_name or delim or signature):
        raise web.HTTPUnauthorized(reason="Bad signature header")

    mac = hmac.new(secret.encode(), msg=await req.read(), digestmod="sha1")

    if not hmac.compare_digest(mac.hexdigest(), signature):
        raise web.HTTPUnauthorized

    git_log.info("Received update from webhook, trying to pull ...")
    asyncio.ensure_future(updater(req.app))

    return web.Response()
