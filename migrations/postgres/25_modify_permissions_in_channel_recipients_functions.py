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
            CREATE OR REPLACE FUNCTION add_channel_user(cid BIGINT, uid BIGINT) RETURNS BOOLEAN
            AS $success$
            DECLARE user_channels BIGINT[];
            BEGIN
              SELECT channel_ids INTO user_channels FROM users WHERE id = uid;

              IF user_channels IS NULL THEN
                RAISE EXCEPTION 'Not such user: %', uid;
                RETURN false;
              END IF;

              IF cid = ANY(user_channels) THEN
                RETURN false;
              END IF;

              IF NOT (SELECT exists(SELECT 1 FROM channels WHERE id = cid)) THEN
                RAISE EXCEPTION 'No such channel: %', cid;
                RETURN false;
              END IF;

              UPDATE users SET channel_ids = array_append(channel_ids, cid) WHERE id = uid;
              UPDATE channels SET user_ids = array_append(user_ids, uid) WHERE id = cid;
              INSERT INTO channel_permissions (channel_id, user_id) VALUES (cid, uid);

              RETURN true;
            END;
            $success$ LANGUAGE plpgsql;

            CREATE OR REPLACE FUNCTION remove_channel_user(cid BIGINT, uid BIGINT) RETURNS BOOLEAN
            AS $success$
            DECLARE user_channels BIGINT[];
            BEGIN
              SELECT channel_ids INTO user_channels FROM users WHERE id = uid;

              IF user_channels IS NULL THEN
                RAISE EXCEPTION 'Not such user: %', uid;
                RETURN false;
              END IF;

              IF NOT(cid = ANY(user_channels)) THEN
                RETURN false;
              END IF;

              IF NOT (SELECT exists(SELECT 1 FROM channels WHERE id = cid)) THEN
                RAISE EXCEPTION 'No such channel: %', cid;
                RETURN false;
              END IF;

              UPDATE users SET channel_ids = array_remove(channel_ids, cid) WHERE id = uid;
              UPDATE channels SET user_ids = array_remove(user_ids, uid) WHERE id = cid;
              DELETE FROM channel_permissions WHERE channel_id = cid AND user_id = uid;

              RETURN true;
            END;
            $success$ LANGUAGE plpgsql;
            """
        )
