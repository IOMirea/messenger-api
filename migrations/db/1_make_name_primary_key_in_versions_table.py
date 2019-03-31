from migration import DBMigration


class Migration(DBMigration):
    async def up(self, latest: int) -> None:
        await self.conn.fetch("ALTER TABLE versions ADD PRIMARY KEY (name)")

    async def down(self) -> None:
        await self.conn.fetch("ALTER TABLE versions DROP CONSTRAINT name_pkey")
