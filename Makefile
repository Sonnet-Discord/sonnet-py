CC=gcc
version=1.2.3-DEV.0

sfdbcload: ./libs/sfdbcloader.c
	mkdir -p ./libs/compiled
	${CC} -fPIC -shared -Wall -Werror -o ./libs/compiled/sonnet.${version}.so ./libs/sfdbcloader.c
