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


import os
import logging
import traceback

from typing import Optional, IO

import aiohttp

from datetime import datetime

from reporter import send_report


# public
git_log = logging.getLogger("git")
server_log = logging.getLogger("server")

# internal
_access_log = logging.getLogger("aiohttp.access")


class AccessLogger(aiohttp.abc.AbstractAccessLogger):
    def log(
        self,
        req: aiohttp.web.BaseRequest,
        res: aiohttp.web.StreamResponse,
        time: float,
    ) -> None:
        remote = req.headers.get("X-Forwarded-For", req.remote)
        user_agent = req.headers.get("User-Agent", "-")

        # TODO: customizable format?
        self.logger.info(
            f'{remote} "{user_agent}": {req.method} {req.path}->{res.status}'
        )


class RequestErrorRepoter(logging.StreamHandler):
    def __init__(
        self, app: aiohttp.web.Application, **kwargs: Optional[IO[str]]
    ):
        super().__init__(**kwargs)
        self.app = app

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno == logging.ERROR:
            # TODO: write to file
            # TODO: error caching
            if self.app["args"].debug:
                return
            else:
                self.app.loop.run_in_executor(
                    None,
                    send_report,
                    self._format_report_text(record),
                    self.app,
                )

    def _format_report_text(self, record: logging.LogRecord) -> str:
        request = getattr(record, "request")

        if record.exc_info is not None:
            exc_name = record.exc_info[0].__class__.__name__
            exc_text = str(record.exc_info[1])
            exc_traceback = "\n".join(
                traceback.format_tb(record.exc_info[2], 20)
            )
        else:
            exc_name = "Unknown exception"
            exc_text = ""
            exc_traceback = ""

        return (
            f"Comment: {record.msg}\n"
            f"Exception: {exc_name}: {exc_text}\n"
            f"Request: {request.method} {request.url}\n"
            f'Headers: {" ".join(f"{k}:{v}" for k, v in request.headers.items())}\n'
            f'Time: {datetime.utcfromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S UTC")}\n'
            f"IP: {request.remote}\n"
            f"\n"
            f"Traceback:\n"
            f"{exc_traceback}"
        )


class RequestErrorFileHandler(logging.FileHandler):
    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno == logging.ERROR:
            super().emit(record)


def setup_logging(app: aiohttp.web.Application) -> None:
    log_config = app["config"]["logging"]

    logging_path_base = log_config["logging-folder"] + os.path.sep

    if not os.path.exists(logging_path_base):
        os.makedirs(logging_path_base)

    # create handlers
    stream_handler = logging.StreamHandler()
    access_stream_handler = logging.StreamHandler()

    # TODO: use separate file? (access-log-file)
    # access_file_handler = logging.FileHandler(
    #    logging_path_base + log_config["common-log-file"]
    # )

    # common_file_handler = logging.FileHandler(
    #    logging_path_base + log_config["common-log-file"]
    # )

    # server_file_handler = logging.FileHandler(
    #    logging_path_base + log_config["server-log-file"]
    # )

    # server_error_file_handler = RequestErrorFileHandler(
    #    logging_path_base + log_config["error-log-file"]
    # )

    # set handler formatting
    access_log_format = log_config["basic-log-format"] + "{msg}"

    access_stream_handler.setFormatter(
        logging.Formatter(
            access_log_format,
            datefmt=log_config["basic-time-format"],
            style="{",
        )
    )

    # access_file_handler.setFormatter(
    #    logging.Formatter(
    #        access_log_format,
    #        datefmt=log_config["basic-time-format"],
    #        style="{",
    #    )
    # )

    stream_handler.setFormatter(
        logging.Formatter(
            log_config["basic-log-format"] + "{msg}",
            style="{",
            datefmt=log_config["basic-time-format"],
        )
    )

    # common_file_handler.setFormatter(
    #    logging.Formatter(
    #        log_config["basic-log-format"] + "{msg}",
    #        style="{",
    #        datefmt=log_config["basic-time-format"],
    #    )
    # )

    # server_file_handler.setFormatter(
    #    logging.Formatter(
    #        log_config["basic-log-format"] + "{msg}",
    #        style="{",
    #        datefmt=log_config["basic-time-format"],
    #    )
    # )

    # apply handlers
    _access_log.addHandler(access_stream_handler)
    # _access_log.addHandler(access_file_handler)

    # server_log.addHandler(common_file_handler)
    # server_log.addHandler(server_file_handler)
    server_log.addHandler(stream_handler)
    # server_log.addHandler(server_error_file_handler)
    server_log.addHandler(RequestErrorRepoter(app))

    # git_log.addHandler(common_file_handler)
    git_log.addHandler(stream_handler)

    # set levels
    _access_log.setLevel(logging.INFO)
    server_log.setLevel(logging.DEBUG if app["args"].debug else logging.INFO)
    git_log.setLevel(logging.INFO)
