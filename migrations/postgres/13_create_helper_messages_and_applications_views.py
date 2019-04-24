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
            CREATE VIEW existing_messages AS SELECT * FROM messages WHERE deleted = false;


            CREATE VIEW messages_with_author AS
              SELECT
                msg.id,
                msg.edit_id,
                msg.channel_id,
                msg.content,
                msg.pinned,

                usr.id AS _author_id,
                usr.name AS _author_name,
                usr.bot AS _author_bot
              FROM existing_messages msg
              INNER JOIN users usr
              ON msg.author_id = usr.id;


            CREATE VIEW applications_with_owner AS
              SELECT
                app.id,
                app.redirect_uri,
                app.name,
                app.secret,

                usr.id AS _author_id,
                usr.name AS _author_name
              FROM applications app
              INNER JOIN users usr
              ON app.owner_id = usr.id;
            """
        )
