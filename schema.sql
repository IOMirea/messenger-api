CREATE TABLE versions (
	version SMALLINT NOT NULL,
	name TEXT PRIMARY KEY NOT NULL
);

CREATE TABLE messages (
	id BIGINT PRIMARY KEY NOT NULL,
	channel_id BIGINT NOT NULL,
	author_id BIGINT NOT NULL,
	content VARCHAR(2048) NOT NULL,
	encrypted BOOL NOT NULL DEFAULT false,
	pinned BOOL NOT NULL DEFAULT false,
	edited BOOL NOT NULL DEFAULT false,
	deleted BOOL NOT NULL DEFAULT false
);

CREATE INDEX messages_channel_index ON messages(channel_id);

CREATE TABLE users (
	id BIGINT PRIMARY KEY NOT NULL,
	name VARCHAR(128) NOT NULL,
	channel_ids BIGINT[] NOT NULL DEFAULT ARRAY[]::BIGINT[],
	last_read_message_ids BIGINT[] NOT NULL DEFAULT ARRAY[]::BIGINT[],
	bot BOOL NOT NULL,
	email TEXT NOT NULL,
	password BYTEA NOT NULL
);

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

CREATE TABLE applications (
	id BIGINT PRIMARY KEY NOT NULL,
	redirect_uri TEXT NOT NULL,
	name VARCHAR(256) NOT NULL
);
