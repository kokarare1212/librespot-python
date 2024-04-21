from __future__ import annotations

import base64
import binascii
import concurrent.futures
import enum
import gzip
import io
import json
import logging
import os
import random
import sched
import socket
import struct
import threading
import time
import typing
import urllib.parse

import defusedxml.ElementTree
import requests
import websocket
from Cryptodome import Random
from Cryptodome.Cipher import AES
from Cryptodome.Hash import HMAC
from Cryptodome.Hash import SHA1
from Cryptodome.Protocol.KDF import PBKDF2
from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import PKCS1_v1_5

from librespot import util
from librespot import Version
from librespot.audio import AudioKeyManager
from librespot.audio import CdnManager
from librespot.audio import PlayableContentFeeder
from librespot.audio.storage import ChannelManager
from librespot.cache import CacheManager
from librespot.crypto import CipherPair
from librespot.crypto import DiffieHellman
from librespot.crypto import Packet
from librespot.mercury import MercuryClient
from librespot.mercury import MercuryRequests
from librespot.mercury import RawMercuryRequest
from librespot.metadata import AlbumId
from librespot.metadata import ArtistId
from librespot.metadata import EpisodeId
from librespot.metadata import PlaylistId
from librespot.metadata import ShowId
from librespot.metadata import TrackId
from librespot.proto import Authentication_pb2 as Authentication
from librespot.proto import ClientToken_pb2 as ClientToken
from librespot.proto import Connect_pb2 as Connect
from librespot.proto import Connectivity_pb2 as Connectivity
from librespot.proto import Keyexchange_pb2 as Keyexchange
from librespot.proto import Metadata_pb2 as Metadata
from librespot.proto import Playlist4External_pb2 as Playlist4External
from librespot.proto.ExplicitContentPubsub_pb2 import UserAttributesUpdate
from librespot.structure import Closeable
from librespot.structure import MessageListener
from librespot.structure import RequestListener
from librespot.structure import SubListener


class ApiClient(Closeable):
    """ """
    logger = logging.getLogger("Librespot:ApiClient")
    __base_url: str
    __client_token_str: str = None
    __session: Session

    def __init__(self, session: Session):
        self.__session = session
        self.__base_url = "https://{}".format(ApResolver.get_random_spclient())

    def build_request(
        self,
        method: str,
        suffix: str,
        headers: typing.Union[None, typing.Dict[str, str]],
        body: typing.Union[None, bytes],
    ) -> requests.PreparedRequest:
        """

        :param method: str:
        :param suffix: str:
        :param headers: typing.Union[None:
        :param typing.Dict[str:
        :param str]]:
        :param body: typing.Union[None:
        :param bytes]:

        """
        if self.__client_token_str is None:
            resp = self.__client_token()
            self.__client_token_str = resp.granted_token.token
            self.logger.debug("Updated client token: {}".format(
                self.__client_token_str))

        request = requests.PreparedRequest()
        request.method = method
        request.data = body
        request.headers = {}
        if headers is not None:
            request.headers = headers
        request.headers["Authorization"] = "Bearer {}".format(
            self.__session.tokens().get("playlist-read"))
        request.headers["client-token"] = self.__client_token_str
        request.url = self.__base_url + suffix
        return request

    def send(
        self,
        method: str,
        suffix: str,
        headers: typing.Union[None, typing.Dict[str, str]],
        body: typing.Union[None, bytes],
    ) -> requests.Response:
        """

        :param method: str:
        :param suffix: str:
        :param headers: typing.Union[None:
        :param typing.Dict[str:
        :param str]]:
        :param body: typing.Union[None:
        :param bytes]:

        """
        response = self.__session.client().send(
            self.build_request(method, suffix, headers, body))
        return response

    def put_connect_state(self, connection_id: str,
                          proto: Connect.PutStateRequest) -> None:
        """

        :param connection_id: str:
        :param proto: Connect.PutStateRequest:

        """
        response = self.send(
            "PUT",
            "/connect-state/v1/devices/{}".format(self.__session.device_id()),
            {
                "Content-Type": "application/protobuf",
                "X-Spotify-Connection-Id": connection_id,
            },
            proto.SerializeToString(),
        )
        if response.status_code == 413:
            self.logger.warning(
                "PUT state payload is too large: {} bytes uncompressed.".
                format(len(proto.SerializeToString())))
        elif response.status_code != 200:
            self.logger.warning("PUT state returned {}. headers: {}".format(
                response.status_code, response.headers))

    def get_metadata_4_track(self, track: TrackId) -> Metadata.Track:
        """

        :param track: TrackId:

        """
        response = self.send("GET",
                             "/metadata/4/track/{}".format(track.hex_id()),
                             None, None)
        ApiClient.StatusCodeException.check_status(response)
        body = response.content
        if body is None:
            raise RuntimeError()
        proto = Metadata.Track()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_episode(self, episode: EpisodeId) -> Metadata.Episode:
        """

        :param episode: EpisodeId:

        """
        response = self.send("GET",
                             "/metadata/4/episode/{}".format(episode.hex_id()),
                             None, None)
        ApiClient.StatusCodeException.check_status(response)
        body = response.content
        if body is None:
            raise IOError()
        proto = Metadata.Episode()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_album(self, album: AlbumId) -> Metadata.Album:
        """

        :param album: AlbumId:

        """
        response = self.send("GET",
                             "/metadata/4/album/{}".format(album.hex_id()),
                             None, None)
        ApiClient.StatusCodeException.check_status(response)

        body = response.content
        if body is None:
            raise IOError()
        proto = Metadata.Album()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_artist(self, artist: ArtistId) -> Metadata.Artist:
        """

        :param artist: ArtistId:

        """
        response = self.send("GET",
                             "/metadata/4/artist/{}".format(artist.hex_id()),
                             None, None)
        ApiClient.StatusCodeException.check_status(response)
        body = response.content
        if body is None:
            raise IOError()
        proto = Metadata.Artist()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_show(self, show: ShowId) -> Metadata.Show:
        """

        :param show: ShowId:

        """
        response = self.send("GET",
                             "/metadata/4/show/{}".format(show.hex_id()), None,
                             None)
        ApiClient.StatusCodeException.check_status(response)
        body = response.content
        if body is None:
            raise IOError()
        proto = Metadata.Show()
        proto.ParseFromString(body)
        return proto

    def get_playlist(self,
                     _id: PlaylistId) -> Playlist4External.SelectedListContent:
        """

        :param _id: PlaylistId:

        """
        response = self.send("GET",
                             "/playlist/v2/playlist/{}".format(_id.id()), None,
                             None)
        ApiClient.StatusCodeException.check_status(response)
        body = response.content
        if body is None:
            raise IOError()
        proto = Playlist4External.SelectedListContent()
        proto.ParseFromString(body)
        return proto

    def set_client_token(self, client_token):
        """

        :param client_token:

        """
        self.__client_token_str = client_token

    def __client_token(self):
        proto_req = ClientToken.ClientTokenRequest(
            request_type=ClientToken.ClientTokenRequestType.
            REQUEST_CLIENT_DATA_REQUEST,
            client_data=ClientToken.ClientDataRequest(
                client_id=MercuryRequests.keymaster_client_id,
                client_version=Version.version_name,
                connectivity_sdk_data=Connectivity.ConnectivitySdkData(
                    device_id=self.__session.device_id(),
                    platform_specific_data=Connectivity.PlatformSpecificData(
                        windows=Connectivity.NativeWindowsData(
                            something1=10,
                            something3=21370,
                            something4=2,
                            something6=9,
                            something7=332,
                            something8=33404,
                            something10=True,
                        ), ),
                ),
            ),
        )

        resp = requests.post(
            "https://clienttoken.spotify.com/v1/clienttoken",
            proto_req.SerializeToString(),
            headers={
                "Accept": "application/x-protobuf",
                "Content-Encoding": "",
            },
        )

        ApiClient.StatusCodeException.check_status(resp)

        proto_resp = ClientToken.ClientTokenResponse()
        proto_resp.ParseFromString(resp.content)
        return proto_resp

    class StatusCodeException(IOError):
        """ """
        code: int

        def __init__(self, response: requests.Response):
            super().__init__(response.status_code)
            self.code = response.status_code

        @staticmethod
        def check_status(response: requests.Response) -> None:
            """

            :param response: requests.Response:

            """
            if response.status_code != 200:
                raise ApiClient.StatusCodeException(response)


