from aiohttp import web


routes = web.RouteTableDef()


@routes.post("/authorize")
async def authorize(req: web.Request) -> web.Response:
    return web.json_response({"message": "authorize: WIP"})


@routes.post("/token")
async def token(req: web.Request) -> web.Response:
    return web.json_response({"message": "token: WIP"})


@routes.post("/revoke")
async def revoke(req: web.Request) -> web.Response:
    return web.json_response({"message": "revoke: WIP"})
