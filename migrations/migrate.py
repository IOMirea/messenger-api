import os
import sys
import time
import yaml
import asyncio
import importlib

import asyncpg

from utils import init_logger, migrate_log

CONFIG_PATH = 'config.yaml'


async def get_config_version(config):
    return config.get('config-version', -1)


async def get_db_version(connection):
    try:
        record = await connection.fetchrow(
            "SELECT version FROM versions WHERE name='database';")
        return record['version']
    except asyncpg.exceptions.UndefinedTableError:
        return -1


def get_migrations(path, config, connection=None):
    migrations = []

    package_path_base = f'{".".join(path.split(os.path.sep)[1:])}.'
    for entry in os.listdir(path):
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
                importlib.import_module(package_path_base + entry),
                f'Migration{version}'
            )(config, version, connection=connection)
        )

    return migrations


async def perform_config_migration(config):
    migrations = get_migrations('migrations/config', config)
    current_version = await get_config_version(config)

    migrations = [m for m in migrations if m.version > current_version]

    if not migrations:
        return config

    migrations.sort(key=lambda m: m.version)
    latest = migrations[-1].version

    migrate_log(
        f'Beginning config migrations: {" -> ".join([str(current_version)] + [str(m.version) for m in migrations])}'
    )

    try:
        for m in migrations:
            migrate_log(f'Started  migration {m.version} ...')

            begin = time.time()
            config = await m._up(latest, True)
            end = time.time()

            migrate_log(f'Finished migration {m.version} in {round((end - begin) * 1000, 3)}ms')
    except Exception as e:
        migrate_log(f'Exception: {e}')
        sys.exit(1)

    migrate_log(f'Successfully finished {len(migrations)} config migrations')

    with open(CONFIG_PATH, 'w') as f:
        f.write(yaml.dump(config, default_flow_style=False))

    return config


async def perform_db_migration(config, connection):
    migrations = get_migrations('migrations/db', config, connection)
    current_version = await get_db_version(connection)

    migrations = [m for m in migrations if m.version > current_version]

    if not migrations:
        return

    migrations.sort(key=lambda m: m.version)
    latest = migrations[-1].version

    if current_version == -1:  # database is not initialized, run migration 0
        migrations = [migrations[0]]

    migrate_log(
        f'Beginning database migrations: {" -> ".join([str(current_version)] + [str(m.version) for m in migrations])}'
    )

    try:
        for m in migrations:
            migrate_log(f'Started  migration {m.version} ...')

            begin = time.time()
            await m._up(latest, False)
            end = time.time()

            migrate_log(f'Finished migration {m.version} in {round((end - begin) * 1000, 3)}ms')
    except Exception as e:
        migrate_log(f'Exception: {e}')
        sys.exit(1)
    finally:
        await connection.close()

    migrate_log(f'Successfully finished {len(migrations)} database migrations')


async def main():
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.load(f)

    init_logger(config)
    new_config = await perform_config_migration(config)
    init_logger(new_config)

    db_connection = await asyncpg.connect(**new_config['postgresql'])

    await perform_db_migration(config, db_connection)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())