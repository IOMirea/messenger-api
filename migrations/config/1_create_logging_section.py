from migration import ConfigMigration


class Migration(ConfigMigration):
    async def up(self, latest: int) -> None:
        self.config["logging"] = {
            "basic-log-format": "[{asctime} {levelname}]{name}: ",
            "basic-time-format": "%I:%M:%S",
            "logging-folder": "logs",
            "common-log-file": "common.log",
            "server-log-file": "server.log",
            "error-log-file": "errors.log",
            "migration-log-file": "migration.log",
        }

    async def down(self) -> None:
        self.config.pop("logging")
