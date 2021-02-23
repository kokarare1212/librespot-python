import struct


class BytesInputStream:
    buffer: bytes
    endian: str

    def __init__(self, buffer: bytes, endian: str = ">"):
        self.buffer = buffer
        self.endian = endian

    def read(self, length: int = None) -> bytes:
        if length is None:
            length = len(self.buffer)
        buffer = self.buffer[:length]
        self.buffer = self.buffer[length:]
        return buffer

    def read_byte(self) -> bytes:
        buffer = struct.unpack("s", self.buffer[:1])[0]
        self.buffer = self.buffer[1:]
        return buffer

    def read_int(self) -> int:
        buffer = struct.unpack("{}i".format(self.endian), self.buffer[:4])[0]
        self.buffer = self.buffer[4:]
        return buffer

    def read_short(self) -> int:
        buffer = struct.unpack("{}h".format(self.endian), self.buffer[:2])[0]
        self.buffer = self.buffer[2:]
        return buffer

    def read_long(self) -> int:
        buffer = struct.unpack("{}q".format(self.endian), self.buffer[:8])[0]
        self.buffer = self.buffer[8:]
        return buffer

    def read_float(self) -> float:
        buffer = struct.unpack("{}f".format(self.endian), self.buffer[:4])[0]
        self.buffer = self.buffer[4:]
        return buffer
