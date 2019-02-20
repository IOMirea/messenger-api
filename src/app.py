import asyncio
import argparse
import logging

from aiohttp import web

from reporter import send_report
from routes import routes
from config import Config
from log import setup_logging


try:
    import uvloop
except ImportError:
    print('Warning: uvloop library not installed or not supported on your system')
    print('Warning: Using default asyncio event loop')
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


argparser = argparse.ArgumentParser(description="IOMirea server")
argparser.add_argument('-d', '--debug', action='store_true', help='run server in debug mode')

@web.middleware
async def middleware(req, handler):
    try:
        resp = await handler(req)
    except web.HTTPException as e:
        raise
    except Exception as e:
        log = logging.getLogger('aiohttp.server')
        log.exception('Error handling request', exc_info=e, extra={'request': req})
        return web.Response(text='Internal server error.', status=500)

    return resp


if __name__ == '__main__':
    args = argparser.parse_args()

    app = web.Application(middlewares=[middleware])
    app.router.add_routes(routes)

    app['config'] = Config('config.yaml')

    setup_logging(app)

    web.run_app(
        app, port=app['config']['app-port'],
        host='127.0.0.1' if args.debug else '0.0.0.0'
    )
