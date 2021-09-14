from __future__ import annotations
from Cryptodome.Cipher import AES
from Cryptodome.Hash import HMAC, SHA1
from Cryptodome.Util import Counter
from librespot import util, Version
from librespot.core import Session
from librespot.crypto import DiffieHellman
from librespot.proto import Connect_pb2 as Connect
from librespot.structure import Closeable, Runnable, SessionListener
import base64
import concurrent.futures
import copy
import io
import json
import logging
import random
import socket
import threading
import typing
import urllib.parse
import zeroconf


class ZeroconfServer(Closeable):
    logger = logging.getLogger("Librespot:ZeroconfServer")
    service = "_spotify-connect._tcp.local."
    __connecting_username: typing.Union[str, None] = None
    __connection_lock = threading.Condition()
    __default_get_info_fields = {
        "status": 101,
        "statusString": "OK",
        "spotifyError": 0,
        "version": "2.7.1",
        "libraryVersion": Version.version_name,
        "accountReq": "PREMIUM",
        "brandDisplayName": "kokarare1212",
        "modelDisplayName": "librespot-python",
        "voiceSupport": "NO",
        "availability": "",
        "productID": 0,
        "tokenType": "default",
        "groupStatus": "NONE",
        "resolverVersion": "0",
        "scope": "streaming,client-authorization-universal",
    }
    __default_successful_add_user = {
        "status": 101,
        "spotifyError": 0,
        "statusString": "OK",
    }
    __eol = b"\r\n"
    __max_port = 65536
    __min_port = 1024
    __runner: HttpRunner
    __service_info: zeroconf.ServiceInfo
    __session: typing.Union[Session, None] = None
    __session_listeners: typing.List[SessionListener] = []
    __zeroconf: zeroconf.Zeroconf

    def __init__(self, inner: Inner, listen_port):
        self.__inner = inner
        self.__keys = DiffieHellman()
        if listen_port == -1:
            listen_port = random.randint(self.__min_port + 1, self.__max_port)
        self.__runner = ZeroconfServer.HttpRunner(self, listen_port)
        threading.Thread(target=self.__runner.run,
                         name="zeroconf-http-server").start()
        self.__zeroconf = zeroconf.Zeroconf()
        self.__service_info = zeroconf.ServiceInfo(
            ZeroconfServer.service,
            inner.device_name + "." + ZeroconfServer.service,
            listen_port,
            0,
            0, {
                "CPath": "/",
                "VERSION": "1.0",
                "STACK": "SP",
            },
            self.get_useful_hostname() + ".",
            addresses=[
                socket.inet_aton(
                    socket.gethostbyname(self.get_useful_hostname()))
            ])
        self.__zeroconf.register_service(self.__service_info)
        threading.Thread(target=self.__zeroconf.start,
                         name="zeroconf-multicast-dns-server").start()

    def add_session_listener(self, listener: ZeroconfServer):
        self.__session_listeners.append(listener)

    def close(self) -> None:
        self.__zeroconf.close()
        self.__runner.close()

    def close_session(self) -> None:
        if self.__session is None:
            return
        for session_listener in self.__session_listeners:
            session_listener.session_closing(self.__session)
        self.__session.close()
        self.__session = None

    def get_useful_hostname(self) -> str:
        host = socket.gethostname()
        if host == "localhost":
            pass
        else:
            return host

    def handle_add_user(self, __socket: socket.socket, params: dict[str, str],
                        http_version: str) -> None:
        username = params.get("userName")
        if not username:
            self.logger.error("Missing userName!")
            return
        blob_str = params.get("blob")
        if not blob_str:
            self.logger.error("Missing blob!")
            return
        client_key_str = params.get("clientKey")
        if not client_key_str:
            self.logger.error("Missing clientKey!")
        with self.__connection_lock:
            if username == self.__connecting_username:
                self.logger.info(
                    "{} is already trying to connect.".format(username))
                __socket.send(http_version.encode())
                __socket.send(b" 403 Forbidden")
                __socket.send(self.__eol)
                __socket.send(self.__eol)
                return
        shared_key = util.int_to_bytes(
            self.__keys.compute_shared_key(
                base64.b64decode(client_key_str.encode())))
        blob_bytes = base64.b64decode(blob_str)
        iv = blob_bytes[:16]
        encrypted = blob_bytes[16:len(blob_bytes) - 20]
        checksum = blob_bytes[len(blob_bytes) - 20:]
        sha1 = SHA1.new()
        sha1.update(shared_key)
        base_key = sha1.digest()[:16]
        hmac = HMAC.new(base_key, digestmod=SHA1)
        hmac.update(b"checksum")
        checksum_key = hmac.digest()
        hmac = HMAC.new(base_key, digestmod=SHA1)
        hmac.update(b"encryption")
        encryption_key = hmac.digest()
        hmac = HMAC.new(checksum_key, digestmod=SHA1)
        hmac.update(encrypted)
        mac = hmac.digest()
        if mac != checksum:
            self.logger.error("Mac and checksum don't match!")
            __socket.send(http_version.encode())
            __socket.send(b" 400 Bad Request")
            __socket.send(self.__eol)
            __socket.send(self.__eol)
            return
        aes = AES.new(encryption_key[:16],
                      AES.MODE_CTR,
                      counter=Counter.new(128,
                                          initial_value=int.from_bytes(
                                              iv, "big")))
        decrypted = aes.decrypt(encrypted)
        self.close_session()
        with self.__connection_lock:
            self.__connecting_username = username
        self.logger.info("Accepted new user from {}. [deviceId: {}]".format(
            params.get("deviceName"), self.__inner.device_id))
        response = json.dumps(self.__default_successful_add_user)
        __socket.send(http_version.encode())
        __socket.send(b" 200 OK")
        __socket.send(self.__eol)
        __socket.send(b"Content-Length: ")
        __socket.send(str(len(response)).encode())
        __socket.send(self.__eol)
        __socket.send(self.__eol)
        __socket.send(response.encode())
        self.__session = Session.Builder(self.__inner.conf) \
            .set_device_id(self.__inner.device_id) \
            .set_device_name(self.__inner.device_name) \
            .set_device_type(self.__inner.device_type) \
            .set_preferred_locale(self.__inner.preferred_locale) \
            .blob(username, decrypted) \
            .create()
        with self.__connection_lock:
            self.__connecting_username = None
        for session_listener in self.__session_listeners:
            session_listener.session_changed(self.__session)

    def handle_get_info(self, __socket: socket.socket,
                        http_version: str) -> None:
        info = copy.deepcopy(self.__default_get_info_fields)
        info["deviceID"] = self.__inner.device_id
        info["remoteName"] = self.__inner.device_name
        info["publicKey"] = base64.b64encode(
            self.__keys.public_key_bytes()).decode()
        info["deviceType"] = Connect.DeviceType.Name(self.__inner.device_type)
        with self.__connection_lock:
            info[
                "activeUser"] = self.__connecting_username if self.__connecting_username is not None else self.__session.username(
                ) if self.has_valid_session() else ""
        __socket.send(http_version.encode())
        __socket.send(b" 200 OK")
        __socket.send(self.__eol)
        __socket.send(b"Content-Type: application/json")
        __socket.send(self.__eol)
        __socket.send(self.__eol)
        __socket.send(json.dumps(info).encode())

    def has_valid_session(self) -> bool:
        valid = self.__session and self.__session.is_valid()
        if not valid:
            self.__session = None
        return valid

    def parse_path(self, path: str) -> dict[str, str]:
        url = "https://host" + path
        parsed = {}
        params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        for key, values in params.items():
            for value in values:
                parsed[key] = value
        return parsed

    def remove_session_listener(self, listener: SessionListener):
        self.__session_listeners.remove(listener)

    class Builder(Session.Builder):
        listen_port: int = -1

        def set_listen_port(self, listen_port: int):
            self.listen_port = listen_port
            return self

        def create(self) -> ZeroconfServer:
            return ZeroconfServer(
                ZeroconfServer.Inner(self.device_type, self.device_name,
                                     self.device_id, self.preferred_locale,
                                     self.conf), self.listen_port)

    class HttpRunner(Closeable, Runnable):
        __should_stop = False
        __socket: socket.socket
        __worker = concurrent.futures.ThreadPoolExecutor()
        __zeroconf_server: ZeroconfServer

        def __init__(self, zeroconf_server: ZeroconfServer, port: int):
            self.__socket = socket.socket()
            self.__socket.bind((".".join(["0"] * 4), port))
            self.__socket.listen(5)
            self.__zeroconf_server = zeroconf_server
            self.__zeroconf_server.logger.info(
                "Zeroconf HTTP server started successfully on port {}!".format(
                    port))

        def close(self) -> None:
            pass

        def run(self):
            while not self.__should_stop:
                __socket, address = self.__socket.accept()

                def anonymous():
                    self.__handle(__socket)
                    __socket.close()

                self.__worker.submit(anonymous)

        def __handle(self, __socket: socket.socket) -> None:
            request = io.BytesIO(__socket.recv(1024 * 1024))
            request_line = request.readline().strip().split(b" ")
            if len(request_line) != 3:
                self.__zeroconf_server.logger.warning(
                    "Unexpected request line: {}".format(request_line))
            method = request_line[0].decode()
            path = request_line[1].decode()
            http_version = request_line[2].decode()
            headers = {}
            while True:
                header = request.readline().strip()
                if not header:
                    break
                split = header.split(b":")
                headers[split[0].decode()] = split[1].strip().decode()
            if not self.__zeroconf_server.has_valid_session():
                self.__zeroconf_server.logger.debug(
                    "Handling request: {}, {}, {}, headers: {}".format(
                        method, path, http_version, headers))
            params = {}
            if method == "POST":
                content_type = headers.get("Content-Type")
                if content_type != "application/x-www-form-urlencoded":
                    self.__zeroconf_server.logger.error(
                        "Bad Content-Type: {}".format(content_type))
                    return
                content_length_str = headers.get("Content-Length")
                if content_length_str is None:
                    self.__zeroconf_server.logger.error(
                        "Missing Content-Length header!")
                    return
                content_length = int(content_length_str)
                body = request.read(content_length).decode()
                pairs = body.split("&")
                for pair in pairs:
                    split = pair.split("=")
                    params[urllib.parse.unquote(
                        split[0])] = urllib.parse.unquote(split[1])
            else:
                params = self.__zeroconf_server.parse_path(path)
            action = params.get("action")
            if action is None:
                self.__zeroconf_server.logger.debug(
                    "Request is missing action.")
                return
            self.handle_request(__socket, http_version, action, params)

        def handle_request(self, __socket: socket.socket, http_version: str,
                           action: str, params: dict[str, str]) -> None:
            if action == "addUser":
                if params is None:
                    raise RuntimeError
                self.__zeroconf_server.handle_add_user(__socket, params,
                                                       http_version)
            elif action == "getInfo":
                self.__zeroconf_server.handle_get_info(__socket, http_version)
            else:
                self.__zeroconf_server.logger.warning(
                    "Unknown action: {}".format(action))

    class Inner:
        conf: typing.Final[Session.Configuration]
        device_name: typing.Final[str]
        device_id: typing.Final[str]
        device_type: typing.Final[Connect.DeviceType]
        preferred_locale: typing.Final[str]

        def __init__(self, device_type: Connect.DeviceType, device_name: str,
                     device_id: str, preferred_locale: str,
                     conf: Session.Configuration):
            self.conf = conf
            self.device_name = device_name
            self.device_id = util.random_hex_string(
                40).lower() if not device_id else device_id
            self.device_type = device_type
            self.preferred_locale = preferred_locale
