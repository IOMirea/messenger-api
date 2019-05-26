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
            CREATE OR REPLACE FUNCTION create_channel(
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
                IF i = owner_id THEN
                  INSERT INTO channel_settings (channel_id, user_id, permissions) VALUES (channel_id, i, 65535::bit(16));
                ELSE
                  INSERT INTO channel_settings (channel_id, user_id) VALUES (channel_id, i);
                END IF;
              END LOOP;

              RETURN channel;
            END;
            $$ LANGUAGE plpgsql;

            -- update existing owners (sorry!!)
            UPDATE channel_settings AS s
            SET permissions = 65535::bit(16)
            FROM channels AS c
            WHERE c.owner_id = s.user_id AND c.id = s.channel_id;

            -- replace channel_permissions reference
            CREATE OR REPLACE FUNCTION add_channel_user(cid BIGINT, uid BIGINT) RETURNS BOOL
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
              INSERT INTO channel_settings (channel_id, user_id) VALUES (cid, uid);

              RETURN true;
            END;
            $success$ LANGUAGE plpgsql;
            """
        )
