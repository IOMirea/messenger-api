from migration import PGMigration


class Migration(PGMigration):
    async def up(self, latest: int) -> None:
        await self.conn.execute(
            "ALTER TABLE applications DROP CONSTRAINT applications_pkey;"
            "ALTER TABLE applications ADD PRIMARY KEY (id);"
            "ALTER TABLE applications ALTER COLUMN id SET NOT NULL;"
            "ALTER TABLE applications ALTER COLUMN name SET NOT NULL;"
        )
