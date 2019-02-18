import asyncio
import os

from aiohttp import web

from log import git_log
from updater import updater


routes = web.RouteTableDef()

@routes.get('/')
async def index(req):
    return web.Response(text="It works")

@routes.get('/version')
async def version(req):
    loop = asyncio.get_event_loop()
    program = 'git show -s HEAD --format="Currently on commit made %cr by %cn: %s (%H)"'
    output = await loop.run_in_executor(None, os.popen, program)
    return web.Response(text=output.read())

# TODO: use github webhook
@routes.post('/gitlab-webhook')
async def gitlab_webhook(req):
    if req.headers.get('X-Gitlab-Token') != req.app['config']['gitlab-webhook-token']:
        return web.Response(text='Permission denied', status=401)

    git_log.info('Received update from webhook, trying to pull ...')
    asyncio.ensure_future(updater(req.app))
    return web.Response()
