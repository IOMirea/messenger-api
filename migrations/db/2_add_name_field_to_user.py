from migration import Migration


class Migration2(Migration):
    async def up(self, latest: int) -> None:
        if self.conn is None:
            raise RuntimeError("database connection is None")

        await self.conn.execute(
            "ALTER TABLE users ADD COLUMN name VARCHAR(128);"
        )
        await self.conn.execute("UPDATE users SET name = 'User';")
        await self.conn.execute(
            "ALTER TABLE users ALTER COLUMN name SET NOT NULL;"
        )
