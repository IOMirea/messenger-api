import asyncpg


class Migration:
    def __init__(self, connection, version):
        self.conn = connection
        self.version = version

    async def _up(self, latest):
        await self.up(latest)
        await self.conn.execute(
            f"UPDATE versions SET version={self.version} WHERE name='database';"
        )

    async def up(self, latest):
        raise NotImplementedError(
            f'Migration {self.version}: Not possible to go up')

    async def _down(self):
        await self.down()
        await self.conn.execute(
            f"UPDATE versions SET version={self.version} WHERE name='database';"
        )

    async def down(self):
        raise NotImplementedError(
            f'Migration {self.version}: Not possible to go down')
