# Cryptographically sound AES-CTR-HMAC wrapper for fileio
# Ultrabear 2021

# This module sucks, python was not meant to do disk handling

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac

from typing import Generator, Union, List, Protocol, runtime_checkable


class errors:
    __slots__ = ()

    class HMACInvalidError(ValueError):
        __slots__ = ()

    class NotSonnetAESError(FileNotFoundError):
        __slots__ = ()


# Never actually called
class crypto_typing:
    class encryptor_decryptor(Protocol):
        def update(self, buf: Union[bytes, bytearray]) -> bytes:
            ...

        def update_into(self, bufin: Union[bytes, bytearray], bufout: Union[bytes, bytearray]) -> None:
            ...

        def finalize(self) -> bytes:
            ...


def directBinNumber(inData: int, length: int) -> bytes:
    return bytes((inData >> (8 * i) & 0xff) for i in range(length))


class _WriteSeekCloser(Protocol):
    def write(self, buf: bytes, /) -> int:
        ...

    def seek(self, cookie: int, whence: int = 0, /) -> int:
        ...

    def close(self) -> None:
        ...


@runtime_checkable
class _Flushable(Protocol):
    def flush(self) -> None:
        ...


class encrypted_writer:
    __slots__ = "cipher", "encryptor_module", "HMACencrypt", "rawfile", "buf"

    def __init__(self, filename: Union[bytes, str, _WriteSeekCloser], key: bytes, iv: bytes) -> None:

        # Start cipher system
        self.cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
        self.encryptor_module = self.cipher.encryptor()

        # Initialize HMAC generator
        self.HMACencrypt = hmac.HMAC(key, hashes.SHA512())

        # Open rawfile and write headers
        if isinstance(filename, (bytes, str)):
            self.rawfile: _WriteSeekCloser = open(filename, "wb+")
        else:
            self.rawfile = filename
        self.rawfile.write(b"SONNETAES\x01")
        self.rawfile.write(bytes(64))

        # Initialize writable buffer
        self.buf = bytes(2**16 + 256)

    def _generate_chunks(self, data: bytes) -> Generator[memoryview, None, None]:

        # Init mem map
        raw_data = memoryview(data)

        # Yield data in chunks
        for i in range(0, len(data), ((2**16) - 1)):
            yield raw_data[i:i + ((2**16) - 1)]

    def write(self, data: bytes) -> None:

        # Write a maximum of 2^16-1 blocksize
        if len(data) > ((2**16) - 1):
            for chunk in self._generate_chunks(data):
                self._write_data(chunk)
        elif data:

            self._write_data(data)

    def _write_data(self, unencrypted: Union[memoryview, bytes]) -> None:

        # Write length of data to file
        dlen = len(unencrypted)
        self.rawfile.write(directBinNumber(dlen, 2))

        # Encrypt
        self.encryptor_module.update_into(unencrypted, self.buf)
        memptr = memoryview(self.buf)

        self.rawfile.write(memptr[:dlen])
        # Update HMAC
        self.HMACencrypt.update(memptr[:dlen])

    def finalize(self) -> None:

        # Finalize HMAC
        encrypted_HMAC = self.HMACencrypt.finalize()

        # Write HMAC to file
        self.rawfile.seek(10)
        self.rawfile.write(encrypted_HMAC)
        # Close objects
        self.rawfile.close()
        self.encryptor_module.finalize()

    def flush(self) -> None:
        if isinstance(self.rawfile, _Flushable):
            self.rawfile.flush()

    def close(self) -> None:

        self.finalize()

    def seekable(self) -> bool:

        return False

    def read(self, size: int = -1) -> None:

        raise TypeError(f"{self} object does not allow reading")


class _ReadSeekCloser(Protocol):
    def read(self, amnt: int) -> bytes:
        ...

    def seek(self, cookie: int, whence: int = 0, /) -> int:
        ...

    def close(self) -> None:
        ...


class encrypted_reader:
    __slots__ = "rawfile", "cipher", "decryptor_module", "pointer", "cache"

    def __init__(self, filename: Union[bytes, str, _ReadSeekCloser], key: bytes, iv: bytes) -> None:

        # Open rawfile
        if isinstance(filename, (bytes, str)):
            self.rawfile: _ReadSeekCloser = open(filename, "rb+")
        else:
            self.rawfile = filename

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
            raise errors.NotSonnetAESError("The file requested is not a SONNETAES file")

        # Calculate HMAC of encrypted field
        while a := self.rawfile.read(2):
            HMACobj.update(self.rawfile.read(int.from_bytes(a, "little")))

        if not HMACobj.finalize() == checksum:
            raise errors.HMACInvalidError("The encrypted contents does not match the HMAC")

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
                self.cache.extend(self._grab_amount(read_amount))
            else:
                eof_reached = True

        return bytes(memoryview(self.cache)[self.pointer:amount_wanted + self.pointer])

    def read(self, size: int = -1) -> bytes:

        if size == -1:
            if self.pointer == 0:
                # Return entire file if pointer is at 0
                datamap: List[bytes] = []
                while a := self.rawfile.read(2):
                    datamap.append(self._grab_amount(int.from_bytes(a, "little")))
                return b"".join(datamap)
            else:
                # Return remainder of data
                while a := self.rawfile.read(2):
                    self.cache.extend((self._grab_amount(int.from_bytes(a, "little"))))
                return bytes(memoryview(self.cache)[self.pointer:])
        else:

            returndata = self._read_exact(size)
            self.pointer += size

            return returndata

    def peek(self, size: int) -> bytes:

        return self._read_exact(size)

    def seek(self, seekloc: int) -> int:

        self.pointer = seekloc
        return int(self.pointer)

    def seekable(self) -> bool:

        return True

    def close(self) -> None:

        self.rawfile.close()
        del self.cache

    def write(self, data: bytes) -> None:
        raise TypeError(f"{self} object does not allow writing")
