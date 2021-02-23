from __future__ import annotations
from librespot.core import Session


class CacheManager:
    CLEAN_UP_THRESHOLD = 604800000
    HEADER_TIMESTAMP = 254
    HEADER_HASH = 253

    parent: str

    def __init__(self, conf: Session.Configuration):
        pass
