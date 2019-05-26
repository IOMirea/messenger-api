-- TABLES --
CREATE TABLE versions (
	version SMALLINT NOT NULL,
	name TEXT PRIMARY KEY NOT NULL
);

CREATE TABLE channels (
	id BIGINT PRIMARY KEY NOT NULL,
	owner_id BIGINT NOT NULL,
	name VARCHAR(128),
	user_ids BIGINT[] NOT NULL,
	pinned_ids BIGINT[] NOT NULL DEFAULT ARRAY[]::BIGINT[]
);

CREATE TABLE users (
	id BIGINT PRIMARY KEY NOT NULL,
	name VARCHAR(128) NOT NULL,
	channel_ids BIGINT[] NOT NULL DEFAULT ARRAY[]::BIGINT[],
	bot BOOL NOT NULL,
	email TEXT NOT NULL UNIQUE,
	password BYTEA NOT NULL,
	verified BOOL NOT NULL DEFAULT false
);


CREATE TABLE applications (
	id BIGINT PRIMARY KEY NOT NULL,
	owner_id BIGINT NOT NULL,
	secret TEXT NOT NULL,
	redirect_uri TEXT NOT NULL,
	name VARCHAR(256) NOT NULL,
	
	FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);


/* Message types
 * 0: text
 * 1: channel create
 * 2: channel name update
 * 3: channel icon update
 * 4: channel pin add
 * 5: channel pin remove
 * 6: recipient add
 * 7: recipient remove
 */

CREATE TABLE messages (
	id BIGINT PRIMARY KEY NOT NULL,
	edit_id BIGINT,
	channel_id BIGINT NOT NULL,
	author_id BIGINT NOT NULL,
	content VARCHAR(2048) NOT NULL,
	encrypted BOOL NOT NULL DEFAULT false,
	pinned BOOL NOT NULL DEFAULT false,
	deleted BOOL NOT NULL DEFAULT false,
	type SMALLINT NOT NULL DEFAULT 0,
	
	FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE RESTRICT,
	FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE RESTRICT
);


/* Permissions bits
 * 0:   modify channel
 * 1:   invite members
 * 2:   kick members
 * 3:   ban members
 * 4:   modify members
 */

CREATE TABLE channel_settings (
	user_id BIGINT NOT NULL,
	channel_id BIGINT NOT NULL,
	permissions BIT VARYING NOT NULL DEFAULT 0::bit(16),
	last_read_id BIGINT,

	FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
	FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
	FOREIGN KEY (last_read_id) REFERENCES messages(id) ON DELETE SET NULL
);


CREATE TABLE files (
	id BIGINT PRIMARY KEY NOT NULL,
	message_id BIGINT NOT NULL,
	channel_id BIGINT NOT NULL,
	name VARCHAR(128) NOT NULL,
	mime SMALLINT NOT NULL,
	hash UUID NOT NULL,
	
	FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE RESTRICT,
	FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE RESTRICT
);

CREATE TABLE bugreports (
	id SERIAL PRIMARY KEY NOT NULL,
	user_id BIGINT,
	report_body TEXT NOT NULL,
	device_info TEXT NOT NULL,
	
	FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE tokens (
	hmac_component TEXT NOT NULL,
	user_id BIGINT NOT NULL,
	app_id BIGINT NOT NULL,
	create_offset INT NOT NULL,
	scope TEXT[] NOT NULL,
	
	FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
	FOREIGN KEY (app_id) REFERENCES applications(id) ON DELETE CASCADE
);


-- INDEXES --
CREATE INDEX messages_channel_index ON messages(channel_id);

CREATE UNIQUE INDEX users_unique_email_index ON users(email);

CREATE INDEX tokens_hmac_component_index ON tokens(hmac_component);

CREATE INDEX channel_settings_user_id_index ON channel_settings(user_id);

CREATE INDEX channel_settings_channel_id_index ON channel_settings(channel_id);


-- VIEWS --
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


-- FOREIGN KEYS --
ALTER TABLE channels ADD CONSTRAINT channels_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(id);


-- FUNCTIONS --

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

-- Warning: function does not perform access checks
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


CREATE FUNCTION delete_message(mid BIGINT) RETURNS BOOL
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

CREATE FUNCTION add_channel_user(cid BIGINT, uid BIGINT) RETURNS BOOL
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

CREATE FUNCTION remove_channel_user(cid BIGINT, uid BIGINT) RETURNS BOOL
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
	DELETE FROM channel_settings WHERE channel_id = cid AND user_id = uid;

        RETURN true;
END;
$success$ LANGUAGE plpgsql;

-- Warning: function does not check amount of pins in channel
-- Warning: function does not check permissions
CREATE FUNCTION add_channel_pin(mid BIGINT, cid BIGINT) RETURNS BOOL
AS $$
BEGIN
	-- channel match condition to verify channel as well
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

-- Warning: function does not check permissions
CREATE FUNCTION remove_channel_pin(mid BIGINT, cid BIGINT) RETURNS BOOL
AS $$
BEGIN
	-- channel match condition to verify channel as well
        UPDATE messages SET pinned = false WHERE id = mid AND channel_id = cid;

        IF NOT FOUND THEN
                RETURN false;
        END IF;

        UPDATE channels SET pinned_ids = array_remove(pinned_ids, mid) WHERE id = cid;

        RETURN true;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION has_permissions(cid BIGINT, uid BIGINT, perms BIT VARYING) RETURNS BOOL
AS $has_permissions$
DECLARE selected_perms BIT VARYING;
BEGIN
	IF (SELECT owner_id FROM channels WHERE id = cid) = uid THEN
		RETURN true;
	END IF;

	SELECT permissions INTO selected_perms
	FROM channel_settings
	WHERE channel_id = cid AND user_id = uid;

	IF NOT FOUND THEN
		RETURN false;
	END IF;

	RETURN perms & selected_perms = perms;
END;
$has_permissions$ LANGUAGE plpgsql;
