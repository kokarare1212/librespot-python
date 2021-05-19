from librespot.zeroconf import Packet


class Record:
    TYPE_A: int = 0x01
    TYPE_PTR: int = 0x0c
    TYPE_CNAME: int = 0x05
    TYPE_TXT: int = 0x10
    TYPE_AAAA: int = 0x1c
    TYPE_SRV: int = 0x21
    TYPE_NSEC: int = 0x2f
    TYPE_ANY: int = 0xff
    __type: int
    _ttl: int
    __name: str
    __clazz: int
    __data: bytes

    def __init__(self, typ: int):
        self.__type = typ
        self.__clazz = 1

    @staticmethod
    def _write_name(self, name: str, packet: Packet):
        length = len(name)
        out = b""
        start = 0
        for i in range(length + 1):
            c = "." if i == length else name[i]
            if c == ".":
                out += bytes([i - start])
                for j in range(start, i):
                    out += name.encode()[j]
                start = i + 1
        out += bytes([0])
        return out, len(name) + 2
