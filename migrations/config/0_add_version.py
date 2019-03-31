from migration import ConfigMigration


class Migration(ConfigMigration):
    async def up(self, latest: int) -> None:
        pass
