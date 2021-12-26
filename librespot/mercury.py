from __future__ import annotations
from librespot import util
from librespot.crypto import Packet
from librespot.proto import Mercury_pb2 as Mercury, Pubsub_pb2 as Pubsub
from librespot.structure import Closeable, PacketsReceiver, SubListener
import io
import json
import logging
import queue
import struct
import threading
import typing

if typing.TYPE_CHECKING:
    from librespot.core import Session


class JsonMercuryRequest:
    request: RawMercuryRequest

    def __init__(self, request: RawMercuryRequest):
        self.request = request


class MercuryClient(Closeable, PacketsReceiver):
    logger = logging.getLogger("Librespot:MercuryClient")
    mercury_request_timeout = 3
    __callbacks: typing.Dict[int, Callback] = {}
    __remove_callback_lock = threading.Condition()
    __partials: typing.Dict[int, typing.List[bytes]] = {}
    __seq_holder = 0
    __seq_holder_lock = threading.Condition()
    __session: Session
    __subscriptions: typing.List[InternalSubListener] = []
    __subscriptions_lock = threading.Condition()

    def __init__(self, session: Session):
        self.__session = session

    def close(self) -> None:
        """
        Close the MercuryClient instance
        """
        if len(self.__subscriptions) != 0:
            for listener in self.__subscriptions:
                if listener.is_sub:
                    self.unsubscribe(listener.uri)
                else:
                    self.not_interested_in(listener.listener)
        if len(self.__callbacks) != 0:
            with self.__remove_callback_lock:
                self.__remove_callback_lock.wait(self.mercury_request_timeout)
        self.__callbacks.clear()

    def dispatch(self, packet: Packet) -> None:
        payload = io.BytesIO(packet.payload)
        seq_length = struct.unpack(">H", payload.read(2))[0]
        if seq_length == 2:
            seq = struct.unpack(">H", payload.read(2))[0]
        elif seq_length == 4:
            seq = struct.unpack(">i", payload.read(4))[0]
        elif seq_length == 8:
            seq = struct.unpack(">q", payload.read(8))[0]
        else:
            raise RuntimeError("Unknown seq length: {}".format(seq_length))
        flags = payload.read(1)
        parts = struct.unpack(">H", payload.read(2))[0]
        partial = self.__partials.get(seq)
        if partial is None or flags == 0:
            partial = []
            self.__partials[seq] = partial
        self.logger.debug(
            "Handling packet, cmd: 0x{}, seq: {}, flags: {}, parts: {}".format(
                util.bytes_to_hex(packet.cmd), seq, flags, parts))
        for _ in range(parts):
            size = struct.unpack(">H", payload.read(2))[0]
            buffer = payload.read(size)
            partial.append(buffer)
            self.__partials[seq] = partial
        if flags != b"\x01":
            return
        self.__partials.pop(seq)
        header = Mercury.Header()
        header.ParseFromString(partial[0])
        response = MercuryClient.Response(header, partial)
        if packet.is_cmd(Packet.Type.mercury_event):
            dispatched = False
            with self.__subscriptions_lock:
                for sub in self.__subscriptions:
                    if sub.matches(header.uri):
                        sub.dispatch(response)
                        dispatched = True
            if not dispatched:
                self.logger.debug(
                    "Couldn't dispatch Mercury event seq: {}, uri: {}, code: {}, payload: {}"
                    .format(seq, header.uri, header.status_code,
                            response.payload))
        elif (packet.is_cmd(Packet.Type.mercury_req)
              or packet.is_cmd(Packet.Type.mercury_sub)
              or packet.is_cmd(Packet.Type.mercury_sub)):
            callback = self.__callbacks.get(seq)
            self.__callbacks.pop(seq)
            if callback is not None:
                callback.response(response)
            else:
                self.logger.warning(
                    "Skipped Mercury response, seq: {}, uri: {}, code: {}".
                    format(seq, response.uri, response.status_code))
            with self.__remove_callback_lock:
                self.__remove_callback_lock.notify_all()
        else:
            self.logger.warning(
                "Couldn't handle packet, seq: {}, uri: {}, code: {}".format(
                    seq, header.uri, header.status_code))

    def interested_in(self, uri: str, listener: SubListener) -> None:
        self.__subscriptions.append(
            MercuryClient.InternalSubListener(uri, listener, False))

    def not_interested_in(self, listener: SubListener) -> None:
        try:
            for subscription in self.__subscriptions:
                if subscription.listener is listener:
                    self.__subscriptions.remove(subscription)
                    break
        except ValueError:
            pass

    def send(self, request: RawMercuryRequest, callback) -> int:
        """
        Send the Mercury request
        Args:
            request: RawMercuryRequest
            callback: Callback function
        Returns:
            MercuryClient.Response
        """
        buffer = io.BytesIO()
        seq: int
        with self.__seq_holder_lock:
            seq = self.__seq_holder
            self.__seq_holder += 1
        self.logger.debug(
            "Send Mercury request, seq: {}, uri: {}, method: {}".format(
                seq, request.header.uri, request.header.method))
        buffer.write(struct.pack(">H", 4))
        buffer.write(struct.pack(">i", seq))
        buffer.write(b"\x01")
        buffer.write(struct.pack(">H", 1 + len(request.payload)))
        header_bytes = request.header.SerializeToString()
        buffer.write(struct.pack(">H", len(header_bytes)))
        buffer.write(header_bytes)
        for part in request.payload:
            buffer.write(struct.pack(">H", len(part)))
            buffer.write(part)
        buffer.seek(0)
        cmd = Packet.Type.for_method(request.header.method)
        self.__session.send(cmd, buffer.read())
        self.__callbacks[seq] = callback
        return seq

    def send_sync(self, request: RawMercuryRequest) -> Response:
        """
        Send the Mercury request
        Args:
            request: RawMercuryRequest
        Returns:
            MercuryClient.Response
        """
        callback = MercuryClient.SyncCallback()
        seq = self.send(request, callback)
        try:
            response = callback.wait_response()
            if response is None:
                raise IOError(
                    "Request timeout out, {} passed, yet no response. seq: {}".
                    format(self.mercury_request_timeout, seq))
            return response
        except queue.Empty as e:
            raise IOError(e)

    def send_sync_json(self, request: JsonMercuryRequest) -> typing.Any:
        response = self.send_sync(request.request)
        if 200 <= response.status_code < 300:
            return json.loads(response.payload)
        raise MercuryClient.MercuryException(response)

    def subscribe(self, uri: str, listener: SubListener) -> None:
        """
        Subscribe URI
        Args:
            uri:
            listener:
        """
        response = self.send_sync(RawMercuryRequest.sub(uri))
        if response.status_code != 200:
            raise RuntimeError(response)
        if len(response.payload) > 0:
            for payload in response.payload:
                sub = Pubsub.Subscription()
                sub.ParseFromString(payload)
                self.__subscriptions.append(
                    MercuryClient.InternalSubListener(sub.uri, listener, True))
        else:
            self.__subscriptions.append(
                MercuryClient.InternalSubListener(uri, listener, True))
        self.logger.debug("Subscribed successfully to {}!".format(uri))

    def unsubscribe(self, uri) -> None:
        """
        Unsubscribe URI
        Args:
            uri:
        """
        response = self.send_sync(RawMercuryRequest.unsub(uri))
        if response.status_code != 200:
            raise RuntimeError(response)
        for subscription in self.__subscriptions:
            if subscription.matches(uri):
                self.__subscriptions.remove(subscription)
                break
        self.logger.debug("Unsubscribed successfully from {}!".format(uri))

    class Callback:
        def response(self, response: MercuryClient.Response) -> None:
            raise NotImplementedError

    class InternalSubListener:
        uri: str
        listener: SubListener
        is_sub: bool

        def __init__(self, uri: str, listener: SubListener, is_sub: bool):
            self.uri = uri
            self.listener = listener
            self.is_sub = is_sub

        def matches(self, uri: str) -> bool:
            """
            Compare with the URI given
            Args:
                uri: URI to be compared
            Returns:
                bool
            """
            return uri.startswith(self.uri)

        def dispatch(self, response: MercuryClient.Response) -> None:
            """
            Dispatch the event response
            Args:
                response: Response generated by the event
            """
            self.listener.event(response)

    class MercuryException(Exception):
        code: int

        def __init__(self, response: MercuryClient.Response):
            super().__init__("status: {}".format(response.status_code))
            self.code = response.status_code

    class PubSubException(MercuryException):
        pass

    class Response:
        uri: str
        payload: bytes
        status_code: int

        def __init__(self, header: Mercury.Header, payload: list[bytes]):
            self.uri = header.uri
            self.status_code = header.status_code
            self.payload = b"".join(payload[1:])

    class SyncCallback(Callback):
        __reference = queue.Queue()

        def response(self, response: MercuryClient.Response) -> None:
            """
            Set the response
            :param response:
            :return:
            """
            self.__reference.put(response)
            self.__reference.task_done()

        def wait_response(self) -> typing.Any:
            return self.__reference.get(
                timeout=MercuryClient.mercury_request_timeout)


