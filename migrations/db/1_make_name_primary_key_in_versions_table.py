from migration import Migration


class Migration1(Migration):
    async def up(self, latest: int) -> None:
        if self.conn is None:
            raise RuntimeError("database connection is None")

        await self.conn.execute("ALTER TABLE versions ADD PRIMARY KEY (name);")

    async def down(self) -> None:
        if self.conn is None:
            raise RuntimeError("database connection is None")

        await self.conn.execute(
            "ALTER TABLE versions DROP CONSTRAINT name_pkey;"
        )
