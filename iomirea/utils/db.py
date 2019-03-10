from aiohttp import web


async def ensure_existance(
    req: web.Request, table: str, object_id: int, object_name: str
) -> None:
    record = await req.config_dict["pg_conn"].fetchrow(
        f"SELECT EXISTS(SELECT 1 FROM {table} WHERE id=$1);", object_id
    )

    if not record[0]:
        raise web.HTTPNotFound(reason=f"{object_name} not found")
