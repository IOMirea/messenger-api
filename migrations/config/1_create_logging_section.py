from migration import Migration


class Migration1(Migration):
    async def up(self, latest):
        self.config['logging'] = {
            'basic-log-format': '[{asctime} {levelname}]{name}: ',
            'basic-time-format': '%I:%M:%S',
            'logging-folder': 'logs',
            'common-log-file': 'common.log',
            'server-log-file': 'server.log',
            'error-log-file': 'errors.log',
            'migration-log-file': 'migration.log'
        }

    async def down(self):
        self.config.pop('logging')
