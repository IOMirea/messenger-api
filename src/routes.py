import asyncio
import hmac
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

@routes.post('/github-webhook')
async def gitlab_webhook(req):
    header_signature = req.headers.get('X-Hub-Signature') or ''
    secret = req.app['config']['github-webhook-token'] or ''

    sha_name, signature = header_signature.partition('=')

    mac = hmac.new(secret.encode(), msg=await req.read(), digestmod='sha1')

    if not hmac.compare_digest(mac.hexdigest(), signature):
        return web.Response(text='Permission denied', status=401)

    git_log.info('Received update from webhook, trying to pull ...')
    asyncio.ensure_future(updater(req.app))
    return web.Response()
