from migration import Migration


class Migration3(Migration):
    async def up(self, latest: int) -> None:
        if self.conn is None:
            raise RuntimeError("database connection is None")

        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bugreports (
                id SERIAL PRIMARY KEY NOT NULL,
                user_id BIGINT,
                report_body TEXT NOT NULL,
                device_info TEXT NOT NULL
            );
            """
        )
