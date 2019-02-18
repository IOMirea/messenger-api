import asyncio
import logging
import traceback

from datetime import datetime

from reporter import send_report



git_log = logging.getLogger('git')


class ErrorReportHandler(logging.StreamHandler):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

    def emit(self, record):
        if record.levelno == logging.ERROR:
            # TODO: write to file
            # TODO: error caching
            self.app.loop.run_in_executor(
                None, send_report, self._format_report_text(record), self.app)

        return super().emit(record)

    def _format_report_text(self, record):
        nl = '\n'

        # TODO: add request formatting
        return (
            f'Exception: {record.msg} ({record.exc_info[0].__name__})\n'
            f'Request: {getattr(record, "request")}\n'
            f'Time: {datetime.utcfromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S UTC")}\n'
            f'\n'
            f'Traceback:\n'
            f'{nl.join(traceback.format_tb(record.exc_info[2], 20))}'
        )

def setup_logging(app):
    # TODO: skip if debug == True
    access_log = logging.getLogger('aiohttp.access')
    access_log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    access_log_format = '{remote_address} "{request_header[User-Agent]}": {first_request_line}: {response_status}'
    handler.setFormatter(logging.Formatter(access_log_format, style='{'))
    access_log.addHandler(handler)

    server_log = logging.getLogger('aiohttp.server')
    handler = ErrorReportHandler(app)
    server_log.addHandler(handler)

    git_log.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[GIT] %(msg)s'))
    git_log.addHandler(handler)
