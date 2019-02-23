import asyncpg


async def create_postgres_connection(app):
    connection = await asyncpg.connect(
        **app['config'].postgresql)

    app['pg_conn'] = connection

async def close_postgres_connection(app):
    await app['pg_conn'].close()
