import struct


class BytesOutputStream:
    buffer: bytes

    def __init__(self):
        self.buffer = b""

    def write(self, data: bytes):
        self.buffer += data
        return len(data)

    def write_byte(self, data: int):
        self.buffer += bytes([data])
        return 1

    def write_int(self, data: int):
        self.buffer += struct.pack(">i", data)
        return 4

    def write_short(self, data: int):
        self.buffer += struct.pack(">h", data)
        return 2
