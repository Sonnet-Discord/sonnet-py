# Cryptographically sound AES-CTR-HMAC wrapper for fileio
# Ultrabear 2021

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac


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
        self.rawfile = open(filename, "wb+")
        self.rawfile.write(b"SONNETAES\x01")
        self.rawfile.write(bytes(64))

        # Initialize writable buffer
        self.buf = bytes(2**16 + 256)

    def write(self, data):

        # Write a maximum of 2^24-1 blocksize
        if len(data) > ((2**16) - 1):
            for chunk in [bytes(data[i:i + ((2**16) - 1)]) for i in range(0, len(data), ((2**16) - 1))]:
                self.write_data(chunk)
        else:
            self.write_data(data)

    def write_data(self, unencrypted):

        # Write length of data to file
        dlen = len(unencrypted)
        self.rawfile.write(bytes(directBinNumber(dlen, 2)))

        # Encrypt and write data block
        self.encryptor_module.update_into(unencrypted, self.buf)
        self.rawfile.write((memoryview(self.buf)[:dlen]))
        # Update HMAC
        self.HMACencrypt.update((memoryview(self.buf)[:dlen]))

    def finalize(self):

        # Finalize HMAC
        encrypted_HMAC = self.HMACencrypt.finalize()

        # Write HMAC to file
        self.rawfile.seek(10)
        self.rawfile.write(encrypted_HMAC)
        # Close objects
        self.rawfile.close()
        self.encryptor_module.finalize()

    def read(self, *args):

        raise TypeError(f"{self} object does not allow reading")


class encrypted_reader:
    def __init__(self, filename, key, iv):

        # Open rawfile
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
        self.cache = b""

    def read(self, *arg):

        if not arg:
            if self.pointer == 0:
                # Return entire file if pointer is at 0
                datamap = []
                while a := self.rawfile.read(2):
                    datamap.append(self.decryptor_module.update(self.rawfile.read(int.from_bytes(a, "little"))))
                return b"".join(datamap)
            else:
                # Return remainder of data
                datamap = [self.cache]
                while a := self.rawfile.read(2):
                    datamap.append(self.decryptor_module.update(self.rawfile.read(int.from_bytes(a, "little"))))
                return b"".join(datamap)
        else:

            amount_wanted = arg[0]

            while len(self.cache) < amount_wanted:
                self.cache += (self.decryptor_module.update(self.rawfile.read(int.from_bytes(self.rawfile.read(2), "little"))))

            self.pointer += amount_wanted
            returndata = bytes(memoryview(self.cache)[:amount_wanted])
            self.cache = bytes(memoryview(self.cache)[amount_wanted:])

            return returndata

    def write(self, data):
        raise TypeError(f"{self} object does not allow writing")
