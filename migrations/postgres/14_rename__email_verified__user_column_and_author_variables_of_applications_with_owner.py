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
            ALTER TABLE users RENAME email_verified TO verified;

            DROP VIEW applications_with_owner;  -- CREATE OR REPLACE does not work here

            CREATE VIEW applications_with_owner AS
              SELECT
                app.id,
                app.redirect_uri,
                app.name,
                app.secret,

                usr.id AS _owner_id,
                usr.name AS _owner_name,
                usr.bot AS _owner_bot
              FROM applications app
              INNER JOIN users usr
              ON app.owner_id = usr.id;
            """
        )
