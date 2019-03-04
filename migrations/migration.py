import asyncpg


class Migration:
    def __init__(self, config, version, connection=None):
        self.config = config
        self.version = version
        self.conn = connection

    async def _up(self, latest, config: bool):
        await self.up(latest)
        if config:
            self.config["config-version"] = self.version
            return self.config

        await self.conn.execute(
            f"UPDATE versions SET version={self.version} WHERE name='database';"
        )

    async def up(self, latest):
        raise NotImplementedError(f"Migration {self.version}: Not possible to go up")

    async def _down(self, config: bool):
        await self.down()
        if config:
            self.config["config_version"] = self.version
            return self.config

        await self.conn.execute(
            f"UPDATE versions SET version={self.version} WHERE name='database';"
        )

    async def down(self):
        raise NotImplementedError(f"Migration {self.version}: Not possible to go down")
