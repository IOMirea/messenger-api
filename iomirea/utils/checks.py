from aiohttp import web

from log import server_log
from utils.converters import ConvertError, CheckError


def get_repeating(iterable):
    seen = set()
    for x in iterable:
        if x in seen:
            return x
        seen.add(x)

    return None


def query_params(params, unique=False):
    def deco(endpoint):
        async def wrapper(req):
            if unique:
                repeating = get_repeating(req.query.keys())

                if repeating is not None:
                    raise web.HTTPBadRequest(
                        reason=f"{repeating} parameter repeats in query"
                    )

            req["query"] = {}

            for name, converter in params.items():
                try:
                    if converter.default is None:
                        if name not in req.query:
                            error_message = f"Parameter {name} is missing from query"
                            break

                    req["query"][name] = await converter.convert(
                        req.query.get(name, converter.default), req.app
                    )
                except ConvertError as e:
                    server_log.debug(f"Parameter {name}: {e}")
                    raise web.HTTPBadRequest(
                        reason=f"Parameter {name}: should be of type {converter}"
                    )
                except CheckError as e:
                    server_log.debug(f"Parameter {name}: check failed: {e}")
                    raise web.HTTPBadRequest(reason=f"Parameter {name}: {e}")

            return await endpoint(req)

        return wrapper

    return deco
