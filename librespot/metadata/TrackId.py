from __future__ import annotations
from librespot.common import Utils
from librespot.metadata import SpotifyId
from librespot.metadata.PlayableId import PlayableId
import re


class TrackId(PlayableId, SpotifyId):
    _PATTERN = re.compile("spotify:track:(.{22})")
    _hexId: str

    def __init__(self, hex_id: str):
        self._hexId = hex_id.lower()

    @staticmethod
    def from_uri(uri: str) -> TrackId:
        search = TrackId._PATTERN.search(uri)
        if search is not None:
            track_id = search.group(1)
            return TrackId(Utils.bytes_to_hex(PlayableId.BASE62.decode(track_id, 16)))
        else:
            raise RuntimeError("Not a Spotify track ID: {}".format(uri))

    @staticmethod
    def from_base62(base62: str) -> TrackId:
        return TrackId(Utils.bytes_to_hex(PlayableId.BASE62.decode(base62, 16)))

    @staticmethod
    def from_hex(hex_str: str) -> TrackId:
        return TrackId(hex_str)

    def to_spotify_uri(self) -> str:
        return "spotify:track:{}".format(self._hexId)

    def hex_id(self) -> str:
        return self._hexId

    def get_gid(self) -> bytes:
        return Utils.hex_to_bytes(self._hexId)
