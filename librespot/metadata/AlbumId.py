from __future__ import annotations

from librespot.common import Base62, Utils
from librespot.metadata import SpotifyId
import re


class AlbumId(SpotifyId.SpotifyId):
    _PATTERN = re.compile(r"spotify:album:(.{22})")
    _BASE62 = Base62.create_instance_with_inverted_character_set()
    _hexId: str

    def __init__(self, hex_id: str):
        self._hexId = hex_id.lower()

    @staticmethod
    def from_uri(uri: str) -> AlbumId:
        matcher = AlbumId._PATTERN.search(uri)
        if matcher is not None:
            album_id = matcher.group(1)
            return AlbumId(
                Utils.bytes_to_hex(AlbumId._BASE62.decode(album_id, 16)))
        else:
            raise TypeError("Not a Spotify album ID: {}.f".format(uri))

    @staticmethod
    def from_base62(base62: str) -> AlbumId:
        return AlbumId(Utils.bytes_to_hex(AlbumId._BASE62.decode(base62, 16)))

    @staticmethod
    def from_hex(hex_str: str) -> AlbumId:
        return AlbumId(hex_str)

    def to_mercury_uri(self) -> str:
        return "spotify:album:{}".format(
            AlbumId._BASE62.encode(Utils.hex_to_bytes(self._hexId)))

    def hex_id(self) -> str:
        return self._hexId
