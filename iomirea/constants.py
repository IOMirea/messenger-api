from enum import Enum


EXIT_CODE_STOP = 1
EXIT_CODE_RESTART = 2
EXIT_CODE_RESTART_IMMEDIATELY = 3

BIGINT64_MAX_POSITIVE = 9223372036854775807

EPOCH_OFFSET = 1546300800
EPOCH_OFFSET_MS = EPOCH_OFFSET * 1000

EXISTING_SCOPES = ("user",)


class ContentType(Enum):
    JSON = "application/json"
    FORM_DATA = "multipart/form-data"
    URLENCODED = "application/x-www-form-urlencoded"
