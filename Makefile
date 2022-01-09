CC=gcc
version=1.2.9-DEV.0
GOCMD=go
GOversion=2.0.0-DEV.3
compilefolder=./libs/compiled

typecheck:
	pyflakes .
	mypy . --strict --ignore-missing-imports --warn-unreachable

all: ${compilefolder} ./libs/sfdbcloader.c
	${CC} -fPIC -shared -Wall -Wextra -Werror -O3 -o ${compilefolder}/sonnet.${version}.so ./libs/sfdbcloader.c

gotools: ${compilefolder} ./libs/gotools.go
	${GOCMD} build -o ${compilefolder}/gotools.${GOversion}.so -buildmode=c-shared ./libs/gotools.go

${compilefolder}:
	mkdir -p ${compilefolder}
