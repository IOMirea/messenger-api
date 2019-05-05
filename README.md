# IOMirea

<img align="right" height="256" src=".github/media/logo256x256.png"/>

IOMirea is a university project of messenger developed by 6 people.

We were inspired by [Discord](https://discordapp.com), [Telegram](https://telegram.org),
[VKontakte](https://vk.com) and many other messenging platforms.
Main goals of this project are getting practice of developing APIs and working in team.  
This repository contains code related to server side of the project.

Current project website: https://iomirea.ml

Other parts of the project can be found at:
- https://github.com/Fogapod/IOMirea-server: server
- https://github.com/Fogapod/IOMirea-client-android: Android client

# IOMirea-server

## Key features
- RESTful API
- OAuth2 authorization
- User applications registration
- CDN (planned)
- Secret chats and end-to-end message encryption (planned)
- Distribution and load balancing (planned)
- Web interface (planned, currently only registration, login and oauth2 related pages are implemented)

## Running server
The latest version of IOMirea-server is hosted on https://iomirea.ml, you can run your own instance
by installing all dependencies listed in the next section and launching `run.sh` script.  
IOMirea-server runs under nginx as well, example nginx configuration files can be found [here](nginx)

## Documentation
List of endpoints can be found at https://iomirea.ml/api/v0/endpoints

Reference: TODO

### API versioning
IOMirea uses API versioning. Current version is `v0`.  
Note: version `v0` is still in development, expect frequent breaking changes.  
Breaking changes would not happen inside the same API version after release of `v1`.

You can omit API version, latest version will be used in this case (works only under nginx).

### Snowflakes
All objects have unique id, snowflake (Twitter snowflakes). You can extract object creation date
from them.

## Dependencies
IOMirea-server currently runs and tested only under Linux, but things might change in future.  
IOMirea-server is built on top of [aiohttp](https://github.com/aio-libs/aiohttp) library,
uses redis for caching and postgresql as primary database.

Core requirements:
- Configured and running [postgresql](https://www.postgresql.org) server with user `iomirea` and database `iomirea`
- Installed [Redis server](https://redis.io)
- [Python](https://python.org) v3.7+

You can install these dependencies using your system package manager.

Python requirements ar listed in:
- `requirements.txt` (for running server)
- `requirements-dev.txt` (for running and working on server)

You can install python dependencies with pip: `pip install -U -r requirements.txt`

## Contributing
Feel free to open an issue or submit a pull request.  
Note: [pre-commit](https://pre-commit.com) checks should be satisfied before submitting code.
pre-commit can be installed from `requirements-dev.txt` and enabled by running `pre-commit install`
inside project repository. black, flake8, mypy and other tools are used to format and validate code.

## License
Source code is available under GPL v3.0 license, you can get it [here](LICENSE)
