import bcrypt


async def check_user_password(password: str, hashed_password: bytes) -> bool:
    return bcrypt.hashpw(password.encode(), hashed_password) == hashed_password
