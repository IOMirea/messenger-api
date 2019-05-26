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
            DROP FUNCTION delete_message;

            CREATE FUNCTION delete_message(
              cid BIGINT,
              mid BIGINT
            ) RETURNS BOOL
            AS $$
            DECLARE
              _pinned BOOL;
            BEGIN
              DELETE FROM messages
              WHERE id = mid AND channel_id = cid
              RETURNING pinned
              INTO _pinned;

              IF NOT FOUND THEN
                RETURN false;
              END IF;

              IF _pinned THEN
                UPDATE channels
                SET pinned_ids = array_remove(pinned_ids, mid)
                WHERE id = cid;
              END IF;

              RETURN true;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
