drop table if exists music cascade;
drop table if exists playlist;
drop table if exists genre;
drop table if exists artist;
drop table if exists album;
drop table if exists label;

create table artist (
	name varchar(31) primary key,
	founded smallint not null
);      

create table label (
	name varchar(31) primary key,
	address varchar(63) not null,
	founded smallint not null
);

create table album (
	name varchar(31) primary key,
	artist varchar(31) not null references artist(name),
	label varchar(31) not null references label(name),
	art varchar(63) not null,
	release smallint not null
);      

create table music (
	title varchar(31) not null,
	artist varchar(31) not null references artist(name),
	album varchar(31) references album(name),
	key varchar(11) primary key,
	length smallint not null,
	added timestamp not null default(localtimestamp)
);

create table playlist (
	name varchar(31) not null unique,
	key varchar(11) references music(key)
);

create table genre (
	key varchar(11) references music(key),
	genre varchar(31) not null
);
