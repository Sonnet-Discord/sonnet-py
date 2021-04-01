import sys, os, time

sys.path.insert(1, os.getcwd() + "/libs")
sys.path.insert(1, os.getcwd() + "/common")

from lib_loaders import generate_infractionid

count = 100000

tstart = time.time()

for i in range(count):
    generate_infractionid()

tend = time.time()

print(f"Total time took: {round(100000*(tend-tstart))/100}ms")
print(f"Ids generated: {count}")
print(f"Time per id: {round((tend-tstart)/count*10000000)/10000}ms")
print(f"Ids/second: {round(count/(tend-tstart))}")
