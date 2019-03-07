from aiohttp import web


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

            error_message = None
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
                except ValueError as e:  # TODO: custom error class
                    error_message = f"Parameter {name}: {e}"
                    break

            if error_message is not None:
                raise web.HTTPBadRequest(reason=error_message)

            return await endpoint(req)

        return wrapper

    return deco
