from typing import Iterable, Optional, Dict, Any, Set, Callable, Awaitable

from aiohttp import web

from log import server_log
from models import converters
from errors import ConvertError, CheckError


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


def query_params(
    params: Dict[str, converters.Converter], unique: bool = False
) -> DecoratedHandlerType:
    def deco(endpoint: HandlerType) -> HandlerType:
        async def wrapper(req: web.Request) -> web.Response:
            if unique:
                repeating = get_repeating(req.query.keys())

                if repeating is not None:
                    return web.json_response(
                        {repeating: "Repeats in query"}, status=400
                    )

            req["query"] = {}

            for name, converter in params.items():
                try:
                    if not hasattr(converter, "default"):
                        if name not in req.query:
                            return web.json_response(
                                {name: "Missing from query"}, status=400
                            )

                    if name in req.query:
                        req["query"][name] = await converter.convert(
                            req.query[name], req.app
                        )
                    else:
                        req["query"][name] = getattr(
                            converter, "default"
                        )  # not converting default value to type, be careful
                except ConvertError as e:
                    server_log.debug(f"Parameter {name}: {e}")
                    return web.json_response(
                        {name: f"Should be of type {converter}"}, status=400
                    )
                except CheckError as e:
                    server_log.debug(f"Parameter {name}: check failed: {e}")
                    return web.json_response({name: str(e)}, status=400)

            return await endpoint(req)

        return wrapper

    return deco
