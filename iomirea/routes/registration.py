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
import ssl
import hmac
import base64
import smtplib

from typing import Dict, Any, Union

import bcrypt
import aiohttp_jinja2

from aiohttp import web

from log import server_log
from utils import helpers
from models import converters, checks
from errors import ConvertError


class Email(converters.Converter):
    EMAIL_REGEX = re.compile(r"[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+")

    async def _convert(self, value: str, app: web.Application) -> str:
        value = value.lower()

        if self.EMAIL_REGEX.fullmatch(value) is None:
            raise ConvertError("Bad email pattern", overwrite_response=True)

        return value


def generate_confirmation_code(email: str, user_id: int) -> str:
    code = hmac.new(
        email.encode(), msg=str(user_id).encode(), digestmod="sha1"
    )
    return base64.urlsafe_b64encode(code.digest()).decode()[:-1]


def send_confirmation_code(email: str, code: str, req: web.Request) -> None:
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

    config = req.config_dict["config"]["email-confirmation"]

    with smtplib.SMTP_SSL(
        config["smtp"]["host"], port=465, context=ssl.create_default_context()
    ) as smtp:
        smtp.login(config["smtp"]["login"], config["smtp"]["password"])
        smtp.sendmail(config["smtp"]["login"], email, text.encode("utf8"))


routes = web.RouteTableDef()


@routes.get("/register")
@aiohttp_jinja2.template("auth/register.html")
async def get_register(
    req: web.Request
) -> Union[web.Response, Dict[str, Any]]:
    return {}


@routes.post("/register")
@helpers.query_params(
    {
        "nickname": converters.String(
            strip=True, checks=[checks.LengthBetween(1, 128)]
        ),
        "email": Email(),
        "password": converters.String(checks=[checks.LengthBetween(4, 2048)]),
    },
    from_body=True,
    json_response=False,
)
async def post_register(req: web.Request) -> web.Response:
    query = req["query"]

    user = await req.config_dict["pg_conn"].fetchrow(
        "SELECT id, name, email, email_verified FROM users WHERE name = $1 OR email = $2",
        query["nickname"],
        query["email"],
    )

    if user is not None:
        if user["email_verified"]:
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

    send_confirmation_code(query["email"], code, req)  # TODO: executor?

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
        "UPDATE users SET email_verified = true WHERE id = $1", user_id
    )

    return {"confirmation_status": "Email successfully confirmed!"}
