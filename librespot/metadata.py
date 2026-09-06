from __future__ import annotations
from librespot import util
from librespot.proto.ContextTrack_pb2 import ContextTrack
from librespot.util import Base62
import re


class Id:
    b62 = Base62.create_instance_with_inverted_character_set()
    uri_pattern: str = None
    mercury_pattern: str = None

    def __init__(self, _id: str):
        self.__id = _id

    @classmethod
    def from_base62(cls, base62: str) -> Id:
        return cls(base62)

    @classmethod
    def from_hex(cls, hex_str: str) -> Id:
        return cls(cls.b62.encode(util.hex_to_bytes(hex_str)).decode())

    @classmethod
    def match_uri(cls, uri: str):
        if not cls.uri_pattern:
            raise NotImplementedError
        return re.search(cls.uri_pattern + r":(.{22})", uri)

    @classmethod
    def from_uri(cls, uri: str) -> Id:
        matcher = cls.match_uri(uri)
        if matcher is not None:
            return cls(matcher.group(1))
        raise TypeError("Not a Spotify ID: {}.".format(uri))

    def id(self) -> str:
        return self.__id

    def get_gid(self) -> bytes:
        return self.b62.decode(self.__id.encode(), 16)

    def hex_id(self) -> str:
        return util.bytes_to_hex(self.get_gid()).lower()

    def to_spotify_uri(self) -> str:
        if not self.uri_pattern:
            raise NotImplementedError
        return self.uri_pattern + ":" + self.__id

    def to_mercury_uri(self) -> str:
        if not self.mercury_pattern:
            raise NotImplementedError
        return self.mercury_pattern + "/" + self.hex_id()


class PlaylistId(Id):
    uri_pattern = r"spotify:playlist"


class AlbumId(Id):
    uri_pattern = r"spotify:album"
    mercury_pattern = "hm://metadata/4/album"


class ArtistId(Id):
    uri_pattern = r"spotify:artist"
    mercury_pattern = "hm://metadata/4/artist"


class ShowId(Id):
    uri_pattern = r"spotify:show"
    mercury_pattern = "hm://metadata/4/show"


class PlayableId:
    @staticmethod
    def from_uri(uri: str) -> PlayableId:
        if not PlayableId.is_supported(uri):
            return UnsupportedId(uri)
        if TrackId.match_uri(uri) is not None:
            return TrackId.from_uri(uri)
        if EpisodeId.match_uri(uri) is not None:
            return EpisodeId.from_uri(uri)
        raise TypeError("Unknown uri: {}".format(uri))

    @staticmethod
    def is_supported(uri: str) -> bool:
        return (not uri.startswith("spotify:local:")
                and not uri == "spotify:delimiter"
                and not uri == "spotify:meta:delimiter")

    @staticmethod
    def should_play(track: ContextTrack):
        return track.metadata_or_default


class UnsupportedId(PlayableId):
    def __init__(self, uri: str):
        self.uri = uri

    def id(self) -> str:
        raise TypeError()

    def get_gid(self) -> bytes:
        raise TypeError()

    def hex_id(self) -> str:
        raise TypeError()

    def to_spotify_uri(self) -> str:
        return self.uri

    def to_mercury_uri(self) -> str:
        raise TypeError()


class TrackId(Id, PlayableId):
    uri_pattern = r"spotify:track"
    mercury_pattern = "hm://metadata/4/track"


class EpisodeId(Id, PlayableId):
    uri_pattern = r"spotify:episode"
    mercury_pattern = "hm://metadata/4/episode"
