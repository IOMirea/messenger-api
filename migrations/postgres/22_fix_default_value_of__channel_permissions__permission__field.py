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
            CREATE FUNCTION has_permissions(cid BIGINT, uid BIGINT, perms BIT VARYING) RETURNS BOOLEAN
        AS $has_permissions$
        DECLARE selected_perms BIT VARYING;
        BEGIN
            IF (SELECT owner_id FROM channels WHERE id = cid) = uid THEN
                RETURN true;
            END IF;

            SELECT permissions INTO selected_perms
            FROM channel_permissions
            WHERE channel_id = cid AND user_id = uid;

            IF NOT FOUND THEN
                    RETURN false;
            END IF;

            RETURN perms & selected_perms = perms;
        END;
        $has_permissions$ LANGUAGE plpgsql;
            """
        )
