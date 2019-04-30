CHANNELS = r"/channels"
CHANNEL = CHANNELS + r"/{channel_id}"

CHANNEL_RECIPIENTS = CHANNEL + r"/recipients"
CHANNEL_RECIPIENT = CHANNEL_RECIPIENTS + r"/{user_id}"

CHANNEL_PINS = CHANNEL + r"/pins"
CHANNEL_PIN = CHANNEL_PINS + r"/{message_id}"

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
