from migration import PGMigration


class Migration(PGMigration):
    async def up(self, latest: int) -> None:
        await self.conn.fetch(
            """
            CREATE TABLE IF NOT EXISTS bugreports (
                id SERIAL PRIMARY KEY NOT NULL,
                user_id BIGINT,
                report_body TEXT NOT NULL,
                device_info TEXT NOT NULL
            )
            """
        )
