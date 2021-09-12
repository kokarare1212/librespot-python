from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from librespot.core import Session


class CacheManager:
    clean_up_threshold = 604800000
    header_hash = 253
    header_timestamp = 254
    parent: str

    def __init__(self, session: Session):
        """
        @Todo Implement function
        :param session:
        """
