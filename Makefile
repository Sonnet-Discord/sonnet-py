CC=gcc
version=1.2.3-DEV.0
GOCMD=go
GOversion=2.0.0-DEV.0

all: ./libs/sfdbcloader.c
	mkdir -p ./libs/compiled
	${CC} -fPIC -shared -Wall -Werror -o ./libs/compiled/sonnet.${version}.so ./libs/sfdbcloader.c

gotools: ./libs/gotools.go
	mkdir -p ./libs/compiled
	${GOCMD} build -o ./libs/compiled/gotools.${GOversion}.so -buildmode=c-shared ./libs/gotools.go

