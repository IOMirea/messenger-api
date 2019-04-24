from migration import PGMigration


class Migration(PGMigration):
    async def up(self, latest: int) -> None:
        await self.conn.fetch(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                hmac_component TEXT NOT NULL,
                user_id BIGINT NOT NULL,
                app_id BIGINT NOT NULL,
                create_offset INT NOT NULL,
                scope TEXT[] NOT NULL
            )
            """
        )

        await self.conn.fetch(
            """
            CREATE TABLE IF NOT EXISTS applications (
                redirect_uri TEXT PRIMARY KEY NOT NULL,
                id BIGINT,
                name VARCHAR(256)
            )
            """
        )
