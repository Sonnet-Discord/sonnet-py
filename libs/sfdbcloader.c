#include <stdio.h>
#include <string.h>
#include <stdlib.h>

typedef struct {
	char* ptr;
	size_t len;
	size_t cap;
} String;

// Copies amount from fp into String
// If the String does not have the capacity it returns 1 and no call occurs, else returns 0
int fcopys(FILE* fp, String* s, int amount) {

	if ((size_t)amount > (s->cap - s->len)) {
		return 1;
	}

	char* r = fgets(s->ptr+s->len, amount+1, fp);

	if (r == NULL) {
		return 1;
	}

	s->len += amount;

	return 0;
}

int load_words_to_string ( FILE* fp, int retamount, String* s ) {
	
	// Grab length of file
	int maxln = fgetc(fp);
	fseek(fp, 0, SEEK_END);
	int size = (ftell(fp) - 1) / maxln ;

	// Grab X amount of words
	for ( int i = 0 ; i < retamount; i++ ) {

		// Seek to random word pointer
		int randval = ((rand() % (size)) * maxln) + 1;
		fseek(fp, randval, SEEK_SET);

		// Grab word and add it to buffer
		int getamnt = fgetc(fp);

		if (fcopys(fp, s, getamnt) != 0) {
			return 1;
		}

	}

	return 0;
}

int load_words ( char* filename, int retamount, unsigned int seed, char* pointer, int pointer_length ) {

	// Seed random number generator
	srand(seed);

	// Open cache file
	FILE* fp = fopen(filename, "rb");

	// Exit if file does not exist
	if ( fp == NULL ) {
		return 2; // Return 2 on file not exist errors, 1 on general errors
	}
	
	// Create String object
	String b = {pointer, 0, (size_t)pointer_length};

	// Zero string
	memset(b.ptr, 0, b.cap);

	int retcode = load_words_to_string(fp, retamount, &b);

	// Close fp regardless of output
	fclose(fp);

	return retcode;
}

int load_words_test( char* filename, int retamount, unsigned int seed, char* pointer, int pointer_length, int testcount) {
	for (int i = 0; i < testcount; i++) {
		seed++;
		load_words(filename, retamount, seed, pointer, pointer_length);
	}
	return 0;
}
