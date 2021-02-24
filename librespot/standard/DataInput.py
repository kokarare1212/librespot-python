class DataInput:
    def internal_read_fully(self, b: bytearray) -> None:
        pass

    def read_fully(self,
                   b: bytearray = None,
                   offset: int = None,
                   length: int = None) -> None:
        pass

    def skip_bytes(self, n: int) -> int:
        pass

    def read_boolean(self) -> bool:
        pass

    def read_byte(self) -> bytes:
        pass

    def read_unsigned_byte(self) -> int:
        pass

    def read_short(self) -> int:
        pass

    def read_unsigned_short(self) -> int:
        pass

    def read_char(self) -> str:
        pass

    def read_int(self) -> int:
        pass

    def read_long(self) -> int:
        pass

    def read_float(self) -> float:
        pass

    def read_double(self) -> float:
        pass

    def read_line(self) -> str:
        pass

    def read_utf(self) -> str:
        pass
