import struct


class Packet:
    __FLAG_RESPONSE: int = 15
    __FLAG_AA: int = 10
    __questions: list
    __answers: list
    __authorities: list
    __additionals: list
    __id: int
    __flags: int
    __address: str

    def __init__(self, _id: int):
        self.__id = _id
        self.__questions = []
        self.__answers = []
        self.__authorities = []
        self.__additionals = []

    def get_address(self) -> str:
        return self.__address

    def set_address(self, address: str) -> None:
        self.__address = address

    def get_id(self) -> int:
        return self.__id

    def is_response(self) -> bool:
        return self.__is_flag(self.__FLAG_RESPONSE)

    def set_response(self, on: bool) -> None:
        self.__set_flag(self.__FLAG_RESPONSE, on)

    def is_authoritative(self) -> bool:
        return self.__is_flag(self.__FLAG_AA)

    def set_authoritative(self, on: bool) -> None:
        self.__set_flag(self.__FLAG_AA, on)

    def __is_flag(self, flag: int):
        return (self.__flags & (1 << flag)) != 0

    def __set_flag(self, flag: int, on: bool):
        if on:
            self.__flags |= (1 << flag)
        else:
            self.__flags &= ~(1 << flag)

    def read(self, inp: bytes, address: str):
        self.__address = address
        self.__id = struct.unpack("<h", inp[0:2])[0]
        self.__flags = struct.unpack("<h", inp[2:4])[0]
        num_questions = struct.unpack("<h", inp[4:6])[0]
        num_answers = struct.unpack("<h", inp[6:8])[0]
        num_authorities = struct.unpack("<h", inp[8:10])[0]
        num_additionals = struct.unpack("<h", inp[10:12])[0]
