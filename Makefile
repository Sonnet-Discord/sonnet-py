CC=gcc
version=1.2.1-PATCH.0

sfdbcload: ./libs/sfdbcloader.c
	mkdir -p ./libs/compiled
	${CC} -fPIC -shared -o ./libs/compiled/sonnet.${version}.so ./libs/sfdbcloader.c