class ApResolver:
    """ """
    base_url = "https://apresolve.spotify.com/"

    @staticmethod
    def request(service_type: str) -> typing.Any:
        """Gets the specified ApResolve

        :param service_type: str:
        :returns: The resulting object will be returned

        """
        response = requests.get("{}?type={}".format(ApResolver.base_url,
                                                    service_type))
        if response.status_code != 200:
            if response.status_code == 502:
                raise RuntimeError(
                    f"ApResolve request failed with the following return value: {response.content}. Servers might be down!"
                )
        return response.json()

    @staticmethod
    def get_random_of(service_type: str) -> str:
        """Gets the specified random ApResolve url

        :param service_type: str:
        :returns: A random ApResolve url will be returned

        """
        pool = ApResolver.request(service_type)
        urls = pool.get(service_type)
        if urls is None or len(urls) == 0:
            raise RuntimeError("No ApResolve url available")
        return random.choice(urls)

    @staticmethod
    def get_random_dealer() -> str:
        """Get dealer endpoint url


        :returns: dealer endpoint url

        """
        return ApResolver.get_random_of("dealer")

    @staticmethod
    def get_random_spclient() -> str:
        """Get spclient endpoint url


        :returns: spclient endpoint url

        """
        return ApResolver.get_random_of("spclient")

    @staticmethod
    def get_random_accesspoint() -> str:
        """Get accesspoint endpoint url


        :returns: accesspoint endpoint url

        """
        return ApResolver.get_random_of("accesspoint")


class DealerClient(Closeable):
    """ """
    logger = logging.getLogger("Librespot:DealerClient")
    __connection: typing.Union[ConnectionHolder, None]
    __last_scheduled_reconnection: typing.Union[sched.Event, None]
    __message_listeners: typing.Dict[MessageListener, typing.List[str]] = {}
    __message_listeners_lock = threading.Condition()
    __request_listeners: typing.Dict[str, RequestListener] = {}
    __request_listeners_lock = threading.Condition()
    __scheduler = sched.scheduler()
    __session: Session
    __worker = concurrent.futures.ThreadPoolExecutor()

    def __init__(self, session: Session):
        self.__session = session

    def add_message_listener(self, listener: MessageListener,
                             uris: list[str]) -> None:
        """

        :param listener: MessageListener:
        :param uris: list[str]:

        """
        with self.__message_listeners_lock:
            if listener in self.__message_listeners:
                raise TypeError(
                    "A listener for {} has already been added.".format(uris))
            self.__message_listeners[listener] = uris
            self.__message_listeners_lock.notify_all()

    def add_request_listener(self, listener: RequestListener, uri: str):
        """

        :param listener: RequestListener:
        :param uri: str:

        """
        with self.__request_listeners_lock:
            if uri in self.__request_listeners:
                raise TypeError(
                    "A listener for '{}' has already been added.".format(uri))
            self.__request_listeners[uri] = listener
            self.__request_listeners_lock.notify_all()

    def close(self) -> None:
        """ """
        self.__worker.shutdown()

    def connect(self) -> None:
        """ """
        self.__connection = DealerClient.ConnectionHolder(
            self.__session,
            self,
            "wss://{}/?access_token={}".format(
                ApResolver.get_random_dealer(),
                self.__session.tokens().get("playlist-read"),
            ),
        )

    def connection_invalided(self) -> None:
        """ """
        self.__connection = None
        self.logger.debug("Scheduled reconnection attempt in 10 seconds...")

        def anonymous():
            """ """
            self.__last_scheduled_reconnection = None
            self.connect()

        self.__last_scheduled_reconnection = self.__scheduler.enter(
            10, 1, anonymous)

    def handle_message(self, obj: typing.Any) -> None:
        """

        :param obj: typing.Any:

        """
        uri = obj.get("uri")
        headers = self.__get_headers(obj)
        payloads = obj.get("payloads")
        decoded_payloads: typing.Any
        if payloads is not None:
            if headers.get("Content-Type") == "application/json":
                decoded_payloads = payloads
            elif headers.get("Content-Type") == "plain/text":
                decoded_payloads = payloads
            else:
                decoded_payloads = base64.b64decode(payloads)
                if headers.get("Transfer-Encoding") == "gzip":
                    decoded_payloads = gzip.decompress(decoded_payloads)
        else:
            decoded_payloads = b""
        interesting = False
        with self.__message_listeners_lock:
            for listener in self.__message_listeners:
                dispatched = False
                keys = self.__message_listeners.get(listener)
                for key in keys:
                    if uri.startswith(key) and not dispatched:
                        interesting = True

                        def anonymous():
                            """ """
                            listener.on_message(uri, headers, decoded_payloads)

                        self.__worker.submit(anonymous)
                        dispatched = True
        if not interesting:
            self.logger.debug("Couldn't dispatch message: {}".format(uri))

    def handle_request(self, obj: typing.Any) -> None:
        """

        :param obj: typing.Any:

        """
        mid = obj.get("message_ident")
        key = obj.get("key")
        headers = self.__get_headers(obj)
        payload = obj.get("payload")
        if headers.get("Transfer-Encoding") == "gzip":
            gz = base64.b64decode(payload.get("compressed"))
            payload = json.loads(gzip.decompress(gz))
        pid = payload.get("message_id")
        sender = payload.get("sent_by_device_id")
        command = payload.get("command")
        self.logger.debug(
            "Received request. [mid: {}, key: {}, pid: {}, sender: {}, command: {}]"
            .format(mid, key, pid, sender, command))
        interesting = False
        with self.__request_listeners_lock:
            for mid_prefix in self.__request_listeners:
                if mid.startswith(mid_prefix):
                    listener = self.__request_listeners.get(mid_prefix)
                    interesting = True

                    def anonymous():
                        """ """
                        result = listener.on_request(mid, pid, sender, command)
                        if self.__connection is not None:
                            self.__connection.send_reply(key, result)
                        self.logger.warning(
                            "Handled request. [key: {}, result: {}]".format(
                                key, result))

                    self.__worker.submit(anonymous)
        if not interesting:
            self.logger.debug("Couldn't dispatch request: {}".format(mid))

    def remove_message_listener(self, listener: MessageListener) -> None:
        """

        :param listener: MessageListener:

        """
        with self.__message_listeners_lock:
            self.__message_listeners.pop(listener)

    def remove_request_listener(self, listener: RequestListener) -> None:
        """

        :param listener: RequestListener:

        """
        with self.__request_listeners_lock:
            request_listeners = {}
            for key, value in self.__request_listeners.items():
                if value != listener:
                    request_listeners[key] = value
            self.__request_listeners = request_listeners

    def wait_for_listener(self) -> None:
        """ """
        with self.__message_listeners_lock:
            if self.__message_listeners == {}:
                return
            self.__message_listeners_lock.wait()

    def __get_headers(self, obj: typing.Any) -> dict[str, str]:
        headers = obj.get("headers")
        if headers is None:
            return {}
        return headers

    class ConnectionHolder(Closeable):
        """ """
        __closed = False
        __dealer_client: DealerClient
        __last_scheduled_ping: sched.Event
        __received_pong = False
        __scheduler = sched.scheduler()
        __session: Session
        __url: str
        __ws: websocket.WebSocketApp

        def __init__(self, session: Session, dealer_client: DealerClient,
                     url: str):
            self.__session = session
            self.__dealer_client = dealer_client
            self.__url = url
            self.__ws = websocket.WebSocketApp(url)

        def close(self):
            """ """
            if not self.__closed:
                self.__ws.close()
                self.__closed = True
            if self.__last_scheduled_ping is not None:
                self.__scheduler.cancel(self.__last_scheduled_ping)

        def on_failure(self, ws: websocket.WebSocketApp, error):
            """

            :param ws: websocket.WebSocketApp:
            :param error:

            """
            if self.__closed:
                return
            self.__dealer_client.logger.warning(
                "An exception occurred. Reconnecting...")
            self.close()

        def on_message(self, ws: websocket.WebSocketApp, text: str):
            """

            :param ws: websocket.WebSocketApp:
            :param text: str:

            """
            obj = json.loads(text)
            self.__dealer_client.wait_for_listener()
            typ = MessageType.parse(obj.get("type"))
            if typ == MessageType.MESSAGE:
                self.__dealer_client.handle_message(obj)
            elif typ == MessageType.REQUEST:
                self.__dealer_client.handle_request(obj)
            elif typ == MessageType.PONG:
                self.__received_pong = True
            elif typ == MessageType.PING:
                pass
            else:
                raise RuntimeError("Unknown message type for {}".format(
                    typ.value))

        def on_open(self, ws: websocket.WebSocketApp):
            """

            :param ws: websocket.WebSocketApp:

            """
            if self.__closed:
                self.__dealer_client.logger.fatal(
                    "I wonder what happened here... Terminating. [closed: {}]".
                    format(self.__closed))
            self.__dealer_client.logger.debug(
                "Dealer connected! [url: {}]".format(self.__url))

            def anonymous():
                """ """
                self.send_ping()
                self.__received_pong = False

                def anonymous2():
                    """ """
                    if self.__last_scheduled_ping is None:
                        return
                    if not self.__received_pong:
                        self.__dealer_client.logger.warning(
                            "Did not receive ping in 3 seconds. Reconnecting..."
                        )
                        self.close()
                        return
                    self.__received_pong = False

                self.__scheduler.enter(3, 1, anonymous2)
                self.__last_scheduled_ping = self.__scheduler.enter(
                    30, 1, anonymous)

            self.__last_scheduled_ping = self.__scheduler.enter(
                30, 1, anonymous)

        def send_ping(self):
            """ """
            self.__ws.send('{"type":"ping"}')

        def send_reply(self, key: str, result: DealerClient.RequestResult):
            """

            :param key: str:
            :param result: DealerClient.RequestResult:

            """
            success = ("true" if result == DealerClient.RequestResult.SUCCESS
                       else "false")
            self.__ws.send(
                '{"type":"reply","key":"%s","payload":{"success":%s}' %
                (key, success))

    class RequestResult(enum.Enum):
        """ """
        UNKNOWN_SEND_COMMAND_RESULT = 0
        SUCCESS = 1
        DEVICE_NOT_FOUND = 2
        CONTEXT_PLAYER_ERROR = 3
        DEVICE_DISAPPEARED = 4
        UPSTREAM_ERROR = 5
        DEVICE_DOES_NOT_SUPPORT_COMMAND = 6
        RATE_LIMITED = 7


