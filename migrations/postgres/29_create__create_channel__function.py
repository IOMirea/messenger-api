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
            CREATE FUNCTION create_channel(
              channel_id BIGINT,
              owner_id BIGINT,
              name VARCHAR(128),
              user_ids BIGINT[]
            ) RETURNS channels
            AS $$
            DECLARE
              channel channels;
              sanitized_user_ids BIGINT[] := '{}';
              i BIGINT;
            BEGIN
              FOREACH i IN ARRAY user_ids
              LOOP
                IF i = ANY(sanitized_user_ids) THEN
                        CONTINUE;
                END IF;
                IF NOT (SELECT EXISTS(SELECT 1 FROM users WHERE id = i)) THEN
                        CONTINUE;
                END IF;

                sanitized_user_ids = array_append(sanitized_user_ids, i);
              END LOOP;

              -- owner id might be included by user
              IF NOT (owner_id = ANY(sanitized_user_ids)) THEN
                sanitized_user_ids = array_append(sanitized_user_ids, owner_id);
              END IF;

              INSERT INTO channels (
                id,
                owner_id,
                name,
                user_ids
              ) VALUES (
                channel_id,
                owner_id,
                name,
                sanitized_user_ids
              ) RETURNING * INTO channel;

              FOREACH i IN ARRAY sanitized_user_ids
              LOOP
                UPDATE users SET channel_ids = array_append(channel_ids, channel_id) WHERE id = i;
                INSERT INTO channel_settings (channel_id, user_id) VALUES (channel_id, i);
              END LOOP;

              RETURN channel;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
