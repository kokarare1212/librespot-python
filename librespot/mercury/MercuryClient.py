from __future__ import annotations
from librespot.common import Utils
from librespot.core import Session, PacketsReceiver
from librespot.crypto import Packet
from librespot.mercury import JsonMercuryRequest, RawMercuryRequest, SubListener
from librespot.standard import BytesInputStream, BytesOutputStream, Closeable
from librespot.proto import Mercury, Pubsub
import json
import logging
import queue
import threading
import typing


class MercuryClient(PacketsReceiver.PacketsReceiver, Closeable):
    _LOGGER: logging = logging.getLogger(__name__)
    _MERCURY_REQUEST_TIMEOUT: int = 3
    _seqHolder: int = 1
    _seqHolderLock: threading.Condition = threading.Condition()
    _callbacks: dict[int, Callback] = {}
    _removeCallbackLock: threading.Condition = threading.Condition()
    _subscriptions: list[MercuryClient.InternalSubListener] = []
    _subscriptionsLock: threading.Condition = threading.Condition()
    _partials: dict[int, bytes] = {}
    _session: Session = None

    def __init__(self, session: Session):
        self._session = session

    def subscribe(self, uri: str, listener: SubListener) -> None:
        response = self.send_sync(RawMercuryRequest.sub(uri))
        if response.status_code != 200:
            raise RuntimeError(response)

        if len(response.payload) > 0:
            for payload in response.payload:
                sub = Pubsub.Subscription()
                sub.ParseFromString(payload)
                self._subscriptions.append(
                    MercuryClient.InternalSubListener(sub.uri, listener, True))
        else:
            self._subscriptions.append(
                MercuryClient.InternalSubListener(uri, listener, True))

        self._LOGGER.debug("Subscribed successfully to {}!".format(uri))

    def unsubscribe(self, uri) -> None:
        response = self.send_sync(RawMercuryRequest.unsub(uri))
        if response.status_code != 200:
            raise RuntimeError(response)

        for subscription in self._subscriptions:
            if subscription.matches(uri):
                self._subscriptions.remove(subscription)
                break
        self._LOGGER.debug("Unsubscribed successfully from {}!".format(uri))

    def send_sync(self, request: RawMercuryRequest) -> MercuryClient.Response:
        callback = MercuryClient.SyncCallback()
        seq = self.send(request, callback)

        try:
            resp = callback.wait_response()
            if resp is None:
                raise IOError(
                    "Request timeout out, {} passed, yet no response. seq: {}".
                    format(self._MERCURY_REQUEST_TIMEOUT, seq))
            return resp
        except queue.Empty as e:
            raise IOError(e)

    def send_sync_json(self, request: JsonMercuryRequest) -> typing.Any:
        resp = self.send_sync(request.request)
        if 200 <= resp.status_code < 300:
            return json.loads(resp.payload[0])
        else:
            raise MercuryClient.MercuryException(resp)

    def send(self, request: RawMercuryRequest, callback) -> int:
        buffer = BytesOutputStream()

        seq: int
        with self._seqHolderLock:
            seq = self._seqHolder
            self._seqHolder += 1

        self._LOGGER.debug(
            "Send Mercury request, seq: {}, uri: {}, method: {}".format(
                seq, request.header.uri, request.header.method))

        buffer.write_short(4)
        buffer.write_int(seq)

        buffer.write_byte(1)
        buffer.write_short(1 + len(request.payload))

        header_bytes = request.header.SerializeToString()
        buffer.write_short(len(header_bytes))
        buffer.write(header_bytes)

        for part in request.payload:
            buffer.write_short(len(part))
            buffer.write(part)

        cmd = Packet.Type.for_method(request.header.method)
        self._session.send(cmd, buffer.buffer)

        self._callbacks[seq] = callback
        return seq

    def dispatch(self, packet: Packet) -> None:
        payload = BytesInputStream(packet.payload)
        seq_length = payload.read_short()
        if seq_length == 2:
            seq = payload.read_short()
        elif seq_length == 4:
            seq = payload.read_int()
        elif seq_length == 8:
            seq = payload.read_long()
        else:
            raise RuntimeError("Unknown seq length: {}".format(seq_length))

        flags = payload.read_byte()
        parts = payload.read_short()

        partial = self._partials.get(seq)
        if partial is None or flags == 0:
            partial = []
            self._partials[seq] = partial

        self._LOGGER.debug(
            "Handling packet, cmd: 0x{}, seq: {}, flags: {}, parts: {}".format(
                Utils.bytes_to_hex(packet.cmd), seq, flags, parts))

        for i in range(parts):
            size = payload.read_short()
            buffer = payload.read(size)
            partial.append(buffer)
            self._partials[seq] = partial

        if flags != b"\x01":
            return

        self._partials.pop(seq)

        header = Mercury.Header()
        header.ParseFromString(partial[0])

        resp = MercuryClient.Response(header, partial)

        if packet.is_cmd(Packet.Type.mercury_event):
            dispatched = False
            with self._subscriptionsLock:
                for sub in self._subscriptions:
                    if sub.matches(header.uri):
                        sub.dispatch(resp)
                        dispatched = True

            if not dispatched:
                self._LOGGER.debug(
                    "Couldn't dispatch Mercury event seq: {}, uri: {}, code: {}, payload: {}"
                    .format(seq, header.uri, header.status_code, resp.payload))
        elif packet.is_cmd(Packet.Type.mercury_req) or \
                packet.is_cmd(Packet.Type.mercury_sub) or \
                packet.is_cmd(Packet.Type.mercury_sub):
            callback = self._callbacks.get(seq)
            self._callbacks.pop(seq)
            if callback is not None:
                callback.response(resp)
            else:
                self._LOGGER.warning(
                    "Skipped Mercury response, seq: {}, uri: {}, code: {}".
                    format(seq, resp.uri, resp.status_code))

            with self._removeCallbackLock:
                self._removeCallbackLock.notify_all()
        else:
            self._LOGGER.warning(
                "Couldn't handle packet, seq: {}, uri: {}, code: {}".format(
                    seq, header.uri, header.status_code))

    def interested_in(self, uri: str, listener: SubListener) -> None:
        self._subscriptions.append(
            MercuryClient.InternalSubListener(uri, listener, False))

    def not_interested_in(self, listener: SubListener) -> None:
        try:
            # noinspection PyTypeChecker
            self._subscriptions.remove(listener)
        except ValueError:
            pass

    def close(self) -> None:
        if len(self._subscriptions) != 0:
            for listener in self._subscriptions:
                if listener.isSub:
                    self.unsubscribe(listener.uri)
                else:
                    self.not_interested_in(listener.listener)

        if len(self._callbacks) != 0:
            with self._removeCallbackLock:
                self._removeCallbackLock.wait(self._MERCURY_REQUEST_TIMEOUT)

        self._callbacks.clear()

    class Callback:
        def response(self, response) -> None:
            pass

    class SyncCallback(Callback):
        _reference = queue.Queue()

        def response(self, response) -> None:
            self._reference.put(response)
            self._reference.task_done()

        def wait_response(self) -> typing.Any:
            return self._reference.get(
                timeout=MercuryClient._MERCURY_REQUEST_TIMEOUT)

    # class PubSubException(MercuryClient.MercuryException):
    #     pass

    class InternalSubListener:
        uri: str
        listener: SubListener
        isSub: bool

        def __init__(self, uri: str, listener: SubListener, is_sub: bool):
            self.uri = uri
            self.listener = listener
            self.isSub = is_sub

        def matches(self, uri: str) -> bool:
            return uri.startswith(self.uri)

        def dispatch(self, resp: MercuryClient.Response) -> None:
            self.listener.event(resp)

    class MercuryException(Exception):
        code: int

        def __init__(self, response):
            super("status: {}".format(response.status_code))
            self.code = response.status_code

    class Response:
        uri: str
        payload: list[bytes]
        status_code: int

        def __init__(self, header: Mercury.Header, payload: list[bytes]):
            self.uri = header.uri
            self.status_code = header.status_code
            self.payload = payload[1:]
