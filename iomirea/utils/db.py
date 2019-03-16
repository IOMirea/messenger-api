from asyncpg import Record
from aiohttp import web


async def ensure_existance(
    req: web.Request, table: str, object_id: int, object_name: str
) -> Record:
    record = await req.config_dict["pg_conn"].fetchrow(
        f"SELECT * FROM {table} WHERE id=$1", object_id
    )

    if record is None:
        raise web.HTTPNotFound(reason=f"{object_name} not found")

    return record
