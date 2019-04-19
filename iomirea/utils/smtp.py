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


import ssl
import asyncio
import smtplib

from typing import List, Optional

from models.config import Config
from log import server_log


async def send_message(
    targets: List[str],
    text: str,
    config: Config,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> None:
    if loop is None:
        loop = asyncio.get_running_loop()

    server_log.debug(f"Sending email to {targets}")

    config = config["email-confirmation"]["smtp"]

    for i in ("host", "login", "password"):
        if config.get(i) is None:
            server_log.info(
                f"Bad configuration, unable to send the following email:\n{text}"
            )
            return

    await loop.run_in_executor(
        None,
        _send_message,
        targets,
        text,
        config["host"],
        config["login"],
        config["password"],
    )


def _send_message(
    targets: List[str], text: str, host: str, login: str, password: str
) -> None:
    with smtplib.SMTP_SSL(
        host, port=465, context=ssl.create_default_context()
    ) as smtp:
        smtp.login(login, password)
        for email in targets:
            smtp.sendmail(login, email, text.encode("utf8"))
