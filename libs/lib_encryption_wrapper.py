# Cryptographically sound AES-CTR-HMAC wrapper for fileio
# Ultrabear 2021

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac

import io

def directBinNumber(inData, length):
    return tuple([(inData >> (8 * i) & 0xff) for i in range(length)])


class encrypted_writer:
    def __init__(self, filename, key, iv):

        # Start cipher system
        self.cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        self.encryptor_module = self.cipher.encryptor()

        # Initalize HMAC generator
        self.HMACencrypt = hmac.HMAC(key, hashes.SHA512())

        # Open rawfile and write headers
        if isinstance(filename, io.IOBase):
            self.rawfile = filename
        else:
            self.rawfile = open(filename, "wb+")
        self.rawfile.write(b"SONNETAES\x01")
        self.rawfile.write(bytes(64))

        # Initialize writable buffer
        self.buf = bytes(2**16 + 256)

    def _generate_chunks(self, data: bytes) -> bytes:

        # Init mem map
        raw_data = memoryview(data)

        # Yield data in chunks
        for i in range(0, len(data), ((2**16) - 1)):
            yield bytes(raw_data[i:i + ((2**16) - 1)])

    def write(self, data: bytes):

        # Write a maximum of 2^16-1 blocksize
        if len(data) > ((2**16) - 1):
            for chunk in self._generate_chunks(data):
                self._write_data(chunk)
        elif data:

            self._write_data(data)

    def _write_data(self, unencrypted: bytes):

        # Write length of data to file
        dlen = len(unencrypted)
        self.rawfile.write(bytes(directBinNumber(dlen, 2)))

        # Encrypt
        self.encryptor_module.update_into(unencrypted, self.buf)
        memptr = memoryview(self.buf)

        self.rawfile.write(memptr[:dlen])
        # Update HMAC
        self.HMACencrypt.update(memptr[:dlen])

    def finalize(self):

        # Finalize HMAC
        encrypted_HMAC = self.HMACencrypt.finalize()

        # Write HMAC to file
        self.rawfile.seek(10)
        self.rawfile.write(encrypted_HMAC)
        # Close objects
        self.rawfile.close()
        self.encryptor_module.finalize()

    def close(self):

        self.finalize()

    def seekable(self):

        return False

    def read(self, *args):

        raise TypeError(f"{self} object does not allow reading")


class encrypted_reader:
    def __init__(self, filename, key, iv):

        # Open rawfile
        if isinstance(filename, io.IOBase):
            self.rawfile = filename
        else:
            self.rawfile = open(filename, "rb+")

        # Make decryptor instance
        self.cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        self.decryptor_module = self.cipher.decryptor()

        # Generate HMAC
        HMACobj = hmac.HMAC(key, hashes.SHA512())

        # Check if file is valid SONNETAES
        if self.rawfile.read(10) == b"SONNETAES\x01":
            checksum = self.rawfile.read(64)
        else:
            self.rawfile.close()
            raise FileNotFoundError("The file requested is not a SONNETAES file")

        # Calculate HMAC of encrypted field
        while a := self.rawfile.read(2):
            HMACobj.update(self.rawfile.read(int.from_bytes(a, "little")))

        if not HMACobj.finalize() == checksum:
            raise ValueError("The encrypted contents does not match the HMAC")

        # Seek to start of file after checking HMAC
        self.rawfile.seek(10 + 64)
        self.pointer = 0
        self.cache = bytearray()

    def _grab_amount(self, amount: int) -> bytes:

        return self.decryptor_module.update(self.rawfile.read(amount))

    def _read_exact(self, amount_wanted: int) -> bytes:

        if amount_wanted == 0:
            return b""

        # Read till EOF
        eof_reached = False
        while len(self.cache) < self.pointer + amount_wanted and not eof_reached:
            read_amount = int.from_bytes(self.rawfile.read(2), "little")
            if read_amount:
                self.cache.extend(((self._grab_amount(read_amount))))
            else:
                eof_reached = True

        return bytes(memoryview(self.cache)[self.pointer:amount_wanted + self.pointer])

    def read(self, size=-1) -> bytes:

        if size == -1:
            if self.pointer == 0:
                # Return entire file if pointer is at 0
                datamap = []
                while a := self.rawfile.read(2):
                    datamap.append(self._grab_amount(int.from_bytes(a, "little")))
                return b"".join(datamap)
            else:
                # Return remainder of data
                self.cache
                while a := self.rawfile.read(2):
                    self.cache.extend((self._grab_amount(int.from_bytes(a, "little"))))
                return bytes(memoryview(self.cache)[self.pointer:])
        else:

            returndata = self._read_exact(size)
            self.pointer += amount_wanted

            return returndata

    def peek(self, size: int) -> bytes:

        return self._read_exact(size)

    def seek(self, seekloc: int) -> int:

        self.pointer = seekloc
        return int(self.pointer)

    def seekable(self) -> bool:

        return True

    def close(self):

        self.rawfile.close()
        del self.cache

    def write(self, data):
        raise TypeError(f"{self} object does not allow writing")
