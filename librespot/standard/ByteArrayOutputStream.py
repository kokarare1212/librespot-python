from librespot.standard.OutputStream import OutputStream


class ByteArrayOutputStream(OutputStream):
    buf: bytearray
    count: int = 0

    def __init__(self, size: int = 32):
        if size < 0:
            raise RuntimeError("Negative initial size: {}".format(self))
        self.buf = bytearray(size)

    def ensure_capacity(self, min_capacity: int) -> None:
        old_capacity = len(self.buf)
        min_growth = min_capacity - old_capacity
        if min_growth > 0:
            new_buf = bytearray(min_capacity)
            new_buf[0:len(self.buf)] = self.buf
            self.buf = new_buf

    def internal_write(self, byte: int) -> None:
        self.ensure_capacity(self.count + 1)
        self.buf[self.count] = byte
        self.count += 1

    def write(self,
              byte: int = None,
              buffer: bytearray = None,
              offset: int = None,
              length: int = None) -> None:
        if byte is not None and buffer is None and offset is None and length is None:
            self.internal_write(byte)
            return
        if byte is None and buffer is not None and offset is None and length is None:
            offset = 0
            length = len(buffer)
        elif not (byte is None and buffer is not None and offset is not None
                  and length is not None):
            raise TypeError()

        if len(buffer) < (offset + length):
            raise IndexError()

        self.ensure_capacity(self.count + length)
        self.buf[self.count:self.count + length] = buffer[offset:offset +
                                                          length]
        self.count += length

    def write_bytes(self, b: bytearray):
        self.write(buffer=b, offset=0, length=len(b))

    def write_to(self, out: OutputStream) -> None:
        out.write(buffer=self.buf, offset=0, length=self.count)

    def reset(self) -> None:
        self.count = 0

    def to_byte_array(self) -> bytearray:
        return self.buf

    def to_bytes(self) -> bytes:
        return bytes(self.buf)

    def size(self) -> int:
        return self.count

    def close(self) -> None:
        pass
