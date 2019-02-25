import asyncio
import argparse
import logging

from aiohttp import web

from reporter import send_report
from routes import routes
from config import Config
from log import setup_logging
from postgresql import create_postgres_connection, close_postgres_connection


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
        return web.json_response({'message': e.text}, status=e.status)
    except Exception as e:
        log = logging.getLogger('aiohttp.server')
        log.exception('Error handling request', exc_info=e, extra={'request': req})
        return web.json_response({'message': 'Internal server error.'}, status=500)

    return resp


if __name__ == '__main__':
    app = web.Application(middlewares=[middleware])

    app['args'] = argparser.parse_args()
    app['config'] = Config('config.yaml')

    app.router.add_routes(routes)

    app.on_startup.append(create_postgres_connection)
    app.on_cleanup.append(close_postgres_connection)

    setup_logging(app)

    web.run_app(
        app, port=app['config']['app-port'],
        host='127.0.0.1' if app['args'].debug else '0.0.0.0'
    )
