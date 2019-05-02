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

from migration import PGMigration


class Migration(PGMigration):
    async def up(self, latest: int) -> None:
        await self.conn.execute(
            """
            ALTER TABLE messages ADD COLUMN type SMALLINT NOT NULL DEFAULT 0;

            DROP VIEW existing_messages CASCADE;

            CREATE VIEW existing_messages AS
              SELECT
                id,
                edit_id,
                channel_id,
                author_id,
                content,
                encrypted,
                pinned,
                type
              FROM messages
              WHERE deleted = false;

            CREATE VIEW messages_with_author AS
              SELECT
                msg.id,
                msg.edit_id,
                msg.channel_id,
                msg.content,
                msg.pinned,
                msg.type,

                usr.id AS _author_id,
                usr.name AS _author_name,
                usr.bot AS _author_bot
              FROM existing_messages msg
              INNER JOIN users usr
              ON msg.author_id = usr.id;
            """
        )
