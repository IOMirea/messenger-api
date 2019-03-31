import binascii

from typing import Iterable, Optional, Dict, Any, Set, Callable, Awaitable

from aiohttp import web

from log import server_log
from models import converters
from errors import ConvertError, CheckError
from utils import access_token


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
    params: Dict[str, converters.Converter],
    unique: bool = False,
    from_body: bool = False,
) -> DecoratedHandlerType:
    def deco(endpoint: HandlerType) -> HandlerType:
        async def wrapper(req: web.Request) -> web.Response:
            # TODO: check encoding

            if from_body:
                query = await req.post()
                query_name = "body"  # used in error messages
            else:
                query = req.query
                query_name = "query"  # used in error messages

            if unique:
                repeating = get_repeating(query.keys())

                if repeating is not None:
                    return web.json_response(
                        {repeating: f"Repeats in {query_name}"}, status=400
                    )

            req["query"] = req.get("query", {})

            for name, converter in params.items():
                if name not in query:
                    try:
                        # not converting default value to type, be careful
                        req["query"][name] = converter.get_default()
                        continue
                    except KeyError:  # no default value
                        return web.json_response(
                            {name: f"Missing from {query_name}"}, status=400
                        )

                try:
                    req["query"][name] = await converter.convert(
                        query[name], req.app
                    )
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


def parse_token(endpoint: HandlerType) -> HandlerType:
    async def wrapper(req: web.Request) -> web.Response:
        try:
            token = req.headers["Authorization"]
        except KeyError:
            raise web.HTTPUnauthorized(reason="No access token passed")

        try:
            token_start, token_middle, token_end = token.split(
                "."
            )  # ValueError
            user_id = access_token.decode_token_user_id(
                token_start
            )  # ValueError, binascii.Error
            create_offset = access_token.decode_token_creation_offset(
                token_middle
            )  # ValueError, binascii.Error
        except (ValueError, binascii.Error) as e:
            server_log.info(f"Error parsing token {token}: {e}")

            raise web.HTTPUnauthorized(reason="Impropper access token passed")

        password = await req.config_dict["pg_conn"].fetchval(
            "SELECT password FROM users WHERE id = $1", user_id
        )

        if password is None:
            raise web.HTTPUnauthorized(reason="Impropper access token passed")

        hmac_component = access_token.encode_token_hmac_component(
            password, user_id, create_offset
        )
        if hmac_component != token_end:
            server_log.info(
                f"Token hmac signature did not match: {user_id}-{token}"
            )
            raise web.HTTPUnauthorized(reason="Impropper access token passed")

        scope = await req.config_dict["pg_conn"].fetchval(
            "SELECT scope FROM tokens WHERE user_id = $1 AND hmac_component = $2",
            user_id,
            hmac_component,
        )

        if scope is None:
            server_log.info(f"Token not found: {user_id}-{hmac_component}")
            raise web.HTTPUnauthorized(reason="Impropper access token passed")

        req["user_id"] = user_id
        req["scope"] = scope

        return await endpoint(req)

    return wrapper
