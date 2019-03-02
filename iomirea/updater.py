import asyncio
import os

from constants import EXIT_CODE_RESTART_IMMEDIATELY
from log import git_log


async def updater(app):
    git_log.info('Checking for updates')

    try:
        process = await asyncio.create_subprocess_exec(
            'git', 'pull', stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    except FileNotFoundError:
        git_log.info('No git executable found!')
        # TODO: restart?
        raise

    stdout, stderr = await process.communicate()

    if stdout == b'Already up to date.\n':  # no updates
        git_log.info('No updates found')
        return

    if stdout.startswith(b'Updating'):  # update begun
        git_log.info('Updated local files, restarting to apply changes')
        # TODO: call app destructor
        os.sys.exit(EXIT_CODE_RESTART_IMMEDIATELY)

    git_log.info(f'Something unexpected happened: {stdout.decode()}')
    # TODO: git reset --hard
