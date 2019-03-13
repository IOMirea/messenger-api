import asyncio
import argparse
import ssl

from typing import Optional

import jinja2
import aiohttp_jinja2

from aiohttp_remotes import setup, XForwardedRelaxed

from aiohttp import web

import middlewares

from routes.api.v0 import routes as api_v0_routes
from routes.oauth2 import routes as oauth2_routes
from routes.misc import routes as misc_routes

from config import Config
from log import setup_logging, server_log, AccessLogger
from db import create_postgres_connection, close_postgres_connection


try:
    import uvloop
except ImportError:
    print(
        "Warning: uvloop library not installed or not supported on your system"
    )
    print("Warning: Using default asyncio event loop")
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


argparser = argparse.ArgumentParser(description="IOMirea server")

argparser.add_argument(
    "-d", "--debug", action="store_true", help="run server in debug mode"
)

argparser.add_argument(
    "--force-ssl",
    action="store_true",
    help="run https server (certificates paths should be configured)",
)


async def on_startup(app: web.Application) -> None:
    # support for X-Forwarded headers
    await setup(app, XForwardedRelaxed())


if __name__ == "__main__":
    app = web.Application(
        middlewares=[
            middlewares.error_handler,
            middlewares.match_info_validator,
        ]
    )

    app["args"] = argparser.parse_args()
    app["config"] = Config("config.yaml")

    app.on_startup.append(create_postgres_connection)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(close_postgres_connection)

    app.router.add_routes(misc_routes)

    # OAuth2 subapp
    OAuth2app = web.Application()
    OAuth2app.add_routes(oauth2_routes)

    app.add_subapp("/oauth2/", OAuth2app)

    # API subapps
    APIv0app = web.Application()
    APIv0app.add_routes(api_v0_routes)

    app.add_subapp("/api/v0/", APIv0app)

    # logging setup
    setup_logging(app)

    # templates setup
    aiohttp_jinja2.setup(
        app, loader=jinja2.FileSystemLoader("iomirea/templates")
    )

    # SSL setup
    ssl_context: Optional[ssl.SSLContext] = None

    if app["args"].force_ssl:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_section = app["config"]["ssl"]
        ssl_context.load_cert_chain(
            ssl_section["cert-chain-path"], ssl_section["cert-privkey-path"]
        )

    server_log.info(
        f'Running in {"debug" if app["args"].debug else "production"} mode'
    )

    web.run_app(
        app,
        access_log_class=AccessLogger,
        port=app["config"]["app-port"],
        ssl_context=ssl_context,
        host="127.0.0.1",
    )
