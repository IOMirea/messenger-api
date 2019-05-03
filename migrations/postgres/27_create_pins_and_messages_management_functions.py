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
            CREATE FUNCTION create_message(
              mid BIGINT,
              cid BIGINT,
              uid BIGINT,
              content VARCHAR(2048),
              encrypted BOOL DEFAULT FALSE,
              type SMALLINT DEFAULT 0
            ) RETURNS SETOF messages_with_author
            AS $$
              BEGIN
              INSERT INTO messages (
                id,
                channel_id,
                author_id,
                content,
                encrypted,
                type
              ) VALUES (
                mid,
                cid,
                uid,
                content,
                encrypted,
                type
              );

              RETURN QUERY SELECT * FROM messages_with_author WHERE id = mid;
            END;
            $$ LANGUAGE plpgsql;

            CREATE FUNCTION delete_message (mid BIGINT) RETURNS BOOL
            AS $$
            DECLARE
              _pinned BOOL;
              _channel_id BIGINT;
            BEGIN
              DELETE FROM messages
              WHERE id = mid
              RETURNING pinned, channel_id
              INTO _pinned, _channel_id;

            IF NOT FOUND THEN
              RETURN false;
            END IF;

            IF _pinned THEN
              UPDATE channels
              SET pinned_ids = array_remove(pinned_ids, mid)
              WHERE Id = _channel_id;
            END IF;

            RETURN true;

            END;
            $$ LANGUAGE plpgsql;

            CREATE FUNCTION add_channel_pin(mid BIGINT, cid BIGINT) RETURNS BOOL
            AS $$
            BEGIN
              UPDATE messages SET pinned = true WHERE id = mid AND channel_id = cid;

              IF NOT FOUND THEN
                RETURN false;
              END IF;

              UPDATE channels
              SET pinned_ids = array_append(pinned_ids, mid)
              WHERE id = cid AND NOT (mid = ANY(pinned_ids));

              RETURN true;
            END;
            $$ LANGUAGE plpgsql;

            CREATE FUNCTION remove_channel_pin(mid BIGINT, cid BIGINT) RETURNS BOOL
            AS $$
            BEGIN
              UPDATE messages SET pinned = false WHERE id = mid AND channel_id = cid;

              IF NOT FOUND THEN
                RETURN false;
              END IF;

              UPDATE channels SET pinned_ids = array_remove(pinned_ids, mid) WHERE id = cid;

              RETURN true;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
