class DataOutput:
    def internal_write(self, byte: int) -> None:
        pass

    def write(self,
              byte: int = None,
              buffer: bytearray = None,
              offset: int = None,
              length: int = None) -> None:
        pass

    def write_boolean(self, v: bytes) -> None:
        pass

    def write_byte(self, v: int) -> None:
        pass

    def write_short(self, v: int) -> None:
        pass

    def write_char(self, v: int) -> None:
        pass

    def write_int(self, v: int) -> None:
        pass

    def write_long(self, v: int) -> None:
        pass

    def write_float(self, v: float) -> None:
        pass

    def write_double(self, v: float) -> None:
        pass

    def write_bytes(self, s: str) -> None:
        pass

    def write_chars(self, s: str) -> None:
        pass

    def write_utf(self, s: str) -> None:
        pass
