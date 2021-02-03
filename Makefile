sfdbcload: ./libs/sfdbcloader.c
	mkdir -p ./libs/compiled
	gcc -fPIC -shared -o ./libs/compiled/sonnet.1.1.4-DEV.1.so ./libs/sfdbcloader.c
