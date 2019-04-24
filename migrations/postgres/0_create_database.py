from migration import PGMigration
from utils import migrate_log


class Migration(PGMigration):
    async def _up(self, latest: int) -> None:
        filename = "schema.sql"

        migrate_log(f"Creating database db from file {filename}")

        with open(filename) as f:
            await self.conn.execute(f.read())

        await self.conn.fetch(
            f"INSERT INTO versions VALUES ({latest}, 'database')"
        )
