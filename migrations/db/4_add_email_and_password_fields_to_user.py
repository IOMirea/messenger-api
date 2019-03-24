from migration import Migration


class Migration4(Migration):
    async def up(self, latest: int) -> None:
        if self.conn is None:
            raise RuntimeError("database connection is None")

        await self.conn.execute(
            "ALTER TABLE users ADD COLUMN email TEXT;"
            "ALTER TABLE users ADD COLUMN password BYTEA;"
        )
        await self.conn.execute(
            "UPDATE users SET email = ''; UPDATE users SET password = '';"
        )
        await self.conn.execute(
            "ALTER TABLE users ALTER COLUMN email SET NOT NULL;"
            "ALTER TABLE users ALTER COLUMN password SET NOT NULL;"
        )
