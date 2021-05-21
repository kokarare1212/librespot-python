from __future__ import annotations

import base64
import json
import logging
import os
import sched
import socket
import struct
import threading
import time
import typing

import defusedxml.ElementTree
import requests
from Crypto.Hash import HMAC
from Crypto.Hash import SHA1
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from librespot.audio import AudioKeyManager
from librespot.audio import PlayableContentFeeder
from librespot.audio.cdn import CdnManager
from librespot.audio.storage import ChannelManager
from librespot.cache import CacheManager
from librespot.common.Utils import Utils
from librespot.core import ApResolver
from librespot.core import EventService
from librespot.core import SearchManager
from librespot.core import TokenProvider
from librespot.crypto import CipherPair
from librespot.crypto import DiffieHellman
from librespot.crypto import Packet
from librespot.dealer import ApiClient
from librespot.dealer import DealerClient
from librespot.mercury import MercuryClient
from librespot.mercury import SubListener
from librespot.proto import Authentication
from librespot.proto import Connect
from librespot.proto import Keyexchange
from librespot.proto.ExplicitContentPubsub import UserAttributesUpdate
from librespot.standard import BytesInputStream
from librespot.standard import Closeable
from librespot.standard import Proxy
from librespot.Version import Version


class Session(Closeable, SubListener, DealerClient.MessageListener):
    _LOGGER: logging = logging.getLogger(__name__)
    _serverKey: bytes = bytes([
        0xAC,
        0xE0,
        0x46,
        0x0B,
        0xFF,
        0xC2,
        0x30,
        0xAF,
        0xF4,
        0x6B,
        0xFE,
        0xC3,
        0xBF,
        0xBF,
        0x86,
        0x3D,
        0xA1,
        0x91,
        0xC6,
        0xCC,
        0x33,
        0x6C,
        0x93,
        0xA1,
        0x4F,
        0xB3,
        0xB0,
        0x16,
        0x12,
        0xAC,
        0xAC,
        0x6A,
        0xF1,
        0x80,
        0xE7,
        0xF6,
        0x14,
        0xD9,
        0x42,
        0x9D,
        0xBE,
        0x2E,
        0x34,
        0x66,
        0x43,
        0xE3,
        0x62,
        0xD2,
        0x32,
        0x7A,
        0x1A,
        0x0D,
        0x92,
        0x3B,
        0xAE,
        0xDD,
        0x14,
        0x02,
        0xB1,
        0x81,
        0x55,
        0x05,
        0x61,
        0x04,
        0xD5,
        0x2C,
        0x96,
        0xA4,
        0x4C,
        0x1E,
        0xCC,
        0x02,
        0x4A,
        0xD4,
        0xB2,
        0x0C,
        0x00,
        0x1F,
        0x17,
        0xED,
        0xC2,
        0x2F,
        0xC4,
        0x35,
        0x21,
        0xC8,
        0xF0,
        0xCB,
        0xAE,
        0xD2,
        0xAD,
        0xD7,
        0x2B,
        0x0F,
        0x9D,
        0xB3,
        0xC5,
        0x32,
        0x1A,
        0x2A,
        0xFE,
        0x59,
        0xF3,
        0x5A,
        0x0D,
        0xAC,
        0x68,
        0xF1,
        0xFA,
        0x62,
        0x1E,
        0xFB,
        0x2C,
        0x8D,
        0x0C,
        0xB7,
        0x39,
        0x2D,
        0x92,
        0x47,
        0xE3,
        0xD7,
        0x35,
        0x1A,
        0x6D,
        0xBD,
        0x24,
        0xC2,
        0xAE,
        0x25,
        0x5B,
        0x88,
        0xFF,
        0xAB,
        0x73,
        0x29,
        0x8A,
        0x0B,
        0xCC,
        0xCD,
        0x0C,
        0x58,
        0x67,
        0x31,
        0x89,
        0xE8,
        0xBD,
        0x34,
        0x80,
        0x78,
        0x4A,
        0x5F,
        0xC9,
        0x6B,
        0x89,
        0x9D,
        0x95,
        0x6B,
        0xFC,
        0x86,
        0xD7,
        0x4F,
        0x33,
        0xA6,
        0x78,
        0x17,
        0x96,
        0xC9,
        0xC3,
        0x2D,
        0x0D,
        0x32,
        0xA5,
        0xAB,
        0xCD,
        0x05,
        0x27,
        0xE2,
        0xF7,
        0x10,
        0xA3,
        0x96,
        0x13,
        0xC4,
        0x2F,
        0x99,
        0xC0,
        0x27,
        0xBF,
        0xED,
        0x04,
        0x9C,
        0x3C,
        0x27,
        0x58,
        0x04,
        0xB6,
        0xB2,
        0x19,
        0xF9,
        0xC1,
        0x2F,
        0x02,
        0xE9,
        0x48,
        0x63,
        0xEC,
        0xA1,
        0xB6,
        0x42,
        0xA0,
        0x9D,
        0x48,
        0x25,
        0xF8,
        0xB3,
        0x9D,
        0xD0,
        0xE8,
        0x6A,
        0xF9,
        0x48,
        0x4D,
        0xA1,
        0xC2,
        0xBA,
        0x86,
        0x30,
        0x42,
        0xEA,
        0x9D,
        0xB3,
        0x08,
        0x6C,
        0x19,
        0x0E,
        0x48,
        0xB3,
        0x9D,
        0x66,
        0xEB,
        0x00,
        0x06,
        0xA2,
        0x5A,
        0xEE,
        0xA1,
        0x1B,
        0x13,
        0x87,
        0x3C,
        0xD7,
        0x19,
        0xE6,
        0x55,
        0xBD,
    ])
    _keys: DiffieHellman = None
    _inner: Session.Inner = None
    _scheduler: sched.scheduler = sched.scheduler(time.time)
    _authLock: threading.Condition = threading.Condition()
    _authLockBool: bool = False
    _client: requests.Session = None
    _closeListeners: typing.List[Session.CloseListener] = []
    _closeListenersLock: threading.Condition = threading.Condition()
    _reconnectionListeners: typing.List[Session.ReconnectionListener] = []
    _reconnectionListenersLock: threading.Condition = threading.Condition()
    _userAttributes: typing.Dict[str, str] = {}
    _conn: Session.ConnectionHolder = None
    _cipherPair: CipherPair = None
    _receiver: Session.Receiver = None
    _apWelcome: Authentication.APWelcome = None
    _mercuryClient: MercuryClient = None
    _audioKeyManager: AudioKeyManager = None
    _channelManager: ChannelManager = None
    _tokenProvider: TokenProvider = None
    _cdnManager: CdnManager = None
    _cacheManager = None
    _dealer: DealerClient = None
    _api: ApiClient = None
    _search: SearchManager = None
    _contentFeeder: PlayableContentFeeder = None
    _eventService: EventService = None
    _countryCode: str = None
    _closed: bool = False
    _closing: bool = False
    _scheduledReconnect: sched.Event = None

    def __init__(self, inner: Session.Inner, addr: str):
        self._inner = inner
        self._keys = DiffieHellman()
        self._conn = Session.ConnectionHolder.create(addr, inner.conf)
        self._client = Session._create_client(self._inner.conf)

        self._LOGGER.info("Created new session! device_id: {}, ap: {}".format(
            inner.device_id, addr))

    @staticmethod
    def _create_client(conf: Session.Configuration) -> requests.Session:
        client = requests.Session()
        if conf.proxyAuth and conf.proxyType is not Proxy.Type.DIRECT:
            if conf.proxyAuth:
                proxy_setting = [
                    conf.proxyUsername,
                    conf.proxyPassword,
                    conf.proxyAddress,
                    conf.proxyPort,
                ]
            else:
                proxy_setting = [conf.proxyAddress, conf.proxyPort]
            client.proxies = {
                "http": "{}:{}@{}:{}".format(*proxy_setting),
                "https": "{}:{}@{}:{}".format(*proxy_setting),
            }

        return client

    @staticmethod
    def _read_blob_int(buffer: bytearray) -> int:
        lo = buffer[0]
        if (lo & 0x80) == 0:
            return lo
        hi = buffer[1]
        return lo & 0x7F | hi << 7

    def client(self) -> requests.Session:
        return self._client

    def _connect(self) -> None:
        acc = Session.Accumulator()

        # Send ClientHello

        nonce = os.urandom(0x10)

        client_hello = Keyexchange.ClientHello(
            build_info=Version.standard_build_info(),
            cryptosuites_supported=[
                Keyexchange.Cryptosuite.CRYPTO_SUITE_SHANNON
            ],
            login_crypto_hello=Keyexchange.LoginCryptoHelloUnion(
                diffie_hellman=Keyexchange.LoginCryptoDiffieHellmanHello(
                    gc=self._keys.public_key_array(), server_keys_known=1), ),
            client_nonce=nonce,
            padding=bytes([0x1E]),
        )

        client_hello_bytes = client_hello.SerializeToString()
        length = 2 + 4 + len(client_hello_bytes)
        self._conn.write_byte(0)
        self._conn.write_byte(4)
        self._conn.write_int(length)
        self._conn.write(client_hello_bytes)
        self._conn.flush()

        acc.write_byte(0)
        acc.write_byte(4)
        acc.write_int(length)
        acc.write(client_hello_bytes)

        # Read APResponseMessage

        length = self._conn.read_int()
        acc.write_int(length)
        buffer = self._conn.read(length - 4)
        acc.write(buffer)

        ap_response_message = Keyexchange.APResponseMessage()
        ap_response_message.ParseFromString(buffer)
        shared_key = Utils.to_byte_array(
            self._keys.compute_shared_key(
                ap_response_message.challenge.login_crypto_challenge.
                diffie_hellman.gs))

        # Check gs_signature

        rsa = RSA.construct((int.from_bytes(self._serverKey, "big"), 65537))
        pkcs1_v1_5 = PKCS1_v1_5.new(rsa)
        sha1 = SHA1.new()
        sha1.update(ap_response_message.challenge.login_crypto_challenge.
                    diffie_hellman.gs)
        # noinspection PyTypeChecker
        if not pkcs1_v1_5.verify(
                sha1,
                ap_response_message.challenge.login_crypto_challenge.
                diffie_hellman.gs_signature,
        ):
            raise RuntimeError("Failed signature check!")

        # Solve challenge

        data = b""

        for i in range(1, 6):
            # noinspection PyTypeChecker
            mac = HMAC.new(shared_key, digestmod=SHA1)
            mac.update(acc.array())
            mac.update(bytes([i]))
            data += mac.digest()

        # noinspection PyTypeChecker
        mac = HMAC.new(data[:20], digestmod=SHA1)
        mac.update(acc.array())

        challenge = mac.digest()
        client_response_plaintext = Keyexchange.ClientResponsePlaintext(
            login_crypto_response=Keyexchange.LoginCryptoResponseUnion(
                diffie_hellman=Keyexchange.LoginCryptoDiffieHellmanResponse(
                    hmac=challenge)),
            pow_response=Keyexchange.PoWResponseUnion(),
            crypto_response=Keyexchange.CryptoResponseUnion(),
        )

        client_response_plaintext_bytes = client_response_plaintext.SerializeToString(
        )
        length = 4 + len(client_response_plaintext_bytes)
        self._conn.write_int(length)
        self._conn.write(client_response_plaintext_bytes)
        self._conn.flush()

        try:
            self._conn.set_timeout(1)
            scrap = self._conn.read(4)
            if 4 == len(scrap):
                length = ((scrap[0] << 24)
                          | (scrap[1] << 16)
                          | (scrap[2] << 8)
                          | (scrap[3] & 0xFF))
                payload = self._conn.read(length - 4)
                failed = Keyexchange.APResponseMessage()
                failed.ParseFromString(payload)
                raise RuntimeError(failed)
        except socket.timeout:
            pass
        finally:
            self._conn.set_timeout(0)

        with self._authLock:
            self._cipherPair = CipherPair(data[20:52], data[52:84])

            self._authLockBool = True

        self._LOGGER.info("Connection successfully!")

    def _authenticate(self,
                      credentials: Authentication.LoginCredentials) -> None:
        self._authenticate_partial(credentials, False)

        with self._authLock:
            self._mercuryClient = MercuryClient(self)
            self._tokenProvider = TokenProvider.TokenProvider(self)
            self._audioKeyManager = AudioKeyManager.AudioKeyManager(self)
            self._channelManager = ChannelManager(self)
            self._api = ApiClient.ApiClient(self)
            self._cdnManager = CdnManager(self)
            self._contentFeeder = PlayableContentFeeder.PlayableContentFeeder(
                self)
            self._cacheManager = CacheManager(self)
            self._dealer = DealerClient(self)
            self._search = SearchManager.SearchManager(self)
            self._eventService = EventService.EventService(self)

            self._authLockBool = False
            self._authLock.notify_all()

        self._eventService.language(self._inner.preferred_locale)
        # TimeProvider.init(self)
        self._dealer.connect()

        self._LOGGER.info("Authenticated as {}!".format(
            self._apWelcome.canonical_username))
        self.mercury().interested_in("spotify:user:attributes:update", self)
        self.dealer().add_message_listener(
            self, "hm://connect-state/v1/connect/logout")

    def _authenticate_partial(self,
                              credentials: Authentication.LoginCredentials,
                              remove_lock: bool) -> None:
        if self._cipherPair is None:
            raise RuntimeError("Connection not established!")

        client_response_encrypted = Authentication.ClientResponseEncrypted(
            login_credentials=credentials,
            system_info=Authentication.SystemInfo(
                os=Authentication.Os.OS_UNKNOWN,
                cpu_family=Authentication.CpuFamily.CPU_UNKNOWN,
                system_information_string=Version.system_info_string(),
                device_id=self._inner.device_id,
            ),
            version_string=Version.version_string(),
        )

        self._send_unchecked(Packet.Type.login,
                             client_response_encrypted.SerializeToString())

        packet = self._cipherPair.receive_encoded(self._conn)
        if packet.is_cmd(Packet.Type.ap_welcome):
            self._apWelcome = Authentication.APWelcome()
            self._apWelcome.ParseFromString(packet.payload)

            self._receiver = Session.Receiver(self)

            bytes0x0f = os.urandom(20)
            self._send_unchecked(Packet.Type.unknown_0x0f, bytes0x0f)

            preferred_locale = bytes()
            preferred_locale += bytes([0x00, 0x00, 0x10, 0x00, 0x02])
            preferred_locale += "preferred-locale".encode()
            preferred_locale += self._inner.preferred_locale.encode()
            self._send_unchecked(Packet.Type.preferred_locale,
                                 preferred_locale)

            if remove_lock:
                with self._authLock:
                    self._authLockBool = False
                    self._authLock.notify_all()

            if self._inner.conf.store_credentials:
                reusable = self._apWelcome.reusable_auth_credentials
                reusable_type = Authentication.AuthenticationType.Name(
                    self._apWelcome.reusable_auth_credentials_type)

                if self._inner.conf.stored_credentials_file is None:
                    raise TypeError()

                with open(self._inner.conf.stored_credentials_file, "w") as f:
                    json.dump(
                        {
                            "username": self._apWelcome.canonical_username,
                            "credentials": base64.b64encode(reusable).decode(),
                            "type": reusable_type,
                        },
                        f,
                    )

        elif packet.is_cmd(Packet.Type.auth_failure):
            ap_login_failed = Keyexchange.APLoginFailed()
            ap_login_failed.ParseFromString(packet.payload)
            raise Session.SpotifyAuthenticationException(ap_login_failed)
        else:
            raise RuntimeError("Unknown CMD 0x" + packet.cmd.hex())

    def close(self) -> None:
        self._LOGGER.info("Closing session. device_id: {}".format(
            self._inner.device_id))

        self._closing = True

        if self._dealer is not None:
            self._dealer.close()
            # noinspection PyTypeChecker
            self._dealer = None

        if self._audioKeyManager is not None:
            # noinspection PyTypeChecker
            self._audioKeyManager = None

        if self._channelManager is not None:
            self._channelManager.close()
            # noinspection PyTypeChecker
            self._channelManager = None

        if self._eventService is not None:
            self._eventService.close()
            # noinspection PyTypeChecker
            self._eventService = None

        if self._mercuryClient is not None:
            self._mercuryClient.close()
            # noinspection PyTypeChecker
            self._mercuryClient = None

        if self._receiver is not None:
            self._receiver.stop()
            # noinspection PyTypeChecker
            self._receiver = None

        if self._client is not None:
            # noinspection PyTypeChecker
            self._client = None

        if self._conn is not None:
            self._conn.sock.close()
            # noinspection PyTypeChecker
            self._conn = None

        with self._authLock:
            self._apWelcome = None
            # noinspection PyTypeChecker
            self._cipherPair = None
            self._closed = True

        with self._closeListenersLock:
            for listener in self._closeListeners:
                listener.on_closed()
            self._closeListeners: typing.List[Session.CloseListener] = []

        self._reconnectionListeners: typing.List[
            Session.ReconnectionListener] = []

        self._LOGGER.info("Closed session. device_id: {}".format(
            self._inner.device_id))

    def _send_unchecked(self, cmd: bytes, payload: bytes) -> None:
        self._cipherPair.send_encoded(self._conn, cmd, payload)

    def _wait_auth_lock(self) -> None:
        if self._closing and self._conn is None:
            self._LOGGER.debug("Connection was broken while closing.")
            return

        if self._closed:
            raise RuntimeError("Session is closed!")

        with self._authLock:
            if self._cipherPair is None or self._authLockBool:
                self._authLock.wait()

    def send(self, cmd: bytes, payload: bytes):
        if self._closing and self._conn is None:
            self._LOGGER.debug("Connection was broken while closing.")
            return

        if self._closed:
            raise RuntimeError("Session is closed!")

        with self._authLock:
            if self._cipherPair is None or self._authLockBool:
                self._authLock.wait()

            self._send_unchecked(cmd, payload)

    def mercury(self) -> MercuryClient:
        self._wait_auth_lock()
        if self._mercuryClient is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._mercuryClient

    def audio_key(self) -> AudioKeyManager:
        self._wait_auth_lock()
        if self._audioKeyManager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._audioKeyManager

    def cache(self) -> CacheManager:
        self._wait_auth_lock()
        if self._cacheManager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._cacheManager

    def cdn(self) -> CdnManager:
        self._wait_auth_lock()
        if self._cdnManager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._cdnManager

    def channel(self) -> ChannelManager:
        self._wait_auth_lock()
        if self._channelManager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._channelManager

    def tokens(self) -> TokenProvider:
        self._wait_auth_lock()
        if self._tokenProvider is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._tokenProvider

    def dealer(self) -> DealerClient:
        self._wait_auth_lock()
        if self._dealer is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._dealer

    def api(self) -> ApiClient:
        self._wait_auth_lock()
        if self._api is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._api

    def content_feeder(self) -> PlayableContentFeeder:
        if self._contentFeeder is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._contentFeeder

    def search(self) -> SearchManager:
        self._wait_auth_lock()
        if self._search is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._search

    def event_service(self) -> EventService:
        self._wait_auth_lock()
        if self._eventService is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._eventService

    def username(self) -> str:
        return self.ap_welcome().canonical_username

    def ap_welcome(self) -> Authentication.APWelcome:
        self._wait_auth_lock()
        if self._apWelcome is None:
            raise RuntimeError("Session isn't authenticated!")
        return self._apWelcome

    def is_valid(self) -> bool:
        if self._closed:
            return False

        self._wait_auth_lock()
        return self._apWelcome is not None and self._conn is not None

    def reconnecting(self) -> bool:
        return not self._closing and not self._closed and self._conn is None

    def country_code(self) -> str:
        return self._countryCode

    def device_id(self) -> str:
        return self._inner.device_id

    def preferred_locale(self) -> str:
        return self._inner.preferred_locale

    def device_type(self) -> Connect.DeviceType:
        return self._inner.device_type

    def device_name(self) -> str:
        return self._inner.device_name

    def configuration(self) -> Session.Configuration:
        return self._inner.conf

    def _reconnect(self) -> None:
        with self._reconnectionListenersLock:
            for listener in self._reconnectionListeners:
                listener.on_connection_dropped()

        if self._conn is not None:
            self._conn.sock.close()
            self._receiver.stop()

        self._conn = Session.ConnectionHolder.create(
            ApResolver.get_random_accesspoint(), self._inner.conf)
        self._connect()
        self._authenticate_partial(
            Authentication.LoginCredentials(
                typ=self._apWelcome.reusable_auth_credentials_type,
                username=self._apWelcome.canonical_username,
                auth_data=self._apWelcome.reusable_auth_credentials,
            ),
            True,
        )

        self._LOGGER.info("Re-authenticated as {}!".format(
            self._apWelcome.canonical_username))

        with self._reconnectionListenersLock:
            for listener in self._reconnectionListeners:
                listener.on_connection_established()

    def add_close_listener(self, listener: CloseListener) -> None:
        if listener not in self._closeListeners:
            self._closeListeners.append(listener)

    def add_reconnection_listener(self,
                                  listener: ReconnectionListener) -> None:
        if listener not in self._reconnectionListeners:
            self._reconnectionListeners.append(listener)

    def remove_reconnection_listener(self,
                                     listener: ReconnectionListener) -> None:
        self._reconnectionListeners.remove(listener)

    def _parse_product_info(self, data) -> None:
        doc = defusedxml.ElementTree.fromstring(data)

        products = doc
        if products is None:
            return

        product = products[0]
        if product is None:
            return

        for i in range(len(product)):
            self._userAttributes[product[i].tag] = product[i].text

        self._LOGGER.debug("Parsed product info: {}".format(
            self._userAttributes))

    def get_user_attribute(self, key: str, fallback: str = None) -> str:
        return (self._userAttributes.get(key)
                if self._userAttributes.get(key) is not None else fallback)

    def event(self, resp: MercuryClient.Response) -> None:
        if resp.uri == "spotify:user:attributes:update":
            attributes_update = UserAttributesUpdate()
            attributes_update.ParseFromString(resp.payload)

            for pair in attributes_update.pairs_list:
                self._userAttributes[pair.key] = pair.value
                self._LOGGER.info("Updated user attribute: {} -> {}".format(
                    pair.key, pair.value))

    def on_message(self, uri: str, headers: typing.Dict[str, str],
                   payload: bytes) -> None:
        if uri == "hm://connect-state/v1/connect/logout":
            self.close()

    class ReconnectionListener:
        def on_connection_dropped(self) -> None:
            pass

        def on_connection_established(self) -> None:
            pass

    class CloseListener:
        def on_closed(self) -> None:
            pass

    class Inner:
        device_type: Connect.DeviceType = None
        device_name: str = None
        device_id: str = None
        conf = None
        preferred_locale: str = None

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

    class AbsBuilder:
        conf = None
        device_id = None
        device_name = "librespot-python"
        device_type = Connect.DeviceType.COMPUTER
        preferred_locale = "en"

        def __init__(self, conf: Session.Configuration = None):
            if conf is None:
                self.conf = Session.Configuration.Builder().build()
            else:
                self.conf = conf

        def set_preferred_locale(self, locale: str) -> Session.AbsBuilder:
            if len(locale) != 2:
                raise TypeError("Invalid locale: {}".format(locale))

            self.preferred_locale = locale
            return self

        def set_device_name(self, device_name: str) -> Session.AbsBuilder:
            self.device_name = device_name
            return self

        def set_device_id(self, device_id: str) -> Session.AbsBuilder:
            if self.device_id is not None and len(device_id) != 40:
                raise TypeError("Device ID must be 40 chars long.")

            self.device_id = device_id
            return self

        def set_device_type(
                self, device_type: Connect.DeviceType) -> Session.AbsBuilder:
            self.device_type = device_type
            return self

    class Builder(AbsBuilder):
        login_credentials: Authentication.LoginCredentials = None

        def stored(self):
            pass

        def stored_file(self,
                        stored_credentials: str = None) -> Session.Builder:
            if stored_credentials is None:
                stored_credentials = self.conf.stored_credentials_file
            if os.path.isfile(stored_credentials):
                try:
                    with open(stored_credentials) as f:
                        obj = json.load(f)
                except json.JSONDecodeError:
                    pass
                else:
                    try:
                        self.login_credentials = Authentication.LoginCredentials(
                            typ=Authentication.AuthenticationType.Value(
                                obj["type"]),
                            username=obj["username"],
                            auth_data=base64.b64decode(obj["credentials"]),
                        )
                    except KeyError:
                        pass

            return self

        def user_pass(self, username: str, password: str) -> Session.Builder:
            self.login_credentials = Authentication.LoginCredentials(
                username=username,
                typ=Authentication.AuthenticationType.AUTHENTICATION_USER_PASS,
                auth_data=password.encode(),
            )
            return self

        def create(self) -> Session:
            if self.login_credentials is None:
                raise RuntimeError("You must select an authentication method.")

            session = Session(
                Session.Inner(
                    self.device_type,
                    self.device_name,
                    self.preferred_locale,
                    self.conf,
                    self.device_id,
                ),
                ApResolver.get_random_accesspoint(),
            )
            session._connect()
            session._authenticate(self.login_credentials)
            return session

    class Configuration:
        # Proxy
        proxyEnabled: bool
        proxyType: Proxy.Type
        proxyAddress: str
        proxyPort: int
        proxyAuth: bool
        proxyUsername: str
        proxyPassword: str

        # Cache
        cache_enabled: bool
        cache_dir: str
        do_cache_clean_up: bool

        # Stored credentials
        store_credentials: bool
        stored_credentials_file: str

        # Fetching
        retry_on_chunk_error: bool

        def __init__(
            self,
            proxy_enabled: bool,
            proxy_type: Proxy.Type,
            proxy_address: str,
            proxy_port: int,
            proxy_auth: bool,
            proxy_username: str,
            proxy_password: str,
            cache_enabled: bool,
            cache_dir: str,
            do_cache_clean_up: bool,
            store_credentials: bool,
            stored_credentials_file: str,
            retry_on_chunk_error: bool,
        ):
            self.proxyEnabled = proxy_enabled
            self.proxyType = proxy_type
            self.proxyAddress = proxy_address
            self.proxyPort = proxy_port
            self.proxyAuth = proxy_auth
            self.proxyUsername = proxy_username
            self.proxyPassword = proxy_password
            self.cache_enabled = cache_enabled
            self.cache_dir = cache_dir
            self.do_cache_clean_up = do_cache_clean_up
            self.store_credentials = store_credentials
            self.stored_credentials_file = stored_credentials_file
            self.retry_on_chunk_error = retry_on_chunk_error

        class Builder:
            # Proxy
            proxyEnabled: bool = False
            proxyType: Proxy.Type = None
            proxyAddress: str = None
            proxyPort: int = None
            proxyAuth: bool = None
            proxyUsername: str = None
            proxyPassword: str = None

            # Cache
            cache_enabled: bool = True
            cache_dir: str = os.path.join(os.getcwd(), "cache")
            do_cache_clean_up: bool = None

            # Stored credentials
            store_credentials: bool = True
            stored_credentials_file: str = os.path.join(
                os.getcwd(), "credentials.json")

            # Fetching
            retry_on_chunk_error: bool = None

            def set_proxy_enabled(
                    self,
                    proxy_enabled: bool) -> Session.Configuration.Builder:
                self.proxyEnabled = proxy_enabled
                return self

            def set_proxy_type(
                    self,
                    proxy_type: Proxy.Type) -> Session.Configuration.Builder:
                self.proxyType = proxy_type
                return self

            def set_proxy_address(
                    self, proxy_address: str) -> Session.Configuration.Builder:
                self.proxyAddress = proxy_address
                return self

            def set_proxy_auth(
                    self, proxy_auth: bool) -> Session.Configuration.Builder:
                self.proxyAuth = proxy_auth
                return self

            def set_proxy_username(
                    self,
                    proxy_username: str) -> Session.Configuration.Builder:
                self.proxyUsername = proxy_username
                return self

            def set_proxy_password(
                    self,
                    proxy_password: str) -> Session.Configuration.Builder:
                self.proxyPassword = proxy_password
                return self

            def set_cache_enabled(
                    self,
                    cache_enabled: bool) -> Session.Configuration.Builder:
                self.cache_enabled = cache_enabled
                return self

            def set_cache_dir(self,
                              cache_dir: str) -> Session.Configuration.Builder:
                self.cache_dir = cache_dir
                return self

            def set_do_cache_clean_up(
                    self,
                    do_cache_clean_up: bool) -> Session.Configuration.Builder:
                self.do_cache_clean_up = do_cache_clean_up
                return self

            def set_store_credentials(
                    self,
                    store_credentials: bool) -> Session.Configuration.Builder:
                self.store_credentials = store_credentials
                return self

            def set_stored_credential_file(
                    self, stored_credential_file: str
            ) -> Session.Configuration.Builder:
                self.stored_credentials_file = stored_credential_file
                return self

            def set_retry_on_chunk_error(
                    self, retry_on_chunk_error: bool
            ) -> Session.Configuration.Builder:
                self.retry_on_chunk_error = retry_on_chunk_error
                return self

            def build(self) -> Session.Configuration:
                return Session.Configuration(
                    self.proxyEnabled,
                    self.proxyType,
                    self.proxyAddress,
                    self.proxyPort,
                    self.proxyAuth,
                    self.proxyUsername,
                    self.proxyPassword,
                    self.cache_enabled,
                    self.cache_dir,
                    self.do_cache_clean_up,
                    self.store_credentials,
                    self.stored_credentials_file,
                    self.retry_on_chunk_error,
                )

    class SpotifyAuthenticationException(Exception):
        def __init__(self, login_failed: Keyexchange.APLoginFailed):
            super().__init__(
                Keyexchange.ErrorCode.Name(login_failed.error_code))

    class Accumulator:
        buffer: bytes = bytes()

        def array(self) -> bytes:
            return self.buffer

        def write(self, data: bytes) -> int:
            self.buffer += data
            return len(data)

        def write_byte(self, data: int) -> int:
            self.buffer += bytes([data])
            return 1

        def write_int(self, data: int) -> int:
            self.buffer += struct.pack(">i", data)
            return 4

    class ConnectionHolder:
        buffer: bytes = bytes()

        def __init__(self, sock: socket.socket):
            self.sock = sock

        @staticmethod
        def create(addr: str,
                   conf: Session.Configuration) -> Session.ConnectionHolder:
            ap_addr = addr.split(":")[0]
            ap_port = int(addr.split(":")[1])
            if not conf.proxyEnabled or conf.proxyType is Proxy.Type.DIRECT:
                sock = socket.socket()
                sock.connect((ap_addr, ap_port))
                return Session.ConnectionHolder(sock)

            if conf.proxyType is Proxy.Type.HTTP:
                sock = socket.socket()
                sock.connect((conf.proxyAddress, conf.proxyPort))

                sock.send("CONNECT {}:{} HTTP/1.0\n".format(ap_addr,
                                                            ap_port).encode())
                if conf.proxyAuth:
                    sock.send(
                        "Proxy-Authorization: {}\n".format(None).encode())

                sock.send(b"\n")

            elif conf.proxyType is Proxy.Type.SOCKS:
                pass
            else:
                raise RuntimeError()

        def flush(self) -> None:
            self.sock.send(self.buffer)
            self.buffer = b""

        def read(self, length: int) -> bytes:
            return self.sock.recv(length)

        def read_int(self) -> int:
            return struct.unpack(">i", self.sock.recv(4))[0]

        def set_timeout(self, timeout: int) -> None:
            if timeout == 0:
                self.sock.settimeout(None)
            else:
                self.sock.settimeout(timeout)

        def write(self, data: bytes) -> int:
            self.buffer += data
            return len(data)

        def write_byte(self, data: int) -> int:
            self.buffer += bytes([data])
            return 1

        def write_int(self, data: int) -> int:
            self.buffer += struct.pack(">i", data)
            return 4

        def write_short(self, data: int) -> int:
            self.buffer += struct.pack(">h", data)
            return 2

    class Receiver:
        session: Session = None
        thread: threading.Thread
        running: bool = True

        def __init__(self, session):
            self.session = session
            self.thread = threading.Thread(target=self.run)
            self.thread.setDaemon(True)
            self.thread.setName("session-packet-receiver")
            self.thread.start()

        def stop(self) -> None:
            self.running = False

        def run(self) -> None:
            self.session._LOGGER.debug("Session.Receiver started")

            while self.running:
                packet: Packet
                cmd: bytes
                try:
                    # noinspection PyProtectedMember
                    packet = self.session._cipherPair.receive_encoded(
                        self.session._conn)
                    cmd = Packet.Type.parse(packet.cmd)
                    if cmd is None:
                        self.session._LOGGER.info(
                            "Skipping unknown command cmd: 0x{}, payload: {}".
                            format(Utils.bytes_to_hex(packet.cmd),
                                   packet.payload))
                        continue
                except RuntimeError as ex:
                    if self.running:
                        self.session._LOGGER.fatal(
                            "Failed reading packet! {}".format(ex))
                        # noinspection PyProtectedMember
                        self.session._reconnect()
                    break

                if not self.running:
                    break
                if cmd == Packet.Type.ping:
                    # noinspection PyProtectedMember
                    if self.session._scheduledReconnect is not None:
                        # noinspection PyProtectedMember
                        self.session._scheduler.cancel(
                            self.session._scheduledReconnect)

                    def anonymous():
                        self.session._LOGGER.warning(
                            "Socket timed out. Reconnecting...")
                        self.session._reconnect()

                    # noinspection PyProtectedMember
                    self.session.scheduled_reconnect = self.session._scheduler.enter(
                        2 * 60 + 5, 1, anonymous)
                    self.session.send(Packet.Type.pong, packet.payload)
                    continue
                if cmd == Packet.Type.pong_ack:
                    continue
                if cmd == Packet.Type.country_code:
                    self.session.country_code = packet.payload.decode()
                    self.session._LOGGER.info(
                        "Received country_code: {}".format(
                            self.session.country_code))
                    continue
                if cmd == Packet.Type.license_version:
                    license_version = BytesInputStream(packet.payload)
                    license_id = license_version.read_short()
                    if license_id != 0:
                        buffer = license_version.read()
                        self.session._LOGGER.info(
                            "Received license_version: {}, {}".format(
                                license_id, buffer.decode()))
                    else:
                        self.session._LOGGER.info(
                            "Received license_version: {}".format(license_id))
                    continue
                if cmd == Packet.Type.unknown_0x10:
                    self.session._LOGGER.debug("Received 0x10: {}".format(
                        Utils.bytes_to_hex(packet.payload)))
                    continue
                if (cmd == Packet.Type.mercury_sub
                        or cmd == Packet.Type.mercury_unsub
                        or cmd == Packet.Type.mercury_event
                        or cmd == Packet.Type.mercury_req):
                    self.session.mercury().dispatch(packet)
                    continue
                if cmd == Packet.Type.aes_key or cmd == Packet.Type.aes_key_error:
                    self.session.audio_key().dispatch(packet)
                    continue
                if (cmd == Packet.Type.channel_error
                        or cmd == Packet.Type.stream_chunk_res):
                    self.session.channel().dispatch(packet)
                    continue
                if cmd == Packet.Type.product_info:
                    # noinspection PyProtectedMember
                    self.session._parse_product_info(packet.payload)
                    continue
                self.session._LOGGER.info("Skipping {}".format(
                    Utils.bytes_to_hex(cmd)))

            self.session._LOGGER.debug("Session.Receiver stopped")
