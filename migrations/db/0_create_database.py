from migration import Migration
from utils import migrate_log


class Migration0(Migration):
    async def _up(self, latest, config):
        filename = 'schema.sql'

        migrate_log(f'Creating database db from file {filename}')

        with open(filename) as f:
            await self.conn.execute(f.read())

        await self.conn.execute(
            f"INSERT INTO versions VALUES ({latest}, 'database');")
