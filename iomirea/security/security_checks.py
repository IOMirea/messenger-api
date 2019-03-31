import bcrypt

from utils import access_token


def check_access_token(token: str, client_secret: bytes) -> bool:
    # TODO: token structure check
    start, middle, hmac_component = token.split(".")

    user_id = access_token.decode_token_user_id(start)
    create_offset = access_token.decode_token_creation_offset(middle)

    return hmac_component == access_token.encode_token_hmac_component(
        client_secret, user_id, create_offset
    )


async def check_user_password(password: str, hashed_password: bytes) -> bool:
    return bcrypt.hashpw(password.encode(), hashed_password) == hashed_password
