import hmac
import time
import math
import codecs
import base64
import hashlib

from typing import List

import asyncpg

from constants import EPOCH_OFFSET


def encode_token_user_id(user_id: int) -> str:
    return base64.urlsafe_b64encode(str(user_id).encode()).decode()


def decode_token_user_id(token_start: str) -> int:
    return int(base64.urlsafe_b64decode(token_start.encode()))


def encode_token_creation_offset(offset: int) -> str:
    hex_bytes = codecs.decode(f"{offset:x}".encode(), "hex")

    # weird mypy behaviour, bytes and str type conflict
    return base64.urlsafe_b64encode(hex_bytes).decode()  # type: ignore


def decode_token_creation_offset(token_middle: str) -> int:
    hex_bytes = base64.urlsafe_b64decode(token_middle.encode())

    # weird mypy behaviour, bytes and str type conflict
    return int(codecs.encode(hex_bytes, "hex"), 16)  # type: ignore


def encode_token_hmac_component(
    secret: str, user_id: int, create_offset: int
) -> str:
    to_encrypt = ".".join([str(user_id), str(create_offset)])

    hmac_component = hmac.new(
        secret.encode(), msg=to_encrypt.encode(), digestmod=hashlib.sha1
    ).digest()

    # removing '=' from the end of the line
    return base64.urlsafe_b64encode(hmac_component).decode()[:-1]


async def create_access_token(
    user_id: int,
    secret: str,
    app_id: int,
    scope: List[str],
    conn: asyncpg.Connection,
) -> str:
    token_start = encode_token_user_id(user_id)

    create_offset = math.floor(time.time()) - EPOCH_OFFSET
    token_middle = encode_token_creation_offset(create_offset)

    token_end = encode_token_hmac_component(secret, user_id, create_offset)

    await conn.fetch(
        "INSERT INTO tokens (hmac_component, user_id, app_id, create_offset, scope)"
        "   VALUES ($1, $2, $3, $4, $5)",
        token_end,
        user_id,
        app_id,
        create_offset,
        scope,
    )

    return ".".join([token_start, token_middle, token_end])
