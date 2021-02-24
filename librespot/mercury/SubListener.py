from __future__ import annotations
from librespot.mercury import MercuryClient


class SubListener:
    def event(self, resp: MercuryClient.Response) -> None:
        pass
