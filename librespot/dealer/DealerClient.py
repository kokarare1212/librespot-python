from __future__ import annotations
from librespot.standard.Closeable import Closeable
import typing


class DealerClient(Closeable):
    def __init__(self, session):
        pass

    def connect(self):
        pass

    def add_message_listener(self, listener: DealerClient.MessageListener,
                             *uris: str):
        pass

    class MessageListener:
        def on_message(self, uri: str, headers: typing.Dict[str, str],
                       payload: bytes):
            pass
