from aiohttp import web


async def ensure_existance(req, table, object_id, object_name):
    record = await req.config_dict["pg_conn"].fetchrow(
        f"SELECT EXISTS(SELECT 1 FROM {table} WHERE id=$1);", object_id
    )

    if not record[0]:
        raise web.HTTPNotFound(reason=f"{object_name} not found")
