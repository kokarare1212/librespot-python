from librespot.standard.Closeable import Closeable
from librespot.standard.Flushable import Flushable


class OutputStream(Closeable, Flushable):
    def null_output_stream(self):
        class Annonymous(OutputStream):
            closed: bool

            def ensure_open(self) -> None:
                if self.closed:
                    raise IOError("Stream closed")

            def internal_write(self, byte: int):
                self.ensure_open()

            def write(self,
                      byte: int = None,
                      buffer: bytearray = None,
                      offset: int = None,
                      length: int = None):
                if byte is not None and buffer is None and offset is None and length is None:
                    self.internal_write(byte)
                elif not (byte is None and buffer is not None
                          and offset is not None and length is not None):
                    raise TypeError()
                if len(bytearray) < (offset + length):
                    raise IndexError()
                self.ensure_open()

            def close(self) -> None:
                self.closed = True

    def internal_write(self, byte: int):
        raise NotImplementedError()

    def write(self,
              byte: int = None,
              buffer: bytearray = None,
              offset: int = None,
              length: int = None):
        if byte is not None and buffer is None and offset is None and length is None:
            self.internal_write(byte)
        elif byte is None and buffer is not None and offset is None and length is None:
            offset = 0
            length = len(buffer)
        elif not (byte is None and buffer is not None and offset is not None
                  and length is not None):
            raise TypeError()

        if len(bytearray) < (offset + length):
            raise IndexError()

        for i in range(length):
            self.write(buffer[offset + i])

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass
