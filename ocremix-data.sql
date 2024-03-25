BEGIN TRANSACTION;
CREATE TABLE artist (
    id integer primary key,
    name text not null,
    url text not null
);
CREATE TABLE remix (
    id integer primary key,
    title text not null,
    primary_game text not null
);
CREATE TABLE remix_artist (
    remix_id integer not null,
    artist_id integer not null
);
COMMIT;
