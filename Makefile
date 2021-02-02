sfdbcload: ./libs/sfdbcloader.c
	mkdir -p ./libs/compiled
	gcc -fPIC -shared -o ./libs/compiled/libsfdbc.sonnet.so ./libs/sfdbcloader.c
