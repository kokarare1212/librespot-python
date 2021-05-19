from __future__ import annotations
from librespot.standard import Closeable
import base64
import random
import socket


class Zeroconf(Closeable):
    __DISCOVERY = "_services._dns-sd._udp.local"
    __BROADCAST4: socket.socket
    __BROADCAST6: socket.socket
    __use_ipv4: bool = True
    __use_ipv6: bool = True
    __hostname: str
    __domain: str

    def __init__(self):
        try:
            self.__BROADCAST4 = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
            self.__BROADCAST4.connect(("224.0.0.251", 5353))
            self.__BROADCAST6 = socket.socket(socket.AF_INET6,
                                              socket.SOCK_DGRAM)
            self.__BROADCAST6.connect(("FF02::FB", 5353))
        except Exception as e:
            pass
        self.set_domain(".local")
        self.set_local_host_name(Zeroconf.get_or_create_local_host_name())

    @staticmethod
    def get_or_create_local_host_name() -> str:
        host = socket.gethostname()
        if host == "localhost":
            host = base64.b64encode(
                random.randint(-9223372036854775808,
                               9223372036854775807)).decode() + ".local"
        return host

    def set_use_ipv4(self, ipv4: bool) -> Zeroconf:
        self.__use_ipv4 = ipv4
        return self

    def set_use_ipv6(self, ipv6: bool) -> Zeroconf:
        self.__use_ipv6 = ipv6
        return self

    def close(self) -> None:
        super().close()

    def get_domain(self) -> str:
        return self.__domain

    def set_domain(self, domain: str) -> Zeroconf:
        self.__domain = domain
        return self

    def get_local_host_name(self) -> str:
        return self.__hostname

    def set_local_host_name(self, name: str) -> Zeroconf:
        self.__hostname = name
        return self

    def handle_packet(self, packet):
        pass

    def announce(self, service):
        pass
