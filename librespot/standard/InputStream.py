from __future__ import annotations
from librespot.standard.Closeable import Closeable
import sys
import typing

if typing.TYPE_CHECKING:
    from librespot.standard.OutputStream import OutputStream


class InputStream(Closeable):
    max_skip_buffer_size: typing.Final[int] = 2048
    default_buffer_size: typing.Final[int] = 8192

    @staticmethod
    def null_input_stream():
        class Anonymous(InputStream):
            closed: bool

            def ensure_open(self) -> None:
                if self.closed:
                    raise IOError("Stream closed")

            def available(self) -> int:
                self.ensure_open()
                return 0

            def read(self,
                     b: bytearray = None,
                     offset: int = None,
                     length: int = None) -> int:
                if b is not None and offset is not None and length is not None:
                    if len(b) < (offset + length):
                        raise IndexError()
                    if length == 0:
                        return 0
                    self.ensure_open()
                    return -1
                if b is None and offset is None and length is None:
                    self.ensure_open()
                    return -1
                raise TypeError()

            def read_all_bytes(self):
                self.ensure_open()
                return bytearray(0)

            def read_n_bytes(self,
                             b: bytearray = None,
                             offset: int = None,
                             length: int = None) -> bytearray:
                if length < 0:
                    raise TypeError("length < 0")
                self.ensure_open()
                return bytearray(0)

            def skip(self, n) -> int:
                self.ensure_open()
                return 0

            def skip_n_bytes(self, n: int) -> None:
                self.ensure_open()
                if n > 0:
                    raise EOFError()

            def transfer_to(self, out) -> int:
                if out is None:
                    raise TypeError()
                self.ensure_open()
                return 0

            def close(self):
                self.closed = True

        return Anonymous()

    def internal_read(self):
        raise NotImplementedError()

    def read(self,
             b: bytearray = None,
             offset: int = None,
             length: int = None) -> int:
        if b is None and offset is None and length is None:
            return self.internal_read()
        if b is not None and offset is None and length is None:
            offset = 0
            length = len(b)
        elif not (b is not None and offset is not None and length is not None):
            raise TypeError()
        if len(b) < (offset + length):
            raise IndexError()
        if length == 0:
            return 0

        c = self.read()
        if c == -1:
            return -1

        b[offset] = c

        i = 1
        for i in range(i, length):
            c = self.read()
            if c == -1:
                break
            b[offset + i] = c
        return i

    max_buffer_size: typing.Final[int] = sys.maxsize - 8

    def read_all_bytes(self) -> bytearray:
        return self.read_n_bytes(length=sys.maxsize)

    def read_n_bytes(self,
                     b: bytearray = None,
                     offset: int = None,
                     length: int = None) -> typing.Union[bytearray, int]:
        if b is None and offset is None and len is not None:
            if length < 0:
                raise TypeError("length < 0")

            bufs = None
            result = None
            total = 0
            remaining = length
            n: int
            while True:
                buf = bytearray(min(remaining, self.default_buffer_size))
                nread = 0

                while True:
                    n = self.read(buf, nread, min(len(buf) - nread, remaining))
                    if not n > 0:
                        break
                    nread += n
                    remaining -= n

                if nread > 0:
                    if self.max_buffer_size - total < nread:
                        raise MemoryError("Required array size too large")
                    total += nread
                    if result is None:
                        result = buf
                    else:
                        if bufs is None:
                            bufs = [result]
                        bufs.append(buf)
                if n >= 0 and remaining > 0:
                    break

            if bufs is None:
                if result is None:
                    return bytearray(0)
                return result if len(result) == total else result[:total]

            result = bytearray(total)
            offset = 0
            remaining = total
            for b in bufs:
                count = min(len(b), remaining)
                for i in range(offset, offset + count):
                    result.insert(i, b[i])
                offset += count
                remaining -= count

            return result
        if b is not None and offset is not None and length is not None:
            if len(b) < (offset + length):
                raise IndexError()

            n = 0
            while n < length:
                count = self.read(b, offset + n, length - n)
                if count < 0:
                    break
                n += count
            return n
        raise TypeError()

    def skip(self, n: int) -> int:
        remaining = n
        nr: int

        if n <= 0:
            return 0

        size = min(self.max_skip_buffer_size, remaining)
        skip_buffer = bytearray(size)
        while remaining > 0:
            nr = self.read(skip_buffer, 0, min(size, remaining))
            if nr < 0:
                break
            remaining -= nr

        return n - remaining

    def skip_n_bytes(self, n: int) -> None:
        if n > 0:
            ns = self.skip(n)
            if ns >= 0 and ns < n:
                n -= ns

                while n > 0 and self.read() != -1:
                    n -= 1

                if n != 0:
                    raise EOFError()
            elif ns != n:
                raise IOError("Unable to skip exactly")

    def available(self) -> int:
        return 0

    def close(self) -> None:
        pass

    def mark(self, read_limit: int) -> None:
        pass

    def reset(self) -> None:
        raise IOError("mark/reset not supported")

    def mark_supported(self) -> bool:
        return False

    def transfer_to(self, out: OutputStream) -> int:
        if out is None:
            raise TypeError()
        transferred = 0
        buffer = bytearray(self.default_buffer_size)
        read: int
        while True:
            read = self.read(buffer, 0, self.default_buffer_size)
            if not read:
                break
            out.write(buffer=buffer, offset=0, length=read)
            transferred += read
        return transferred