class MercuryRequests:
    keymaster_client_id = "65b708073fc0480ea92a077233ca87bd"

    @staticmethod
    def get_root_playlists(username: str):
        """
        @TODO implement function
        """

    @staticmethod
    def request_token(device_id, scope):
        return JsonMercuryRequest(
            RawMercuryRequest.get(
                "hm://keymaster/token/authenticated?scope={}&client_id={}&device_id={}"
                .format(scope, MercuryRequests.keymaster_client_id,
                        device_id)))


class RawMercuryRequest:
    header: Mercury.Header
    payload: typing.List[bytes]

    def __init__(self, header: Mercury.Header, payload: typing.List[bytes]):
        self.header = header
        self.payload = payload

    @staticmethod
    def sub(uri: str):
        return RawMercuryRequest.new_builder().set_uri(uri).set_method(
            "SUB").build()

    @staticmethod
    def unsub(uri: str):
        return RawMercuryRequest.new_builder().set_uri(uri).set_method(
            "UNSUB").build()

    @staticmethod
    def get(uri: str):
        return RawMercuryRequest.new_builder().set_uri(uri).set_method(
            "GET").build()

    @staticmethod
    def send(uri: str, part: bytes):
        return RawMercuryRequest.new_builder().set_uri(uri) \
            .add_payload_part(part).set_method("SEND").build()

    @staticmethod
    def post(uri: str, part: bytes):
        return RawMercuryRequest.new_builder().set_uri(uri) \
            .set_method("POST").add_payload_part(part).build()

    @staticmethod
    def new_builder():
        return RawMercuryRequest.Builder()

    class Builder:
        header_dict: dict
        payload: typing.List[bytes]

        def __init__(self):
            self.header_dict = {}
            self.payload = []

        def set_uri(self, uri: str):
            self.header_dict["uri"] = uri
            return self

        def set_content_type(self, content_type: str):
            self.header_dict["content_type"] = content_type
            return self

        def set_method(self, method: str):
            self.header_dict["method"] = method
            return self

        def add_user_field(self,
                           field: Mercury.UserField = None,
                           key: str = None,
                           value: str = None):
            if field is None and (key is None or value is None):
                return self
            try:
                self.header_dict["user_fields"]
            except KeyError:
                self.header_dict["user_fields"] = []
            if field is not None:
                self.header_dict["user_fields"].append(field)
            if key is not None and value is not None:
                self.header_dict["user_fields"].append(
                    Mercury.UserField(key=key, value=value.encode()))
            return self

        def add_payload_part(self, part: bytes):
            self.payload.append(part)
            return self

        def add_protobuf_payload(self, msg):
            return self.add_payload_part(msg)

        def build(self):
            return RawMercuryRequest(Mercury.Header(**self.header_dict),
                                     self.payload)
