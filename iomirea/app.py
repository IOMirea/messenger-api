import asyncio
import argparse

from aiohttp import web

from routes.api.v0 import routes as api_v0_routes
from routes.oauth2 import routes as oauth2_routes
from routes.misc import routes as misc_routes

from config import Config
from log import setup_logging, server_log
from db import create_postgres_connection, close_postgres_connection


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
async def error_middleware(req, handler):
    try:
        return await handler(req)
    except web.HTTPException as e:
        status = e.status
        message = e.text
    except Exception as e:
        server_log.exception('Error handling request', exc_info=e, extra={'request': req})
        status = 500
        message = f'{status}: Internal server error'

    return web.json_response({'message': message}, status=status)


if __name__ == '__main__':
    app = web.Application(middlewares=[error_middleware])

    app['args'] = argparser.parse_args()
    app['config'] = Config('config.yaml')

    app.on_startup.append(create_postgres_connection)
    app.on_cleanup.append(close_postgres_connection)

    setup_logging(app)

    app.router.add_routes(misc_routes)

    # OAuth2 subapp
    OAuth2app = web.Application()
    OAuth2app.add_routes(oauth2_routes)

    app.add_subapp('/oauth/', OAuth2app)

    # API subapps
    APIv0app = web.Application()
    APIv0app.add_routes(api_v0_routes)

    app.add_subapp('/api/v0/', APIv0app)
    # app.add_subapp('/api/', APIv0app)  # defaults to latest API version

    server_log.info(f'Running in {"debug" if app["args"].debug else "production"} mode')

    web.run_app(
        app, port=app['config']['app-port'],
        host='127.0.0.1' if app['args'].debug else '0.0.0.0'
    )
