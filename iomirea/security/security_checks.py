import asyncpg
import bcrypt

from utils import auth
from log import server_log


def check_access_token(token: str, client_secret: str) -> bool:
    # TODO: token structure check
    start, middle, hmac_component = token.split(".")

    user_id = auth.decode_token_user_id(start)
    create_offset = auth.decode_token_creation_offset(middle)

    return hmac_component == auth.encode_token_hmac_component(
        client_secret, user_id, create_offset
    )


async def check_user_password(
    user_id: int, password: str, conn: asyncpg.Connection
) -> bool:
    saved_hash = await conn.fetchval(
        "SELECT password FROM users WHERE id=$1", user_id
    )

    if saved_hash is None:
        server_log.warn(
            f"Password check: user {user_id} not found in database"
        )
        return False

    return bcrypt.hashpw(password.encode(), saved_hash) == saved_hash
