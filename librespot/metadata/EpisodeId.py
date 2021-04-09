from __future__ import annotations
from librespot.common import Utils
from librespot.metadata import SpotifyId
from librespot.metadata.PlayableId import PlayableId
import re


class EpisodeId(SpotifyId.SpotifyId, PlayableId):
    _PATTERN = re.compile(r"spotify:episode:(.{22})")
    _hexId: str

    def __init__(self, hex_id: str):
        self._hexId = hex_id.lower()

    @staticmethod
    def from_uri(uri: str) -> EpisodeId:
        matcher = EpisodeId._PATTERN.search(uri)
        if matcher is not None:
            episode_id = matcher.group(1)
            return EpisodeId(
                Utils.Utils.bytes_to_hex(
                    PlayableId.BASE62.decode(episode_id, 16)))
        TypeError("Not a Spotify episode ID: {}".format(uri))

    @staticmethod
    def from_base62(base62: str) -> EpisodeId:
        return EpisodeId(
            Utils.Utils.bytes_to_hex(PlayableId.BASE62.decode(base62, 16)))

    @staticmethod
    def from_hex(hex_str: str) -> EpisodeId:
        return EpisodeId(hex_str)

    def to_mercury_uri(self) -> str:
        return "hm://metadata/4/episode/{}".format(self._hexId)

    def to_spotify_uri(self) -> str:
        return "Spotify:episode:{}".format(
            PlayableId.BASE62.encode(Utils.Utils.hex_to_bytes(self._hexId)))

    def hex_id(self) -> str:
        return self._hexId

    def get_gid(self) -> bytes:
        return Utils.Utils.hex_to_bytes(self._hexId)
