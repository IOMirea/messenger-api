from migration import PGMigration


class Migration(PGMigration):
    async def up(self, latest: int) -> None:
        await self.conn.fetch("ALTER TABLE users ADD COLUMN name VARCHAR(128)")
        await self.conn.fetch("UPDATE users SET name = 'User'")
        await self.conn.fetch(
            "ALTER TABLE users ALTER COLUMN name SET NOT NULL"
        )
