"""
IOMirea-server - A server for IOMirea messenger
Copyright (C) 2019  Eugene Ershov

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


import asyncio
import random
import time
import uuid

from typing import Dict, Any, Callable, List

import asyncpg
import bcrypt
import yaml


# script was written for this version
CURRENT_DATABASE_VERSION = 7


# taken from https://www.ssa.gov/oact/babynames/decades/century.html
sample_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Margaret', 'Christopher', 'Karen', 'Daniel', 'Nancy', 'Matthew', 'Lisa', 'Anthony', 'Betty', 'Donald', 'Dorothy', 'Mark', 'Sandra', 'Paul', 'Ashley', 'Steven', 'Kimberly', 'Andrew', 'Donna', 'Kenneth', 'Emily', 'George', 'Carol', 'Joshua', 'Michelle', 'Kevin', 'Amanda', 'Brian', 'Melissa', 'Edward', 'Deborah', 'Ronald', 'Stephanie', 'Timothy', 'Rebecca', 'Jason', 'Laura', 'Jeffrey', 'Helen', 'Ryan', 'Sharon', 'Jacob', 'Cynthia', 'Gary', 'Kathleen', 'Nicholas', 'Amy', 'Eric', 'Shirley', 'Stephen', 'Angela', 'Jonathan', 'Anna', 'Larry', 'Ruth', 'Justin', 'Brenda', 'Scott', 'Pamela', 'Brandon', 'Nicole', 'Frank', 'Katherine', 'Benjamin', 'Samantha', 'Gregory', 'Christine', 'Raymond', 'Catherine', 'Samuel', 'Virginia', 'Patrick', 'Debra', 'Alexander', 'Rachel', 'Jack', 'Janet', 'Dennis', 'Emma', 'Jerry', 'Carolyn', 'Tyler', 'Maria', 'Aaron', 'Heather', 'Henry', 'Diane', 'Jose', 'Julie', 'Douglas', 'Joyce', 'Peter', 'Evelyn', 'Adam', 'Joan', 'Nathan', 'Victoria', 'Zachary', 'Kelly', 'Walter', 'Christina', 'Kyle', 'Lauren', 'Harold', 'Frances', 'Carl', 'Martha', 'Jeremy', 'Judith', 'Gerald', 'Cheryl', 'Keith', 'Megan', 'Roger', 'Andrea', 'Arthur', 'Olivia', 'Terry', 'Ann', 'Lawrence', 'Jean', 'Sean', 'Alice', 'Christian', 'Jacqueline', 'Ethan', 'Hannah', 'Austin', 'Doris', 'Joe', 'Kathryn', 'Albert', 'Gloria', 'Jesse', 'Teresa', 'Willie', 'Sara', 'Billy', 'Janice', 'Bryan', 'Marie', 'Bruce', 'Julia', 'Noah', 'Grace', 'Jordan', 'Judy', 'Dylan', 'Theresa', 'Ralph', 'Madison', 'Roy', 'Beverly', 'Alan', 'Denise', 'Wayne', 'Marilyn', 'Eugene', 'Amber', 'Juan', 'Danielle', 'Gabriel', 'Rose', 'Louis', 'Brittany', 'Russell', 'Diana', 'Randy', 'Abigail', 'Vincent', 'Natalie', 'Philip', 'Jane', 'Logan', 'Lori', 'Bobby', 'Alexis', 'Harry', 'Tiffany', 'Johnny', 'Kayla']

sample_channel_adjectives = ["cool", "awesome", "dank", "secret", "private", "public", "business", "meme", "game", "unique", "popular", "unpopular", "weird", "creative", "programming", "fun", "super", "mega"]

sample_message_words = ["meme", "bump", "sage"]

sample_file_mimes = range(10)


def profiler(task_name: str) -> Callable[[Any], Any]:
    def decorator(fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            print(f">{task_name}")
            start = time.time()
            result = await fn(*args, **kwargs)  # type: ignore
            print(f"<Finished in {round((time.time() - start)*1000, 3)}ms")
            return result

        return wrapper

    return decorator


def get_db_credentials() -> Dict[str, Any]:
    with open("config.yaml") as config:
        data = yaml.load(config, Loader=yaml.SafeLoader)

        return data["postgresql"]


class RandObject:
    def __init__(self, id: int):
        self.id = id

        self._generate_self()

    def _generate_self(self) -> None:
        raise NotImplementedError


class User(RandObject):
    def _generate_self(self) -> None:
        self.channel_ids: List[int] = []

        if self.id == 0:
            self.name = "Test Bob"
            self.channel_ids = list(range(10))
            self.bot = False
            self.email = 'test-bob@gmail.com'

        else:
            self.name = random.choice(sample_names)

            for i in range(random.randrange(10)):
                channel_id = random.randrange(100)
                if channel_id not in self.channel_ids:
                    self.channel_ids.append(channel_id)

            self.bot = random.random() > 0.5
            self.email = f'{self.name}{self.id}@gmail.com'

        self.password = bcrypt.hashpw(self.name.encode(), bcrypt.gensalt())


class Message(RandObject):
    def _generate_self(self) -> None:
        self.channel_id = random.randrange(100)
        self.author_id = random.choice(list(users.keys()))
        self.content = random.choice(sample_message_words)[:2048]
        self.encrypted = False
        self.pinned = random.random() > 0.5
        self.edited = random.random() > 0.5
        self.deleted = False


class Channel(RandObject):
    def _generate_self(self) -> None:
        self.name = ""
        for i in range(random.randrange(1, 10)):
            next_adjective = random.choice(sample_channel_adjectives)
            if next_adjective not in self.name:
                self.name += f"{next_adjective} "

        self.name = (f"{self.name}channel")[:128]

        self.user_ids: List[int] = []
        global users
        for user in users.values():
            if self.id in user.channel_ids:
                self.user_ids.append(user.id)

        global messages
        self.pinned_ids: List[int] = []
        for message in messages.values():
            if message.channel_id == self.id and message.pinned:
                self.pinned_ids.append(message.id)


class File(RandObject):
    def _generate_self(self) -> None:
        global messages
        self.message_id = random.choice(list(messages.keys()))
        self.channel_id = messages[self.message_id].channel_id
        self.name = "md5 hash?"
        self.mime = random.choice(sample_file_mimes)
        self.hash = uuid.uuid4()


# global objects
users = {}
channels = {}
messages = {}
files = {}


@profiler("Creating users")
async def populate_users(conn: asyncpg.Connection) -> None:
    global users
    query = await conn.prepare(
        "INSERT INTO users (id, name, channel_ids, bot, email, password) VALUES ($1, $2, $3, $4, $5, $6)"
    )

    for i in range(100):
        user = User(i)
        users[i] = user
        await query.fetch(user.id, user.name, user.channel_ids, user.bot, user.email, user.password)


@profiler("Creating messages")
async def populate_messages(conn: asyncpg.Connection) -> None:
    global messages
    query = await conn.prepare(
        "INSERT INTO messages (id, channel_id, author_id, content, encrypted, pinned, edited, deleted) VALUES($1, $2, $3, $4, $5, $6, $7, $8)"
    )

    for i in range(200):
        message = Message(i)
        messages[i] = message
        await query.fetch(
            message.id,
            message.channel_id,
            message.author_id,
            message.content,
            message.encrypted,
            message.pinned,
            message.edited,
            message.deleted,
        )


@profiler("Creating channels")
async def populate_channels(conn: asyncpg.Connection) -> None:
    global channels
    query = await conn.prepare(
        "INSERT INTO channels (id, name, user_ids, pinned_ids) VALUES($1, $2, $3, $4)"
    )

    for i in range(100):
        channel = Channel(i)
        channels[i] = channel
        await query.fetch(
            channel.id, channel.name, channel.user_ids, channel.pinned_ids
        )


@profiler("Creating files")
async def populate_files(conn: asyncpg.Connection) -> None:
    global files
    query = await conn.prepare(
        "INSERT INTO files (id, message_id, channel_id, name, mime, hash) VALUES($1, $2, $3, $4, $5, $6)"
    )

    for i in range(100):
        file = File(i)
        files[i] = file
        await query.fetch(
            file.id,
            file.message_id,
            file.channel_id,
            file.name,
            file.mime,
            file.hash,
        )


async def is_db_filled(conn: asyncpg.Connection) -> bool:
    return await conn.fetchval(
        "SELECT EXISTS(SELECT FROM users WHERE id=0 AND name='Test Bob')"
    )


async def check_db_version(conn: asyncpg.Connection) -> bool:
    db_version = await conn.fetchval(
        "SELECT version FROM versions WHERE name = 'database'"
    )

    if db_version != CURRENT_DATABASE_VERSION:
        answer = ''
        while True:
            if answer.lower() == 'y':
                return True
            elif answer.lower() == 'n':
                return False

            answer = input(
                f"Database version is {db_version} while script version is {CURRENT_DATABASE_VERSION}.\n"
                f"This might damage database. Do you want to continue? (y/n) "
            )

    return True


async def main() -> None:
    conn = await asyncpg.connect(**get_db_credentials())
    if not await check_db_version(conn):
        return

    if await is_db_filled(conn):
        print(
            "Database is already filled. You should clear tables before running this script\n"
            "Drop command: DELETE FROM users; DELETE FROM messages; DELETE FROM channels; DELETE FROM files;"
        )
        return

    await populate_users(conn)
    await populate_messages(conn)
    await populate_channels(conn)
    await populate_files(conn)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
