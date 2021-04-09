import binascii
import os


class Utils:
    @staticmethod
    def random_hex_string(length: int):
        buffer = os.urandom(int(length / 2))
        return Utils.bytes_to_hex(buffer)

    @staticmethod
    def truncate_middle(s: str, length: int) -> str:
        if length <= 1:
            raise TypeError()

        first = length / 2
        result = s[:first]
        result += "..."
        result += s[len(s) - (length - first):]
        return result

    @staticmethod
    def split(s: str, c: str):
        return s.split(c)

    @staticmethod
    def to_byte_array(i: int) -> bytes:
        width = i.bit_length()
        width += 8 - ((width % 8) or 8)
        fmt = '%%0%dx' % (width // 4)
        if i == 0:
            return bytes([0])
        return binascii.unhexlify(fmt % i)

    @staticmethod
    def bytes_to_hex(buffer: bytes) -> str:
        return binascii.hexlify(buffer).decode()

    @staticmethod
    def hex_to_bytes(s: str) -> bytes:
        return binascii.unhexlify(s)