class EventService(Closeable):
    """ """
    logger = logging.getLogger("Librespot:EventService")
    __session: Session
    __worker = concurrent.futures.ThreadPoolExecutor()

    def __init__(self, session: Session):
        self.__session = session

    def __worker_callback(self, event_builder: EventBuilder):
        try:
            body = event_builder.to_array()
            resp = self.__session.mercury().send_sync(
                RawMercuryRequest.Builder().set_uri(
                    "hm://event-service/v1/events").set_method("POST").
                add_user_field("Accept-Language", "en").add_user_field(
                    "X-ClientTimeStamp",
                    int(time.time() * 1000)).add_payload_part(body).build())
            self.logger.debug("Event sent. body: {}, result: {}".format(
                body, resp.status_code))
        except IOError as ex:
            self.logger.error("Failed sending event: {} {}".format(
                event_builder, ex))

    def send_event(self, event_or_builder: typing.Union[GenericEvent,
                                                        EventBuilder]):
        """

        :param event_or_builder: typing.Union[GenericEvent:
        :param EventBuilder]:

        """
        if type(event_or_builder) is EventService.GenericEvent:
            builder = event_or_builder.build()
        elif type(event_or_builder) is EventService.EventBuilder:
            builder = event_or_builder
        else:
            raise TypeError()
        self.__worker.submit(lambda: self.__worker_callback(builder))

    def language(self, lang: str):
        """

        :param lang: str:

        """
        event = EventService.EventBuilder(EventService.Type.LANGUAGE)
        event.append(s=lang)

    def close(self):
        """ """
        self.__worker.shutdown()

    class Type(enum.Enum):
        """ """
        LANGUAGE = ("812", 1)
        FETCHED_FILE_ID = ("274", 3)
        NEW_SESSION_ID = ("557", 3)
        NEW_PLAYBACK_ID = ("558", 1)
        TRACK_PLAYED = ("372", 1)
        TRACK_TRANSITION = ("12", 37)
        CDN_REQUEST = ("10", 20)

        eventId: str
        unknown: str

        def __init__(self, event_id: str, unknown: str):
            self.eventId = event_id
            self.unknown = unknown

    class GenericEvent:
        """ """

        def build(self) -> EventService.EventBuilder:
            """ """
            raise NotImplementedError

    class EventBuilder:
        """ """
        body: io.BytesIO

        def __init__(self, event_type: EventService.Type):
            self.body = io.BytesIO()
            self.append_no_delimiter(event_type.value[0])
            self.append(event_type.value[1])

        def append_no_delimiter(self, s: str = None) -> None:
            """

            :param s: str:  (Default value = None)

            """
            if s is None:
                s = ""
            self.body.write(s.encode())

        def append(self,
                   c: int = None,
                   s: str = None) -> EventService.EventBuilder:
            """

            :param c: int:  (Default value = None)
            :param s: str:  (Default value = None)

            """
            if c is None and s is None or c is not None and s is not None:
                raise TypeError()
            if c is not None:
                self.body.write(b"\x09")
                self.body.write(bytes([c]))
                return self
            if s is not None:
                self.body.write(b"\x09")
                self.append_no_delimiter(s)
                return self

        def to_array(self) -> bytes:
            """ """
            pos = self.body.tell()
            self.body.seek(0)
            data = self.body.read()
            self.body.seek(pos)
            return data


class MessageType(enum.Enum):
    """ """
    MESSAGE = "message"
    PING = "ping"
    PONG = "pong"
    REQUEST = "request"

    @staticmethod
    def parse(_typ: str):
        """

        :param _typ: str:

        """
        if _typ == MessageType.MESSAGE.value:
            return MessageType.MESSAGE
        if _typ == MessageType.PING.value:
            return MessageType.PING
        if _typ == MessageType.PONG.value:
            return MessageType.PONG
        if _typ == MessageType.REQUEST.value:
            return MessageType.REQUEST
        raise TypeError("Unknown MessageType: {}".format(_typ))


