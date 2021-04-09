from __future__ import annotations
from librespot.common import Base62, Utils
from librespot.metadata import SpotifyId
import re


class ArtistId(SpotifyId.SpotifyId):
    _PATTERN = re.compile("spotify:artist:(.{22})")
    _BASE62 = Base62.create_instance_with_inverted_character_set()
    _hexId: str

    def __init__(self, hex_id: str):
        self._hexId = hex_id

    @staticmethod
    def from_uri(uri: str) -> ArtistId:
        matcher = ArtistId._PATTERN.search(uri)
        if matcher is not None:
            artist_id = matcher.group(1)
            return ArtistId(
                Utils.bytes_to_hex(ArtistId._BASE62.decode(artist_id, 16)))
        else:
            raise TypeError("Not a Spotify artist ID: {}".format(uri))

    @staticmethod
    def from_base62(base62: str) -> ArtistId:
        return ArtistId(Utils.bytes_to_hex(ArtistId._BASE62.decode(base62,
                                                                   16)))

    @staticmethod
    def from_hex(hex_str: str) -> ArtistId:
        return ArtistId(hex_str)

    def to_mercury_uri(self) -> str:
        return "hm://metadata/4/artist/{}".format(self._hexId)

    def to_spotify_uri(self) -> str:
        return "spotify:artist:{}".format(
            ArtistId._BASE62.encode(Utils.hex_to_bytes(self._hexId)))

    def hex_id(self) -> str:
        return self._hexId
