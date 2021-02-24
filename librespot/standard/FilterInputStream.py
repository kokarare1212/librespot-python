from librespot.standard.InputStream import InputStream


class FilterInputStream(InputStream):
    input_stream: InputStream

    def __init__(self, input_stream: InputStream):
        self.input_stream = input_stream

    def internal_read(self):
        return self.input_stream.read()

    def read(self,
             b: bytearray = None,
             offset: int = None,
             length: int = None) -> int:
        if b is not None and offset is None and length is None:
            offset = 0
            length = len(b)
        elif not (b is not None and offset is not None and length is not None):
            raise TypeError()

        return self.input_stream.read(b, offset, length)

    def skip(self, n: int) -> int:
        return self.input_stream.skip(n)

    def available(self) -> int:
        return self.input_stream.available()

    def close(self) -> None:
        self.input_stream.close()

    def mark(self, read_limit: int) -> None:
        self.input_stream.mark(read_limit)

    def reset(self) -> None:
        self.input_stream.reset()

    def mark_supported(self) -> bool:
        return self.input_stream.mark_supported()
