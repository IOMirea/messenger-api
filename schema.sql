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
	last_read_message_ids BIGINT[] NOT NULL DEFAULT ARRAY[]::BIGINT[],
	bot BOOL NOT NULL,
	email TEXT NOT NULL UNIQUE,
	password BYTEA NOT NULL,
	verified BOOL NOT NULL DEFAULT false
);


/* Permissions bitfield
 * 0:   modify channel
 * 1:   invite members
 * 2:   kick members
 * 3:   ban members
 * 4:   modify members
 */

CREATE TABLE channel_permissions (
	user_id BIGINT NOT NULL,
	channel_id BIGINT NOT NULL,
	permissions BIT VARYING NOT NULL DEFAULT 0::bit(16),

	FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
	FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
);

CREATE TABLE applications (
	id BIGINT PRIMARY KEY NOT NULL,
	owner_id BIGING NOT NULL,
	secret TEXT NOT NULL,
	redirect_uri TEXT NOT NULL,
	name VARCHAR(256) NOT NULL,
	
	FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE messages (
	id BIGINT PRIMARY KEY NOT NULL,
	edit_id BIGINT,
	channel_id BIGINT NOT NULL,
	author_id BIGINT NOT NULL,
	content VARCHAR(2048) NOT NULL,
	encrypted BOOL NOT NULL DEFAULT false,
	pinned BOOL NOT NULL DEFAULT false,
	deleted BOOL NOT NULL DEFAULT false,
	
	FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE RESTRICT,
	FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX messages_channel_index ON messages(channel_id);

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

CREATE UNIQUE users_unique_email_index ON users (email);

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

CREATE INDEX tokens_hmac_component_index ON tokens(hmac_component);

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
CREATE FUNCTION add_channel_user(cid BIGINT, uid BIGINT) RETURNS BOOLEAN
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

        RETURN true;
END;
$success$ LANGUAGE plpgsql;

CREATE FUNCTION remove_channel_user(cid BIGINT, uid BIGINT) RETURNS BOOLEAN
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

        RETURN true;
END;
$success$ LANGUAGE plpgsql;

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
