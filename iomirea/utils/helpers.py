from typing import Iterable, Optional, Dict, Any, Set, Callable, Awaitable

from aiohttp import web

from log import server_log
from utils.converters import ConvertError, CheckError


HandlerType = Callable[[web.Request], Awaitable[web.Response]]
DecoratedHandlerType = Callable[
    [Callable[[web.Request], Awaitable[web.Response]]],
    Callable[[web.Request], Awaitable[web.Response]],
]


def get_repeating(iterable: Iterable[Any]) -> Optional[Any]:
    seen: Set[Any] = set()
    for x in iterable:
        if x in seen:
            return x
        seen.add(x)

    return None


def query_params(params: Dict[str, Any], unique: bool = False) -> DecoratedHandlerType:
    def deco(endpoint: HandlerType) -> HandlerType:
        async def wrapper(req: web.Request) -> web.Response:
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
