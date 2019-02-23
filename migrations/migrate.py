import os
import sys
import time
import yaml
import asyncio

import asyncpg

from utils import migrate_log


async def main():
    with open('config.yaml') as f:
        postgres_credentials = yaml.load(f)['postgresql']

    connection = await asyncpg.connect(**postgres_credentials)

    migrations = []

    for entry in os.listdir('migrations'):
        if not entry.endswith('.py'):
            continue

        entry = entry[:-3]  # strip '.py'

        version, delim, rest = entry.partition('_')
        if not delim:
            continue

        try:
            version = int(version)
        except ValueError:
            continue

        migrations.append(
            getattr(
                __import__(entry),
                f'Migration{version}'
            )(connection, version)
        )

    try:
        record = await connection.fetchrow(
            "SELECT version FROM versions WHERE name='database';")
        current_version = record['version']
    except asyncpg.exceptions.UndefinedTableError:
        current_version = -1

    migrations = [m for m in migrations if m.version > current_version]

    if not migrations:
        return

    migrations.sort(key=lambda m: m.version)
    latest = migrations[-1].version

    if current_version == -1:  # database is not initialized, run migration 0
        migrations = [migrations[0]]

    migrate_log(
        f'Beginning migrations: {" -> ".join([str(current_version)] + [str(m.version) for m in migrations])}'
    )

    try:
        for m in migrations:
            migrate_log(f'Started  migration {m.version} ...')

            begin = time.time()
            await m._up(latest)
            end = time.time()

            migrate_log(f'Finished migration {m.version} in {round((end - begin) * 1000, 3)}ms')
    finally:
        await connection.close()

    migrate_log(f'Successfully finished {len(migrations)} migrations')

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
