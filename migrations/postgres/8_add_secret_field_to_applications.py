from migration import PGMigration


class Migration(PGMigration):
    async def up(self, latest: int) -> None:
        await self.conn.execute(
            """
            ALTER TABLE applications ADD COLUMN secret TEXT;
            UPDATE applications SET secret = '';
            ALTER TABLE applications ALTER COLUMN secret SET NOT NULL;

            """
        )
