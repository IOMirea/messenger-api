import io
import random
import string
import textwrap
import traceback

from contextlib import redirect_stdout
from typing import Dict, Any, Tuple, Optional

import aiohttp

import aiohttp_jinja2

from aiohttp import web

from log import server_log


class CompilationError(SyntaxError):
    pass


routes = web.RouteTableDef()


@routes.get(
    f"/{''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))}-python-eval",
    name="python-eval",
)
@aiohttp_jinja2.template("debug/python-eval.html")
async def python_eval(req: web.Request) -> Dict[str, Any]:
    if not req.config_dict["args"].with_eval:
        raise web.HTTPForbidden(reason="Python eval page not ebabled")

    if req.app.get("eval-session", None) is not None:
        raise web.HTTPConflict(reason="Eval session already launched")

    ws_current = web.WebSocketResponse()
    ws_ready = ws_current.can_prepare(req)
    if not ws_ready.ok:
        return {}

    await ws_current.prepare(req)

    req.app["eval-session"] = ws_current

    async for msg in ws_current:
        if msg.type == aiohttp.WSMsgType.text:
            server_log.warn(
                f"Evaluating code from python eval page: {msg.data}"
            )
            try:
                stdout, tb, returned = await eval_code(msg.data, req)
            except CompilationError as e:
                await ws_current.send_json(
                    {"action": "eval_compilation_error", "text": str(e)}
                )
                continue

            await ws_current.send_json(
                {
                    "action": "eval_result",
                    "stdout": stdout,
                    "traceback": tb,
                    "returned": str(returned),
                }
            )
        else:
            break

    await ws_current.close()

    req.app["eval-session"] = None

    return {}


async def eval_code(
    code: str, req: web.Request
) -> Tuple[str, str, Optional[str]]:
    fake_stdout = io.StringIO()

    to_compile = "async def func():\n" + textwrap.indent(code, "  ")

    glob = {"req": req, "app": req.app}

    try:
        exec(to_compile, glob)
    except Exception as e:
        raise CompilationError(f"{e.__class__.__name__}: {e}")

    func = glob["func"]

    try:
        with redirect_stdout(fake_stdout):
            returned = await func()
    except Exception:
        return fake_stdout.getvalue(), traceback.format_exc(), ""
    else:
        return fake_stdout.getvalue(), "", returned


async def shutdown(app: web.Application) -> None:
    eval_ws = app.get("eval-session", None)

    if eval_ws is not None:
        await eval_ws.close()