class Session(Closeable, MessageListener, SubListener):
    """ """
    cipher_pair: typing.Union[CipherPair, None]
    country_code: str = "EN"
    connection: typing.Union[ConnectionHolder, None]
    logger = logging.getLogger("Librespot:Session")
    scheduled_reconnect: typing.Union[sched.Event, None] = None
    scheduler = sched.scheduler(time.time)
    __api: ApiClient
    __ap_welcome: Authentication.APWelcome
    __audio_key_manager: typing.Union[AudioKeyManager, None] = None
    __auth_lock = threading.Condition()
    __auth_lock_bool = False
    __cache_manager: typing.Union[CacheManager, None]
    __cdn_manager: typing.Union[CdnManager, None]
    __channel_manager: typing.Union[ChannelManager, None] = None
    __client: typing.Union[requests.Session, None]
    __closed = False
    __closing = False
    __content_feeder: typing.Union[PlayableContentFeeder, None]
    __dealer_client: typing.Union[DealerClient, None] = None
    __event_service: typing.Union[EventService, None] = None
    __keys: DiffieHellman
    __mercury_client: MercuryClient
    __receiver: typing.Union[Receiver, None] = None
    __search: typing.Union[SearchManager, None]
    __server_key = (b"\xac\xe0F\x0b\xff\xc20\xaf\xf4k\xfe\xc3\xbf\xbf\x86="
                    b"\xa1\x91\xc6\xcc3l\x93\xa1O\xb3\xb0\x16\x12\xac\xacj"
                    b"\xf1\x80\xe7\xf6\x14\xd9B\x9d\xbe.4fC\xe3b\xd22z\x1a"
                    b"\r\x92;\xae\xdd\x14\x02\xb1\x81U\x05a\x04\xd5,\x96\xa4"
                    b"L\x1e\xcc\x02J\xd4\xb2\x0c\x00\x1f\x17\xed\xc2/\xc45"
                    b"!\xc8\xf0\xcb\xae\xd2\xad\xd7+\x0f\x9d\xb3\xc52\x1a*"
                    b"\xfeY\xf3Z\r\xach\xf1\xfab\x1e\xfb,\x8d\x0c\xb79-\x92"
                    b"G\xe3\xd75\x1am\xbd$\xc2\xae%[\x88\xff\xabs)\x8a\x0b"
                    b"\xcc\xcd\x0cXg1\x89\xe8\xbd4\x80xJ_\xc9k\x89\x9d\x95k"
                    b"\xfc\x86\xd7O3\xa6x\x17\x96\xc9\xc3-\r2\xa5\xab\xcd\x05'"
                    b"\xe2\xf7\x10\xa3\x96\x13\xc4/\x99\xc0'\xbf\xed\x04\x9c"
                    b"<'X\x04\xb6\xb2\x19\xf9\xc1/\x02\xe9Hc\xec\xa1\xb6B\xa0"
                    b"\x9dH%\xf8\xb3\x9d\xd0\xe8j\xf9HM\xa1\xc2\xba\x860B\xea"
                    b"\x9d\xb3\x08l\x19\x0eH\xb3\x9df\xeb\x00\x06\xa2Z\xee\xa1"
                    b"\x1b\x13\x87<\xd7\x19\xe6U\xbd")
    __stored_str: str = ""
    __token_provider: typing.Union[TokenProvider, None]
    __user_attributes = {}

    def __init__(self, inner: Inner, address: str) -> None:
        self.__client = Session.create_client(inner.conf)
        self.connection = Session.ConnectionHolder.create(address, None)
        self.__inner = inner
        self.__keys = DiffieHellman()
        self.logger.info("Created new session! device_id: {}, ap: {}".format(
            inner.device_id, address))

    def api(self) -> ApiClient:
        """ """
        self.__wait_auth_lock()
        if self.__api is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__api

    def ap_welcome(self):
        """ """
        self.__wait_auth_lock()
        if self.__ap_welcome is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__ap_welcome

    def audio_key(self) -> AudioKeyManager:
        """ """
        self.__wait_auth_lock()
        if self.__audio_key_manager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__audio_key_manager

    def authenticate(self,
                     credential: Authentication.LoginCredentials) -> None:
        """Log in to Spotify

        :param credential: Spotify account login information
        :param credential: Authentication.LoginCredentials:

        """
        self.__authenticate_partial(credential, False)
        with self.__auth_lock:
            self.__mercury_client = MercuryClient(self)
            self.__token_provider = TokenProvider(self)
            self.__audio_key_manager = AudioKeyManager(self)
            self.__channel_manager = ChannelManager(self)
            self.__api = ApiClient(self)
            self.__cdn_manager = CdnManager(self)
            self.__content_feeder = PlayableContentFeeder(self)
            self.__cache_manager = CacheManager(self)
            self.__dealer_client = DealerClient(self)
            self.__search = SearchManager(self)
            self.__event_service = EventService(self)
            self.__auth_lock_bool = False
            self.__auth_lock.notify_all()
        self.dealer().connect()
        self.logger.info("Authenticated as {}!".format(
            self.__ap_welcome.canonical_username))
        self.mercury().interested_in("spotify:user:attributes:update", self)
        self.dealer().add_message_listener(
            self, ["hm://connect-state/v1/connect/logout"])

    def cache(self) -> CacheManager:
        """ """
        self.__wait_auth_lock()
        if self.__cache_manager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__cache_manager

    def cdn(self) -> CdnManager:
        """ """
        self.__wait_auth_lock()
        if self.__cdn_manager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__cdn_manager

    def channel(self) -> ChannelManager:
        """ """
        self.__wait_auth_lock()
        if self.__channel_manager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__channel_manager

    def client(self) -> requests.Session:
        """ """
        return self.__client

    def close(self) -> None:
        """Close instance"""
        self.logger.info("Closing session. device_id: {}".format(
            self.__inner.device_id))
        self.__closing = True
        if self.__dealer_client is not None:
            self.__dealer_client.close()
            self.__dealer_client = None
        if self.__audio_key_manager is not None:
            self.__audio_key_manager = None
        if self.__channel_manager is not None:
            self.__channel_manager.close()
            self.__channel_manager = None
        if self.__event_service is not None:
            self.__event_service.close()
            self.__event_service = None
        if self.__receiver is not None:
            self.__receiver.stop()
            self.__receiver = None
        if self.__client is not None:
            self.__client.close()
            self.__client = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        with self.__auth_lock:
            self.__ap_welcome = None
            self.cipher_pair = None
            self.__closed = True
        self.logger.info("Closed session. device_id: {}".format(
            self.__inner.device_id))

    def connect(self) -> None:
        """Connect to the Spotify Server"""
        acc = Session.Accumulator()
        # Send ClientHello
        nonce = Random.get_random_bytes(0x10)
        client_hello_proto = Keyexchange.ClientHello(
            build_info=Version.standard_build_info(),
            client_nonce=nonce,
            cryptosuites_supported=[
                Keyexchange.Cryptosuite.CRYPTO_SUITE_SHANNON
            ],
            login_crypto_hello=Keyexchange.LoginCryptoHelloUnion(
                diffie_hellman=Keyexchange.LoginCryptoDiffieHellmanHello(
                    gc=self.__keys.public_key_bytes(), server_keys_known=1), ),
            padding=b"\x1e",
        )
        client_hello_bytes = client_hello_proto.SerializeToString()
        self.connection.write(b"\x00\x04")
        self.connection.write_int(2 + 4 + len(client_hello_bytes))
        self.connection.write(client_hello_bytes)
        self.connection.flush()
        acc.write(b"\x00\x04")
        acc.write_int(2 + 4 + len(client_hello_bytes))
        acc.write(client_hello_bytes)
        # Read APResponseMessage
        ap_response_message_length = self.connection.read_int()
        acc.write_int(ap_response_message_length)
        ap_response_message_bytes = self.connection.read(
            ap_response_message_length - 4)
        acc.write(ap_response_message_bytes)
        ap_response_message_proto = Keyexchange.APResponseMessage()
        ap_response_message_proto.ParseFromString(ap_response_message_bytes)
        shared_key = util.int_to_bytes(
            self.__keys.compute_shared_key(
                ap_response_message_proto.challenge.login_crypto_challenge.
                diffie_hellman.gs))
        # Check gs_signature
        rsa = RSA.construct((int.from_bytes(self.__server_key, "big"), 65537))
        pkcs1_v1_5 = PKCS1_v1_5.new(rsa)
        sha1 = SHA1.new()
        sha1.update(ap_response_message_proto.challenge.login_crypto_challenge.
                    diffie_hellman.gs)
        if not pkcs1_v1_5.verify(
                sha1,
                ap_response_message_proto.challenge.login_crypto_challenge.
                diffie_hellman.gs_signature,
        ):
            raise RuntimeError("Failed signature check!")
        # Solve challenge
        buffer = io.BytesIO()
        for i in range(1, 6):
            mac = HMAC.new(shared_key, digestmod=SHA1)
            mac.update(acc.read())
            mac.update(bytes([i]))
            buffer.write(mac.digest())
        buffer.seek(0)
        mac = HMAC.new(buffer.read(20), digestmod=SHA1)
        mac.update(acc.read())
        challenge = mac.digest()
        client_response_plaintext_proto = Keyexchange.ClientResponsePlaintext(
            crypto_response=Keyexchange.CryptoResponseUnion(),
            login_crypto_response=Keyexchange.LoginCryptoResponseUnion(
                diffie_hellman=Keyexchange.LoginCryptoDiffieHellmanResponse(
                    hmac=challenge)),
            pow_response=Keyexchange.PoWResponseUnion(),
        )
        client_response_plaintext_bytes = (
            client_response_plaintext_proto.SerializeToString())
        self.connection.write_int(4 + len(client_response_plaintext_bytes))
        self.connection.write(client_response_plaintext_bytes)
        self.connection.flush()
        try:
            self.connection.set_timeout(1)
            scrap = self.connection.read(4)
            if len(scrap) == 4:
                payload = self.connection.read(
                    struct.unpack(">i", scrap)[0] - 4)
                failed = Keyexchange.APResponseMessage()
                failed.ParseFromString(payload)
                raise RuntimeError(failed)
        except socket.timeout:
            pass
        finally:
            self.connection.set_timeout(0)
        buffer.seek(20)
        with self.__auth_lock:
            self.cipher_pair = CipherPair(buffer.read(32), buffer.read(32))
            self.__auth_lock_bool = True
        self.logger.info("Connection successfully!")

    def content_feeder(self) -> PlayableContentFeeder:
        """ """
        self.__wait_auth_lock()
        if self.__content_feeder is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__content_feeder

    @staticmethod
    def create_client(conf: Configuration) -> requests.Session:
        """

        :param conf: Configuration:

        """
        client = requests.Session()
        return client

    def dealer(self) -> DealerClient:
        """ """
        self.__wait_auth_lock()
        if self.__dealer_client is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__dealer_client

    def device_id(self) -> str:
        """ """
        return self.__inner.device_id

    def device_name(self) -> str:
        """ """
        return self.__inner.device_name

    def device_type(self) -> Connect.DeviceType:
        """ """
        return self.__inner.device_type

    def event(self, resp: MercuryClient.Response) -> None:
        """

        :param resp: MercuryClient.Response:

        """
        if resp.uri == "spotify:user:attributes:update":
            attributes_update = UserAttributesUpdate()
            attributes_update.ParseFromString(resp.payload)
            for pair in attributes_update.pairs_list:
                self.__user_attributes[pair.key] = pair.value
                self.logger.info("Updated user attribute: {} -> {}".format(
                    pair.key, pair.value))

    def get_user_attribute(self, key: str, fallback: str = None) -> str:
        """

        :param key: str:
        :param fallback: str:  (Default value = None)

        """
        return (self.__user_attributes.get(key)
                if self.__user_attributes.get(key) is not None else fallback)

    def is_valid(self) -> bool:
        """ """
        if self.__closed:
            return False
        self.__wait_auth_lock()
        return self.__ap_welcome is not None and self.connection is not None

    def mercury(self) -> MercuryClient:
        """ """
        self.__wait_auth_lock()
        if self.__mercury_client is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__mercury_client

    def on_message(self, uri: str, headers: typing.Dict[str, str],
                   payload: bytes):
        """

        :param uri: str:
        :param headers: typing.Dict[str:
        :param str]:
        :param payload: bytes:

        """
        if uri == "hm://connect-state/v1/connect/logout":
            self.close()

    def parse_product_info(self, data) -> None:
        """Parse product information

        :param data: Raw product information

        """
        products = defusedxml.ElementTree.fromstring(data)
        if products is None:
            return
        product = products[0]
        if product is None:
            return
        for i in range(len(product)):
            self.__user_attributes[product[i].tag] = product[i].text
        self.logger.debug("Parsed product info: {}".format(
            self.__user_attributes))

    def preferred_locale(self) -> str:
        """ """
        return self.__inner.preferred_locale

    def reconnect(self) -> None:
        """Reconnect to the Spotify Server"""
        if self.connection is not None:
            self.connection.close()
            self.__receiver.stop()
        self.connection = Session.ConnectionHolder.create(
            ApResolver.get_random_accesspoint(), self.__inner.conf)
        self.connect()
        self.__authenticate_partial(
            Authentication.LoginCredentials(
                typ=self.__ap_welcome.reusable_auth_credentials_type,
                username=self.__ap_welcome.canonical_username,
                auth_data=self.__ap_welcome.reusable_auth_credentials,
            ),
            True,
        )
        self.logger.info("Re-authenticated as {}!".format(
            self.__ap_welcome.canonical_username))

    def reconnecting(self) -> bool:
        """ """
        return not self.__closing and not self.__closed and self.connection is None

    def search(self) -> SearchManager:
        """ """
        self.__wait_auth_lock()
        if self.__search is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__search

    def send(self, cmd: bytes, payload: bytes):
        """Send data to socket using send_unchecked

        :param cmd: Command
        :param payload: Payload
        :param cmd: bytes:
        :param payload: bytes:

        """
        if self.__closing and self.connection is None:
            self.logger.debug("Connection was broken while closing.")
            return
        if self.__closed:
            raise RuntimeError("Session is closed!")
        with self.__auth_lock:
            if self.cipher_pair is None or self.__auth_lock_bool:
                self.__auth_lock.wait()
            self.__send_unchecked(cmd, payload)

    def tokens(self) -> TokenProvider:
        """ """
        self.__wait_auth_lock()
        if self.__token_provider is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__token_provider

    def username(self):
        """ """
        return self.__ap_welcome.canonical_username

    def stored(self):
        """ """
        return self.__stored_str

    def __authenticate_partial(self,
                               credential: Authentication.LoginCredentials,
                               remove_lock: bool) -> None:
        """
        Login to Spotify
        Args:
            credential: Spotify account login information
        """
        if self.cipher_pair is None:
            raise RuntimeError("Connection not established!")
        client_response_encrypted_proto = Authentication.ClientResponseEncrypted(
            login_credentials=credential,
            system_info=Authentication.SystemInfo(
                os=Authentication.Os.OS_UNKNOWN,
                cpu_family=Authentication.CpuFamily.CPU_UNKNOWN,
                system_information_string=Version.system_info_string(),
                device_id=self.__inner.device_id,
            ),
            version_string=Version.version_string(),
        )
        self.__send_unchecked(
            Packet.Type.login,
            client_response_encrypted_proto.SerializeToString())
        packet = self.cipher_pair.receive_encoded(self.connection)
        if packet.is_cmd(Packet.Type.ap_welcome):
            self.__ap_welcome = Authentication.APWelcome()
            self.__ap_welcome.ParseFromString(packet.payload)
            self.__receiver = Session.Receiver(self)
            bytes0x0f = Random.get_random_bytes(0x14)
            self.__send_unchecked(Packet.Type.unknown_0x0f, bytes0x0f)
            preferred_locale = io.BytesIO()
            preferred_locale.write(b"\x00\x00\x10\x00\x02preferred-locale" +
                                   self.__inner.preferred_locale.encode())
            preferred_locale.seek(0)
            self.__send_unchecked(Packet.Type.preferred_locale,
                                  preferred_locale.read())
            if remove_lock:
                with self.__auth_lock:
                    self.__auth_lock_bool = False
                    self.__auth_lock.notify_all()
            if self.__inner.conf.store_credentials:
                reusable = self.__ap_welcome.reusable_auth_credentials
                reusable_type = Authentication.AuthenticationType.Name(
                    self.__ap_welcome.reusable_auth_credentials_type)
                if self.__inner.conf.stored_credentials_file is None:
                    raise TypeError(
                        "The file path to be saved is not specified")
                self.__stored_str = base64.b64encode(
                    json.dumps({
                        "username":
                        self.__ap_welcome.canonical_username,
                        "credentials":
                        base64.b64encode(reusable).decode(),
                        "type":
                        reusable_type,
                    }).encode()).decode()
                with open(self.__inner.conf.stored_credentials_file, "w") as f:
                    json.dump(
                        {
                            "username": self.__ap_welcome.canonical_username,
                            "credentials": base64.b64encode(reusable).decode(),
                            "type": reusable_type,
                        },
                        f,
                    )

        elif packet.is_cmd(Packet.Type.auth_failure):
            ap_login_failed = Keyexchange.APLoginFailed()
            ap_login_failed.ParseFromString(packet.payload)
            self.close()
            raise Session.SpotifyAuthenticationException(ap_login_failed)
        else:
            raise RuntimeError("Unknown CMD 0x" + packet.cmd.hex())

    def __send_unchecked(self, cmd: bytes, payload: bytes) -> None:
        self.cipher_pair.send_encoded(self.connection, cmd, payload)

    def __wait_auth_lock(self) -> None:
        if self.__closing and self.connection is None:
            self.logger.debug("Connection was broken while closing.")
            return
        if self.__closed:
            raise RuntimeError("Session is closed!")
        with self.__auth_lock:
            if self.cipher_pair is None or self.__auth_lock_bool:
                self.__auth_lock.wait()

    class AbsBuilder:
        """ """
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
            """

            :param locale: str:

            """
            if len(locale) != 2:
                raise TypeError("Invalid locale: {}".format(locale))
            self.preferred_locale = locale
            return self

        def set_device_name(self, device_name: str) -> Session.AbsBuilder:
            """

            :param device_name: str:

            """
            self.device_name = device_name
            return self

        def set_device_id(self, device_id: str) -> Session.AbsBuilder:
            """

            :param device_id: str:

            """
            if self.device_id is not None and len(device_id) != 40:
                raise TypeError("Device ID must be 40 chars long.")
            self.device_id = device_id
            return self

        def set_device_type(
                self, device_type: Connect.DeviceType) -> Session.AbsBuilder:
            """

            :param device_type: Connect.DeviceType:

            """
            self.device_type = device_type
            return self

    class Accumulator:
        """ """
        __buffer: io.BytesIO

        def __init__(self):
            self.__buffer = io.BytesIO()

        def read(self) -> bytes:
            """Read all buffer


            :returns: All buffer

            """
            pos = self.__buffer.tell()
            self.__buffer.seek(0)
            data = self.__buffer.read()
            self.__buffer.seek(pos)
            return data

        def write(self, data: bytes) -> None:
            """Write data to buffer

            :param data: Bytes to be written
            :param data: bytes:

            """
            self.__buffer.write(data)

        def write_int(self, data: int) -> None:
            """Write data to buffer

            :param data: Integer to be written
            :param data: int:

            """
            self.write(struct.pack(">i", data))

        def write_short(self, data: int) -> None:
            """Write data to buffer

            :param data: Short integer to be written
            :param data: int:

            """
            self.write(struct.pack(">h", data))

    class Builder(AbsBuilder):
        """ """
        login_credentials: Authentication.LoginCredentials = None

        def blob(self, username: str, blob: bytes) -> Session.Builder:
            """

            :param username: str:
            :param blob: bytes:

            """
            if self.device_id is None:
                raise TypeError("You must specify the device ID first.")
            self.login_credentials = self.decrypt_blob(self.device_id,
                                                       username, blob)
            return self

        def decrypt_blob(
                self, device_id: str, username: str,
                encrypted_blob: bytes) -> Authentication.LoginCredentials:
            """

            :param device_id: str:
            :param username: str:
            :param encrypted_blob: bytes:

            """
            encrypted_blob = base64.b64decode(encrypted_blob)
            sha1 = SHA1.new()
            sha1.update(device_id.encode())
            secret = sha1.digest()
            base_key = PBKDF2(secret,
                              username.encode(),
                              20,
                              0x100,
                              hmac_hash_module=SHA1)
            sha1 = SHA1.new()
            sha1.update(base_key)
            key = sha1.digest() + b"\x00\x00\x00\x14"
            aes = AES.new(key, AES.MODE_ECB)
            decrypted_blob = bytearray(aes.decrypt(encrypted_blob))
            l = len(decrypted_blob)
            for i in range(0, l - 0x10):
                decrypted_blob[l - i - 1] ^= decrypted_blob[l - i - 0x11]
            blob = io.BytesIO(decrypted_blob)
            blob.read(1)
            le = self.read_blob_int(blob)
            blob.read(le)
            blob.read(1)
            type_int = self.read_blob_int(blob)
            type_ = Authentication.AuthenticationType.Name(type_int)
            if type_ is None:
                raise IOError(
                    TypeError(
                        "Unknown AuthenticationType: {}".format(type_int)))
            blob.read(1)
            l = self.read_blob_int(blob)
            auth_data = blob.read(l)
            return Authentication.LoginCredentials(
                auth_data=auth_data,
                typ=type_,
                username=username,
            )

        def read_blob_int(self, buffer: io.BytesIO) -> int:
            """

            :param buffer: io.BytesIO:

            """
            lo = buffer.read(1)
            if (int(lo[0]) & 0x80) == 0:
                return int(lo[0])
            hi = buffer.read(1)
            return int(lo[0]) & 0x7F | int(hi[0]) << 7

        def stored(self, stored_credentials_str: str):
            """Create credential from stored string

            :param stored_credentials_str: str:
            :returns: Builder

            """
            try:
                obj = json.loads(base64.b64decode(stored_credentials_str))
            except binascii.Error:
                pass
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

        def stored_file(self,
                        stored_credentials: str = None) -> Session.Builder:
            """Create credential from stored file

            :param stored_credentials: str:  (Default value = None)
            :returns: Builder

            """
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
            """Create credential from username and password

            :param username: Spotify's account username
            :param username: str:
            :param password: str:
            :returns: Builder

            """
            self.login_credentials = Authentication.LoginCredentials(
                username=username,
                typ=Authentication.AuthenticationType.AUTHENTICATION_USER_PASS,
                auth_data=password.encode(),
            )
            return self

        def create(self) -> Session:
            """Create the Session instance


            :returns: Session instance

            """
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
            session.connect()
            session.authenticate(self.login_credentials)
            return session

    class Configuration:
        """ """
        # Proxy
        # proxyEnabled: bool
        # proxyType: Proxy.Type
        # proxyAddress: str
        # proxyPort: int
        # proxyAuth: bool
        # proxyUsername: str
        # proxyPassword: str

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
            # proxy_enabled: bool,
            # proxy_type: Proxy.Type,
            # proxy_address: str,
            # proxy_port: int,
            # proxy_auth: bool,
            # proxy_username: str,
            # proxy_password: str,
            cache_enabled: bool,
            cache_dir: str,
            do_cache_clean_up: bool,
            store_credentials: bool,
            stored_credentials_file: str,
            retry_on_chunk_error: bool,
        ):
            # self.proxyEnabled = proxy_enabled
            # self.proxyType = proxy_type
            # self.proxyAddress = proxy_address
            # self.proxyPort = proxy_port
            # self.proxyAuth = proxy_auth
            # self.proxyUsername = proxy_username
            # self.proxyPassword = proxy_password
            self.cache_enabled = cache_enabled
            self.cache_dir = cache_dir
            self.do_cache_clean_up = do_cache_clean_up
            self.store_credentials = store_credentials
            self.stored_credentials_file = stored_credentials_file
            self.retry_on_chunk_error = retry_on_chunk_error

        class Builder:
            """ """
            # Proxy
            # proxyEnabled: bool = False
            # proxyType: Proxy.Type = Proxy.Type.DIRECT
            # proxyAddress: str = None
            # proxyPort: int = None
            # proxyAuth: bool = None
            # proxyUsername: str = None
            # proxyPassword: str = None

            # Cache
            cache_enabled: bool = True
            cache_dir: str = os.path.join(os.getcwd(), "cache")
            do_cache_clean_up: bool = True

            # Stored credentials
            store_credentials: bool = True
            stored_credentials_file: str = os.path.join(
                os.getcwd(), "credentials.json")

            # Fetching
            retry_on_chunk_error: bool = True

            # def set_proxy_enabled(
            #         self,
            #         proxy_enabled: bool) -> Session.Configuration.Builder:
            #     self.proxyEnabled = proxy_enabled
            #     return self

            # def set_proxy_type(
            #         self,
            #         proxy_type: Proxy.Type) -> Session.Configuration.Builder:
            #     self.proxyType = proxy_type
            #     return self

            # def set_proxy_address(
            #         self, proxy_address: str) -> Session.Configuration.Builder:
            #     self.proxyAddress = proxy_address
            #     return self

            # def set_proxy_auth(
            #         self, proxy_auth: bool) -> Session.Configuration.Builder:
            #     self.proxyAuth = proxy_auth
            #     return self

            # def set_proxy_username(
            #         self,
            #         proxy_username: str) -> Session.Configuration.Builder:
            #     self.proxyUsername = proxy_username
            #     return self

            # def set_proxy_password(
            #         self,
            #         proxy_password: str) -> Session.Configuration.Builder:
            #     self.proxyPassword = proxy_password
            #     return self

            def set_cache_enabled(
                    self,
                    cache_enabled: bool) -> Session.Configuration.Builder:
                """Set cache_enabled

                :param cache_enabled: bool:
                :returns: Builder

                """
                self.cache_enabled = cache_enabled
                return self

            def set_cache_dir(self,
                              cache_dir: str) -> Session.Configuration.Builder:
                """Set cache_dir

                :param cache_dir: str:
                :returns: Builder

                """
                self.cache_dir = cache_dir
                return self

            def set_do_cache_clean_up(
                    self,
                    do_cache_clean_up: bool) -> Session.Configuration.Builder:
                """Set do_cache_clean_up

                :param do_cache_clean_up: bool:
                :returns: Builder

                """
                self.do_cache_clean_up = do_cache_clean_up
                return self

            def set_store_credentials(
                    self,
                    store_credentials: bool) -> Session.Configuration.Builder:
                """Set store_credentials

                :param store_credentials: bool:
                :returns: Builder

                """
                self.store_credentials = store_credentials
                return self

            def set_stored_credential_file(
                    self, stored_credential_file: str
            ) -> Session.Configuration.Builder:
                """Set stored_credential_file

                :param stored_credential_file: str:
                :returns: Builder

                """
                self.stored_credentials_file = stored_credential_file
                return self

            def set_retry_on_chunk_error(
                    self, retry_on_chunk_error: bool
            ) -> Session.Configuration.Builder:
                """Set retry_on_chunk_error

                :param retry_on_chunk_error: bool:
                :returns: Builder

                """
                self.retry_on_chunk_error = retry_on_chunk_error
                return self

            def build(self) -> Session.Configuration:
                """Build Configuration instance


                :returns: Session.Configuration

                """
                return Session.Configuration(
                    # self.proxyEnabled,
                    # self.proxyType,
                    # self.proxyAddress,
                    # self.proxyPort,
                    # self.proxyAuth,
                    # self.proxyUsername,
                    # self.proxyPassword,
                    self.cache_enabled,
                    self.cache_dir,
                    self.do_cache_clean_up,
                    self.store_credentials,
                    self.stored_credentials_file,
                    self.retry_on_chunk_error,
                )

    class ConnectionHolder:
        """ """
        __buffer: io.BytesIO
        __socket: socket.socket

        def __init__(self, sock: socket.socket):
            self.__buffer = io.BytesIO()
            self.__socket = sock

        @staticmethod
        def create(address: str, conf) -> Session.ConnectionHolder:
            """Create the ConnectionHolder instance

            :param address: Address to connect
            :param address: str:
            :param conf:
            :returns: ConnectionHolder instance

            """
            ap_address = address.split(":")[0]
            ap_port = int(address.split(":")[1])
            sock = socket.socket()
            sock.connect((ap_address, ap_port))
            return Session.ConnectionHolder(sock)

        def close(self) -> None:
            """Close the connection"""
            self.__socket.close()

        def flush(self) -> None:
            """Flush data to socket"""
            try:
                self.__buffer.seek(0)
                self.__socket.send(self.__buffer.read())
                self.__buffer = io.BytesIO()
            except BrokenPipeError:
                pass

        def read(self, length: int) -> bytes:
            """Read data from socket

            :param length: int:
            :returns: Bytes data from socket

            """
            return self.__socket.recv(length)

        def read_int(self) -> int:
            """Read integer from socket


            :returns: integer from socket

            """
            return struct.unpack(">i", self.read(4))[0]

        def read_short(self) -> int:
            """Read short integer from socket


            :returns: short integer from socket

            """
            return struct.unpack(">h", self.read(2))[0]

        def set_timeout(self, seconds: float) -> None:
            """Set socket's timeout

            :param seconds: Number of seconds until timeout
            :param seconds: float:

            """
            self.__socket.settimeout(None if seconds == 0 else seconds)

        def write(self, data: bytes) -> None:
            """Write data to buffer

            :param data: Bytes to be written
            :param data: bytes:

            """
            self.__buffer.write(data)

        def write_int(self, data: int) -> None:
            """Write data to buffer

            :param data: Integer to be written
            :param data: int:

            """
            self.write(struct.pack(">i", data))

        def write_short(self, data: int) -> None:
            """Write data to buffer

            :param data: Short integer to be written
            :param data: int:

            """
            self.write(struct.pack(">h", data))

    class Inner:
        """ """
        device_type: Connect.DeviceType = None
        device_name: str
        device_id: str
        conf = None
        preferred_locale: str

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
                              util.random_hex_string(40))

    class Receiver:
        """ """
        __session: Session
        __thread: threading.Thread
        __running: bool = True

        def __init__(self, session):
            self.__session = session
            self.__thread = threading.Thread(target=self.run)
            self.__thread.daemon = True
            self.__thread.name = "session-packet-receiver"
            self.__thread.start()

        def stop(self) -> None:
            """ """
            self.__running = False

        def run(self) -> None:
            """Receive Packet thread function"""
            self.__session.logger.info("Session.Receiver started")
            while self.__running:
                packet: Packet
                cmd: bytes
                try:
                    packet = self.__session.cipher_pair.receive_encoded(
                        self.__session.connection)
                    cmd = Packet.Type.parse(packet.cmd)
                    if cmd is None:
                        self.__session.logger.info(
                            "Skipping unknown command cmd: 0x{}, payload: {}".
                            format(util.bytes_to_hex(packet.cmd),
                                   packet.payload))
                        continue
                except (RuntimeError, ConnectionResetError) as ex:
                    if self.__running:
                        self.__session.logger.fatal(
                            "Failed reading packet! {}".format(ex))
                        self.__session.reconnect()
                    break
                if not self.__running:
                    break
                if cmd == Packet.Type.ping:
                    if self.__session.scheduled_reconnect is not None:
                        self.__session.scheduler.cancel(
                            self.__session.scheduled_reconnect)

                    def anonymous():
                        """ """
                        self.__session.logger.warning(
                            "Socket timed out. Reconnecting...")
                        self.__session.reconnect()

                    self.__session.scheduled_reconnect = self.__session.scheduler.enter(
                        2 * 60 + 5, 1, anonymous)
                    self.__session.send(Packet.Type.pong, packet.payload)
                elif cmd == Packet.Type.pong_ack:
                    continue
                elif cmd == Packet.Type.country_code:
                    self.__session.__country_code = packet.payload.decode()
                    self.__session.logger.info(
                        "Received country_code: {}".format(
                            self.__session.__country_code))
                elif cmd == Packet.Type.license_version:
                    license_version = io.BytesIO(packet.payload)
                    license_id = struct.unpack(">h",
                                               license_version.read(2))[0]
                    if license_id != 0:
                        buffer = license_version.read()
                        self.__session.logger.info(
                            "Received license_version: {}, {}".format(
                                license_id, buffer.decode()))
                    else:
                        self.__session.logger.info(
                            "Received license_version: {}".format(license_id))
                elif cmd == Packet.Type.unknown_0x10:
                    self.__session.logger.debug("Received 0x10: {}".format(
                        util.bytes_to_hex(packet.payload)))
                elif cmd in [
                        Packet.Type.mercury_sub,
                        Packet.Type.mercury_unsub,
                        Packet.Type.mercury_event,
                        Packet.Type.mercury_req,
                ]:
                    self.__session.mercury().dispatch(packet)
                elif cmd in [Packet.Type.aes_key, Packet.Type.aes_key_error]:
                    self.__session.audio_key().dispatch(packet)
                elif cmd in [
                        Packet.Type.channel_error, Packet.Type.stream_chunk_res
                ]:
                    self.__session.channel().dispatch(packet)
                elif cmd == Packet.Type.product_info:
                    self.__session.parse_product_info(packet.payload)
                else:
                    self.__session.logger.info("Skipping {}".format(
                        util.bytes_to_hex(cmd)))

    class SpotifyAuthenticationException(Exception):
        """ """

        def __init__(self, login_failed: Keyexchange.APLoginFailed):
            super().__init__(
                Keyexchange.ErrorCode.Name(login_failed.error_code))


