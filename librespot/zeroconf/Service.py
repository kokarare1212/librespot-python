from __future__ import annotations
from librespot.zeroconf import Packet


class Service:
    __alias: str
    __service: str
    __port: int
    __text: dict
    __domain: str
    __protocol: str
    __host: str

    def __init__(self, alias: str, service: str, port: int):
        self.__alias = alias
        for s in alias:
            c = ord(s)
            if c < 0x20 or c == 0x7f:
                raise TypeError()

            self.__service = service
            self.__port = port
            self.__protocol = "tcp"
            self.__text = {}

    def __esc(self, text: str):
        ns = ""
        for s in text:
            c = ord(s)
            if c == 0x2e or c == 0x5c:
                ns += "\\"
            ns += s
        return ns

    def set_protocol(self, protocol: str) -> Service:
        if protocol == "tcp" or protocol == "udp":
            self.__protocol = protocol
        else:
            raise TypeError()
        return self

    def get_domain(self) -> str:
        return self.__domain

    def set_domain(self, domain: str) -> Service:
        if domain is None or len(domain) < 2 or domain[0] != ".":
            raise TypeError(domain)
        self.__domain = domain
        return self

    def get_host(self) -> str:
        return self.__host

    def set_host(self, host: str) -> Service:
        self.__host = host
        return self

    def get_packet(self) -> Packet:
        packet = Packet()
        return packet
