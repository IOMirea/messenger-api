from aiohttp import web


routes = web.RouteTableDef()

@routes.post('/authorize')
async def token(req):
    return web.json_response({'message': 'authorize: WIP'})


@routes.post('/token')
async def token(req):
    return web.json_response({'message': 'token: WIP'})


@routes.post('/revoke')
async def token(req):
    return web.json_response({'message': 'revoke: WIP'})
