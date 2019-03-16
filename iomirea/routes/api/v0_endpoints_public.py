CHANNELS = r"/channels"
CHANNEL = CHANNELS + r"/{channel_id}"

PINNED_MESSAGES = CHANNEL + r"/pins"
MESSAGES = CHANNEL + r"/messages"
MESSAGE = MESSAGES + r"/{message_id}"

USERS = r"/users"
USER = USERS + r"/{user_id}"
USER_CHANNELS = USER + r"/channels"

FILES = r"/files"
FILE = FILES + r"/{file_id}"

BUGREPORTS = r"/bugreports"
BUGREPORT = BUGREPORTS + r"/{report_id}"

ENDPOINTS = r"/endpoints"