class SearchManager:
    """ """
    base_url = "hm://searchview/km/v4/search/"
    __session: Session

    def __init__(self, session: Session):
        self.__session = session

    def request(self, request: SearchRequest) -> typing.Any:
        """

        :param request: SearchRequest:

        """
        if request.get_username() == "":
            request.set_username(self.__session.username())
        if request.get_country() == "":
            request.set_country(self.__session.country_code)
        if request.get_locale() == "":
            request.set_locale(self.__session.preferred_locale())
        response = self.__session.mercury().send_sync(
            RawMercuryRequest.new_builder().set_method("GET").set_uri(
                request.build_url()).build())
        if response.status_code != 200:
            raise SearchManager.SearchException(response.status_code)
        return json.loads(response.payload)

    class SearchException(Exception):
        """ """

        def __init__(self, status_code: int):
            super().__init__("Search failed with code {}.".format(status_code))

    class SearchRequest:
        """ """
        query: typing.Final[str]
        __catalogue = ""
        __country = ""
        __image_size = ""
        __limit = 10
        __locale = ""
        __username = ""

        def __init__(self, query: str):
            self.query = query
            if query == "":
                raise TypeError

        def build_url(self) -> str:
            """ """
            url = SearchManager.base_url + urllib.parse.quote(self.query)
            url += "?entityVersion=2"
            url += "&catalogue=" + urllib.parse.quote(self.__catalogue)
            url += "&country=" + urllib.parse.quote(self.__country)
            url += "&imageSize=" + urllib.parse.quote(self.__image_size)
            url += "&limit=" + str(self.__limit)
            url += "&locale=" + urllib.parse.quote(self.__locale)
            url += "&username=" + urllib.parse.quote(self.__username)
            return url

        def get_catalogue(self) -> str:
            """ """
            return self.__catalogue

        def get_country(self) -> str:
            """ """
            return self.__country

        def get_image_size(self) -> str:
            """ """
            return self.__image_size

        def get_limit(self) -> int:
            """ """
            return self.__limit

        def get_locale(self) -> str:
            """ """
            return self.__locale

        def get_username(self) -> str:
            """ """
            return self.__username

        def set_catalogue(self, catalogue: str) -> SearchManager.SearchRequest:
            """

            :param catalogue: str:

            """
            self.__catalogue = catalogue
            return self

        def set_country(self, country: str) -> SearchManager.SearchRequest:
            """

            :param country: str:

            """
            self.__country = country
            return self

        def set_image_size(self,
                           image_size: str) -> SearchManager.SearchRequest:
            """

            :param image_size: str:

            """
            self.__image_size = image_size
            return self

        def set_limit(self, limit: int) -> SearchManager.SearchRequest:
            """

            :param limit: int:

            """
            self.__limit = limit
            return self

        def set_locale(self, locale: str) -> SearchManager.SearchRequest:
            """

            :param locale: str:

            """
            self.__locale = locale
            return self

        def set_username(self, username: str) -> SearchManager.SearchRequest:
            """

            :param username: str:

            """
            self.__username = username
            return self


