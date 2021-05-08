import sys, os, time

sys.path.insert(1, os.getcwd() + "/libs")
sys.path.insert(1, os.getcwd() + "/common")

from lib_loaders import generate_infractionid, loader

generate_infractionid()

count = 100000

tstart = time.time()

buf = bytes(256 * 3)

loader.load_words_test(b"datastore/wordlist.cache.db\x00", 3, int(time.time() * 1000000) % (2**32), buf, len(buf), count)

tend = time.time()

print(f"Total time took: {round(100000*(tend-tstart))/100}ms")
print(f"Ids generated: {count}")
print(f"Time per id: {round((tend-tstart)/count*10000000)/10000}ms")
print(f"Ids/second: {round(count/(tend-tstart))}")
