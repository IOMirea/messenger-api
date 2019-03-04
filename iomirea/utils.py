import aiohttp


async def ensure_existance(app, table, object_id, object_name):
    record = await app['pg_conn'].fetchrow(
        f'SELECT EXISTS(SELECT 1 FROM {table} WHERE id=$1);', object_id)

    if not record[0]:
        raise aiohttp.web.HTTPNotFound(reason=f'{object_name} not found')
