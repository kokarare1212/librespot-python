from __future__ import annotations

import concurrent.futures
import random
import socket

from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf

from librespot.common import Utils
from librespot.core import Session
from librespot.crypto import DiffieHellman
from librespot.proto import Connect
from librespot.standard import Closeable
from librespot.standard import Runnable


class ZeroconfServer(Closeable):
    SERVICE = "spotify-connect"
    __MAX_PORT = 65536
    __MIN_PORT = 1024
    __EOL = "\r\n"
    __keys: DiffieHellman
    __inner: ZeroconfServer.Inner

    def __init__(self, inner: ZeroconfServer.Inner, listen_port: int,
                 listen_all: bool):
        self.__inner = inner
        self.__keys = DiffieHellman()

        if listen_port == -1:
            listen_port = random.randint(self.__MIN_PORT, self.__MAX_PORT)

    class Builder(Session.AbsBuilder):
        __listenAll = False
        __listenPort = -1

        def __init__(self, conf: Session.Configuration):
            super().__init__(conf)

        def set_listen_all(self, listen_all: bool) -> ZeroconfServer.Builder:
            self.__listenAll = listen_all
            return self

        def set_listen_port(self, listen_port: int) -> ZeroconfServer.Builder:
            self.__listenPort = listen_port
            return self

        def create(self) -> ZeroconfServer:
            return ZeroconfServer(
                ZeroconfServer.Inner(
                    self.device_type,
                    self.device_name,
                    self.preferred_locale,
                    self.conf,
                    self.device_id,
                ),
                self.__listenPort,
                self.__listenAll,
            )

    class Inner:
        device_type: Connect.DeviceType = None
        device_name: str = None
        device_id: str = None
        preferred_locale: str = None
        conf = None

        def __init__(
            self,
            device_type: Connect.DeviceType,
            device_name: str,
            preferred_locale: str,
            conf: Session.Configuration,
            device_id: str = None,
        ):
            self.preferred_locale = preferred_locale
            self.conf = conf
            self.device_type = device_type
            self.device_name = device_name
            self.device_id = (device_id if device_id is not None else
                              Utils.random_hex_string(40))

    class HttpRunner(Runnable, Closeable):
        __sock: socket
        __executorService: concurrent.futures.ThreadPoolExecutor = (
            concurrent.futures.ThreadPoolExecutor())
        __shouldStop: bool = False

        def __init__(self, port: int):
            self.__sock = socket.socket()
            self.__sock.bind(("0.0.0.0", port))
            self.__sock.listen(1)

        def run(self) -> None:
            while not self.__shouldStop:
                client, address = self.__sock.accept()

                def anonymous():
                    self.__handle(client)
                    client.close()

                self.__executorService.submit(anonymous)

        def __handle(self, client: socket.socket):
            client.recv(1)

        def close(self) -> None:
            super().close()
