CREATE TABLE versions (
	version SMALLINT NOT NULL,
	name TEXT PRIMARY KEY NOT NULL
);

CREATE TABLE messages (
	id BIGINT PRIMARY KEY NOT NULL,
	edit_id BIGINT,
	channel_id BIGINT NOT NULL,
	author_id BIGINT NOT NULL,
	content VARCHAR(2048) NOT NULL,
	encrypted BOOL NOT NULL DEFAULT false,
	pinned BOOL NOT NULL DEFAULT false,
	deleted BOOL NOT NULL DEFAULT false
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

CREATE UNIQUE users_unique_email_index ON users (email);

CREATE TABLE channels (
	id BIGINT PRIMARY KEY NOT NULL,
	name VARCHAR(128),
	user_ids BIGINT[] NOT NULL,
	pinned_ids BIGINT[] NOT NULL
);

CREATE TABLE files (
	id BIGINT PRIMARY KEY NOT NULL,
	message_id BIGINT NOT NULL,
	channel_id BIGINT NOT NULL,
	name VARCHAR(128) NOT NULL,
	mime SMALLINT NOT NULL,
	hash UUID NOT NULL
);

CREATE TABLE bugreports (
	id SERIAL PRIMARY KEY NOT NULL,
	user_id BIGINT,
	report_body TEXT NOT NULL,
	device_info TEXT NOT NULL
);

CREATE TABLE tokens (
	hmac_component TEXT NOT NULL,
	user_id BIGINT NOT NULL,
	app_id BIGINT NOT NULL,
	create_offset INT NOT NULL,
	scope TEXT[] NOT NULL
);

CREATE INDEX tokens_hmac_component_index ON tokens(hmac_component);

CREATE TABLE applications (
	id BIGINT PRIMARY KEY NOT NULL,
	owner_id BIGING NOT NULL,
	secret TEXT NOT NULL,
	redirect_uri TEXT NOT NULL,
	name VARCHAR(256) NOT NULL
);

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
