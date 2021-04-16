from librespot.standard.DataInput import DataInput
from librespot.standard.FilterInputStream import FilterInputStream
from librespot.standard.InputStream import InputStream


class DataInputStream(FilterInputStream, DataInput):
    def read(self,
             b: bytearray = None,
             offset: int = None,
             length: int = None) -> int:
        if b is not None and offset is None and length is None:
            return self.input_stream.read(b, 0, len(b))
        if b is not None and offset is not None and length is not None:
            return self.input_stream.read(b, offset, length)
        raise TypeError()

    def read_fully(self,
                   b: bytearray = None,
                   offset: int = None,
                   length: int = None) -> None:
        if b is not None and offset is None and length is None:
            offset = 0
            length = len(b)
        elif not (b is not None and offset is not None and length is not None):
            raise TypeError()
        if length < 0:
            raise IndexError()
        n = 0
        while n < length:
            count = self.input_stream.read(b, offset + n, length - n)
            if count < 0:
                raise EOFError()
            n += count

    def skip_bytes(self, n: int) -> int:
        total = 0
        cur = 0
        while True:
            cur = self.input_stream.skip(n - total)
            if not (total < n and cur > 0):
                break
            total += cur

        return total

    def read_boolean(self) -> bool:
        ch = self.input_stream.read()
        if ch < 0:
            raise EOFError()
        return ch != 0

    def read_byte(self) -> bytes:
        ch = self.input_stream.read()
        if ch < 0:
            raise EOFError()
        return bytes([ch])

    def read_unsigned_byte(self) -> int:
        ch = self.input_stream.read()
        if ch < 0:
            raise EOFError()
        return ch

    def read_short(self) -> int:
        ch1 = self.input_stream.read()
        ch2 = self.input_stream.read()
        if (ch1 | ch2) < 0:
            raise EOFError()
        return (ch1 << 8) + (ch2 << 0)

    def read_unsigned_short(self) -> int:
        ch1 = self.input_stream.read()
        ch2 = self.input_stream.read()
        if (ch1 | ch2) < 0:
            raise EOFError()
        return (ch1 << 8) + (ch2 << 0)

    def read_char(self) -> str:
        ch1 = self.input_stream.read()
        ch2 = self.input_stream.read()
        if (ch1 | ch2) < 0:
            raise EOFError()
        return chr((ch1 << 8) + (ch2 << 0))

    def read_int(self) -> int:
        ch1 = self.input_stream.read()
        ch2 = self.input_stream.read()
        ch3 = self.input_stream.read()
        ch4 = self.input_stream.read()
        if (ch1 | ch2 | ch3 | ch4) < 0:
            raise EOFError()
        return (ch1 << 24) + (ch2 << 16) + (ch3 << 8) + (ch4 << 0)

    read_buffer = bytearray(8)

    def read_long(self) -> int:
        self.read_fully(self.read_buffer, 0, 8)
        return (self.read_buffer[0] << 56) + \
               ((self.read_buffer[1] & 255) << 48) + \
               ((self.read_buffer[2] & 255) << 40) + \
               ((self.read_buffer[3] & 255) << 32) + \
               ((self.read_buffer[4] & 255) << 24) + \
               ((self.read_buffer[5] & 255) << 16) + \
               ((self.read_buffer[6] & 255) << 8) + \
               ((self.read_buffer[7] & 255) << 0)

    def read_float(self) -> float:
        pass

    def read_double(self) -> float:
        pass

    def read_line(self) -> str:
        pass
