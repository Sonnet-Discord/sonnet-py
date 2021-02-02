#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void load_words(int retamount, unsigned long long seed, char* pointer) {

    // Open cache file
    FILE* fp = fopen("datastore/wordlist.cache.db", "rb");

    // Grab length of file
    int maxln = fgetc(fp);
    fseek(fp, 0, SEEK_END);
    int size = (ftell(fp) - 1) / maxln ;

    // Make mini buffer to hold words
    char buf[maxln];

    // Seed random number generator
    srand(seed);

    // Grab X amount of words
    for ( int i = 0 ; i < retamount; i++ ) {

        // Seek to random word pointer
        int rval = ((rand() % (size)) * maxln) + 1;
        fseek(fp, rval, SEEK_SET);

        // Grab word and add it to buffer
        int curlen = fgetc(fp);
        fgets(buf, curlen, fp);
        strcat(pointer, buf);

    }

    // Close file pointer
    fclose(fp);
}