class TokenProvider:
    """ """
    logger = logging.getLogger("Librespot:TokenProvider")
    token_expire_threshold = 10
    __session: Session
    __tokens: typing.List[StoredToken] = []

    def __init__(self, session: Session):
        self._session = session

    def find_token_with_all_scopes(
            self, scopes: typing.List[str]) -> typing.Union[StoredToken, None]:
        """

        :param scopes: typing.List[str]:

        """
        for token in self.__tokens:
            if token.has_scopes(scopes):
                return token
        return None

    def get(self, scope: str) -> str:
        """

        :param scope: str:

        """
        return self.get_token(scope).access_token

    def get_token(self, *scopes) -> StoredToken:
        """

        :param *scopes:

        """
        scopes = list(scopes)
        if len(scopes) == 0:
            raise RuntimeError("The token doesn't have any scope")
        token = self.find_token_with_all_scopes(scopes)
        if token is not None:
            if token.expired():
                self.__tokens.remove(token)
            else:
                return token
        self.logger.debug(
            "Token expired or not suitable, requesting again. scopes: {}, old_token: {}"
            .format(scopes, token))
        response = self._session.mercury().send_sync_json(
            MercuryRequests.request_token(self._session.device_id(),
                                          ",".join(scopes)))
        token = TokenProvider.StoredToken(response)
        self.logger.debug(
            "Updated token successfully! scopes: {}, new_token: {}".format(
                scopes, token))
        self.__tokens.append(token)
        return token

    class StoredToken:
        """ """
        expires_in: int
        access_token: str
        scopes: typing.List[str]
        timestamp: int

        def __init__(self, obj):
            self.timestamp = int(time.time_ns() / 1000)
            self.expires_in = obj["expiresIn"]
            self.access_token = obj["accessToken"]
            self.scopes = obj["scope"]

        def expired(self) -> bool:
            """ """
            return self.timestamp + (self.expires_in - TokenProvider.
                                     token_expire_threshold) * 1000 * 1000 < int(
                                         time.time_ns() / 1000)

        def has_scope(self, scope: str) -> bool:
            """

            :param scope: str:

            """
            for s in self.scopes:
                if s == scope:
                    return True
            return False

        def has_scopes(self, sc: typing.List[str]) -> bool:
            """

            :param sc: typing.List[str]:

            """
            for s in sc:
                if not self.has_scope(s):
                    return False
            return True
