#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int load_words ( char* filename, int retamount, unsigned long long seed, char* pointer, int pointer_length ) {

	// Open cache file
	FILE* fp = fopen(filename, "rb");

	// Exit if file does not exist
	if ( fp == NULL ) {
		return 1;
	}

	// Grab length of file
	int maxln = fgetc(fp);
	fseek(fp, 0, SEEK_END);
	int size = (ftell(fp) - 1) / maxln ;

	// Make mini buffer to hold words
	char buf[256];

	// Seed random number generator
	srand(seed);

	// Empty buffer
	memset(pointer, 0, pointer_length);

	// Grab X amount of words
	for ( int i = 0 ; i < retamount; i++ ) {

		// Seek to random word pointer
		int randval = ((rand() % (size)) * maxln) + 1;
		fseek(fp, randval, SEEK_SET);

		// Grab word and add it to buffer
		// The plus one makes no sense i think it just reads one less than its supposed to cause \x00 terminator?
		int getamnt = fgetc(fp)+1;
		fgets(buf, getamnt, fp);

		// Only add to buffer if it has space
		if ( strlen(buf) + strlen(pointer) < pointer_length ) {
			strcat(pointer, buf);
		}
		else {
			fclose(fp);
			return 1;
		}

	}

	// Close file pointer
	fclose(fp);
	return 0;
}

int load_words_test( char* filename, int retamount, unsigned long long seed, char* pointer, int pointer_length, int testcount) {
	for (int i = 0; i < testcount; i++) {
		load_words(filename, retamount, seed, pointer, pointer_length);
	}
	return 0;
}
