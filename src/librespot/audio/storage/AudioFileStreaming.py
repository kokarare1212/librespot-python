from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from librespot.core.Session import Session


class AudioFileStreaming:
    cache_handler = None

    def __init__(self, session: Session):
        pass
