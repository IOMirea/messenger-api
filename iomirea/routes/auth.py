"""
IOMirea-server - A server for IOMirea messenger
Copyright (C) 2019  Eugene Ershov

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


import re
import uuid
import hmac
import base64

from typing import Dict, Any, Union

import bcrypt
import aiohttp_jinja2

from aiohttp_session import new_session, get_session
from aiohttp import web

from utils import helpers, smtp
from models import converters, checks
from errors import ConvertError
from db.redis import REMOVE_EXPIRED_COOKIES
from security.security_checks import check_user_password
from constants import ContentType


class Email(converters.Converter):
    EMAIL_REGEX = re.compile(r"[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+")

    async def _convert(self, value: str, app: web.Application) -> str:
        value = value.lower()

        if self.EMAIL_REGEX.fullmatch(value) is None:
            raise ConvertError("Bad email pattern", overwrite_response=True)

        return value


def generate_confirmation_code(email: str, user_id: int) -> str:
    code = hmac.new(
        email.encode(), msg=str(user_id).encode(), digestmod="sha512"
    )
    return base64.urlsafe_b64encode(code.digest()).decode()[:-2]


async def send_email_confirmation_code(
    email: str, code: str, req: web.Request
) -> None:
    relative_url = (
        req.app.router["confirm_email"].url_for().with_query({"code": code})
    )
    url = req.url.join(relative_url)

    text = (
        f"Subject: IOMirea registration confirmation\n\n"
        f"This email was used to register on IOMirea service.\n"
        f"If you did not do it, please, ignore this message.\n\n"
        f"To finish registration, use this url: {url}"
    )

    await smtp.send_message([email], text, req.config_dict["config"])


async def send_password_reset_code(
    email: str, code: str, user_name: str, req: web.Request
) -> None:
    relative_url = (
        req.app.router["reset_password"].url_for().with_query({"code": code})
    )

    url = req.url.join(relative_url)

    text = (
        f"Subject: IOMirea password reset\n\n"
        f"Password reset requested for account {user_name}\n"
        f"Use this url to reset your password: {url}\n"
        f"If you did not request reset, ignore this email"
    )

    await smtp.send_message([email], text, req.config_dict["config"])


routes = web.RouteTableDef()


@routes.get("/register")
@aiohttp_jinja2.template("auth/register.html")
async def get_register(
    req: web.Request
) -> Union[web.Response, Dict[str, Any]]:
    return {}


@routes.post("/register")
@helpers.body_params(
    {
        "nickname": converters.String(
            strip=True, checks=[checks.LengthBetween(1, 128)]
        ),
        "email": Email(),
        "password": converters.String(checks=[checks.LengthBetween(4, 2048)]),
    },
    content_types=[ContentType.FORM_DATA, ContentType.URLENCODED],
    json_response=False,
)
async def post_register(req: web.Request) -> web.Response:
    query = req["body"]

    user = await req.config_dict["pg_conn"].fetchrow(
        "SELECT id, name, email, verified FROM users WHERE name = $1 OR email = $2",
        query["nickname"],
        query["email"],
    )

    if user is not None:
        if user["verified"]:
            if user["name"] == query["nickname"]:
                raise web.HTTPBadRequest(
                    reason="Nickname is already registered"
                )
            elif user["email"] == query["email"]:
                raise web.HTTPBadRequest(reason="Email is already registered")

        code = generate_confirmation_code(user["email"], user["id"])

        if (
            await req.config_dict["rd_conn"].execute(
                "GET", f"email_confirm_code:{code}"
            )
            is None
        ):  # user confirmation code expired
            await req.config_dict["pg_conn"].fetch(
                "DELETE FROM users WHERE id = $1", user["id"]
            )
        else:
            raise web.HTTPBadRequest(
                reason="User with this name or email is in registration process"
            )

    # TODO: propper password and login checks

    new_user_id = req.config_dict["sf_gen"].gen_id()

    code = generate_confirmation_code(query["email"], new_user_id)

    await req.config_dict["rd_conn"].execute(
        "SETEX", f"email_confirm_code:{code}", 86400, new_user_id
    )

    await req.config_dict["pg_conn"].fetch(
        "INSERT INTO USERS (id, name, bot, email, password) VALUES($1, $2, $3, $4, $5)",
        new_user_id,
        query["nickname"],
        False,
        query["email"],
        bcrypt.hashpw(query["password"].encode(), bcrypt.gensalt()),
    )

    await send_email_confirmation_code(query["email"], code, req)

    helpers.redirect(req, "email_sent")


@routes.get("/register/email-sent", name="email_sent")
@aiohttp_jinja2.template("auth/email_sent.html")
async def get_email_send(
    req: web.Request
) -> Union[web.Response, Dict[str, Any]]:
    return {}


@routes.get("/register/confirm", name="confirm_email")
@helpers.query_params({"code": converters.String()}, json_response=False)
@aiohttp_jinja2.template("auth/email_confirm.html")
async def get_email_confirm(
    req: web.Request
) -> Union[web.Response, Dict[str, Any]]:
    user_id = await req.config_dict["rd_conn"].execute(
        "GET", f"email_confirm_code:{req['query']['code']}"
    )
    await req.config_dict["rd_conn"].execute(
        "DEL", f"email_confirm_code:{req['query']['code']}"
    )

    if user_id is None:
        return {
            "confirmation_status": (
                "Wrong confirmation code!\n\n"
                "Please, let us know if you have registration problems.\n"
                "Notice: email confirmation codes are valid for 24 hours"
            )
        }

    user_id = int(user_id.decode())

    # TODO: check code / handle wrong user_id errors?
    await req.config_dict["pg_conn"].fetch(
        "UPDATE users SET verified = true WHERE id = $1", user_id
    )

    session = await new_session(req)
    session["user_id"] = user_id

    # WARING: monkeypatch
    # TODO: use wrapper to get identity after cookie is saved
    session._identity = uuid.uuid4().hex

    await req.config_dict["rd_conn"].execute(
        "SADD", f"user_cookies:{user_id}", session.identity
    )

    return {"confirmation_status": "Email successfully confirmed!"}


@routes.get("/login", name="login")
@helpers.query_params({"redirect": converters.String(default=None)})
@aiohttp_jinja2.template("auth/login.html")
async def get_login(req: web.Request) -> Union[web.Response, Dict[str, Any]]:
    redirect = req["query"]["redirect"]

    return {
        "redirect": f"{req.scheme}://{req.host}"
        if redirect is None
        else redirect
    }


@routes.post("/login")
@helpers.body_params(
    {
        "login": Email(),
        "password": converters.String(checks=[checks.LengthBetween(4, 2048)]),
    },
    unique=True,
    content_types=[ContentType.FORM_DATA, ContentType.URLENCODED],
)
async def post_login(req: web.Request) -> web.Response:
    query = req["body"]

    record = await req.config_dict["pg_conn"].fetchrow(
        "SELECT id, password FROM users WHERE email = $1", query["login"]
    )

    if record is None:
        raise web.HTTPUnauthorized()

    if not await check_user_password(query["password"], record["password"]):
        raise web.HTTPUnauthorized()

    session = await new_session(req)
    session["user_id"] = record["id"]

    # WARING: monkeypatch
    # TODO: use wrapper to get identity after cookie is saved
    session._identity = uuid.uuid4().hex

    await req.config_dict["rd_conn"].execute(
        "EVAL", REMOVE_EXPIRED_COOKIES, 1, record["id"]
    )

    await req.config_dict["rd_conn"].execute(
        "SADD", f"user_cookies:{record['id']}", session.identity
    )

    return web.Response()


@routes.get("/logout", name="logout")
async def logout(req: web.Request) -> web.Response:
    session = await get_session(req)
    if session.get("user_id") is None:
        raise web.HTTPForbidden()

    await req.config_dict["rd_conn"].execute(
        "SREM", f"user_cookies:{session['user_id']}", session.identity
    )

    session.invalidate()

    return web.HTTPFound(req.app.router["login"].url_for())


@routes.get("/reset-password")
@helpers.query_params({"code": converters.String()}, unique=True)
@aiohttp_jinja2.template("auth/reset_password.html")
async def reset_password(
    req: web.Request
) -> Union[web.Response, Dict[str, Any]]:
    query = req["query"]

    user_id = await req.config_dict["rd_conn"].execute(
        "GET", f"password_reset_code:{query['code']}"
    )

    if user_id is None:
        return web.HTTPUnauthorized(reason="Bad or expired code")

    return {"code": query["code"]}


@routes.post("/reset-password", name="reset_password")
@helpers.body_params(
    {
        "email": Email(default=None),
        "code": converters.String(default=None),
        "password": converters.String(
            checks=[checks.LengthBetween(4, 2048)], default=None
        ),
    },
    unique=True,
    content_types=[ContentType.FORM_DATA, ContentType.URLENCODED],
)
async def post_reset_password(req: web.Request) -> web.Response:
    query = req["body"]

    if query["email"]:
        user = await req.config_dict["pg_conn"].fetchrow(
            "SELECT id, email, name FROM users WHERE email = $1",
            query["email"],
        )

        if user is None:
            raise web.HTTPUnauthorized(reason="Bad email")

        new_code = generate_confirmation_code(user["email"], user["id"])

        await req.config_dict["rd_conn"].execute(
            "SETEX", f"password_reset_code:{new_code}", 43200, user["id"]
        )

        await send_password_reset_code(
            user["email"], new_code, user["name"], req
        )

        return web.Response()
    elif query["code"] and query["password"]:
        # TODO: password checks

        user_id = await req.config_dict["rd_conn"].execute(
            "GET", f"password_reset_code:{query['code']}"
        )

        if user_id is None:
            raise web.HTTPBadRequest(reason="Invalid code")

        await req.config_dict["rd_conn"].execute(
            "DEL", f"password_reset_code:{query['code']}"
        )

        # update password
        password_hash = bcrypt.hashpw(
            query["password"].encode(), bcrypt.gensalt()
        )

        await req.config_dict["pg_conn"].fetch(
            "UPDATE users SET password = $1 WHERE id = $2",
            password_hash,
            int(user_id),
        )

        # clear all user cookies
        user_cookies = await req.config_dict["rd_conn"].execute(
            "SMEMBERS", f"user_cookies:{user_id}"
        )

        await req.config_dict["rd_conn"].execute(
            "DEL",
            f"user_cookies:{user_id}",
            *user_cookies,
            f"user_cookies:{user_id}",
        )

        # create new session
        session = await new_session(req)
        session["user_id"] = int(user_id)

        # WARING: monkeypatch
        # TODO: use wrapper to get identity after cookie is saved
        session._identity = uuid.uuid4().hex

        await req.config_dict["rd_conn"].execute(
            "SADD", f"user_cookies:{session['user_id']}", session.identity
        )
        return web.Response()
    else:
        raise web.HTTPBadRequest()
