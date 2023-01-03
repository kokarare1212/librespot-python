from __future__ import annotations
from librespot import util
from librespot.proto.ContextTrack_pb2 import ContextTrack
from librespot.util import Base62
import re


class SpotifyId:
    STATIC_FROM_URI = "fromUri"
    STATIC_FROM_BASE62 = "fromBase62"
    STATIC_FROM_HEX = "fromHex"

    @staticmethod
    def from_base62(base62: str):
        raise NotImplementedError

    @staticmethod
    def from_hex(hex_str: str):
        raise NotImplementedError

    @staticmethod
    def from_uri(uri: str):
        raise NotImplementedError

    def to_spotify_uri(self) -> str:
        raise NotImplementedError

    class SpotifyIdParsingException(Exception):
        pass


class PlayableId:
    base62 = Base62.create_instance_with_inverted_character_set()

    @staticmethod
    def from_uri(uri: str) -> PlayableId:
        if not PlayableId.is_supported(uri):
            return UnsupportedId(uri)
        if TrackId.pattern.search(uri) is not None:
            return TrackId.from_uri(uri)
        if EpisodeId.pattern.search(uri) is not None:
            return EpisodeId.from_uri(uri)
        raise TypeError("Unknown uri: {}".format(uri))

    @staticmethod
    def is_supported(uri: str):
        return (not uri.startswith("spotify:local:")
                and not uri == "spotify:delimiter"
                and not uri == "spotify:meta:delimiter")

    @staticmethod
    def should_play(track: ContextTrack):
        return track.metadata_or_default

    def get_gid(self) -> bytes:
        raise NotImplementedError

    def hex_id(self) -> str:
        raise NotImplementedError

    def to_spotify_uri(self) -> str:
        raise NotImplementedError


class PlaylistId(SpotifyId):
    base62 = Base62.create_instance_with_inverted_character_set()
    pattern = re.compile(r"spotify:playlist:(.{22})")
    __id: str

    def __init__(self, _id: str):
        self.__id = _id

    @staticmethod
    def from_uri(uri: str) -> PlaylistId:
        matcher = PlaylistId.pattern.search(uri)
        if matcher is not None:
            playlist_id = matcher.group(1)
            return PlaylistId(playlist_id)
        raise TypeError("Not a Spotify playlist ID: {}.".format(uri))

    def id(self) -> str:
        return self.__id

    def to_spotify_uri(self) -> str:
        return "spotify:playlist:" + self.__id


class UnsupportedId(PlayableId):
    uri: str

    def __init__(self, uri: str):
        self.uri = uri

    def get_gid(self) -> bytes:
        raise TypeError()

    def hex_id(self) -> str:
        raise TypeError()

    def to_spotify_uri(self) -> str:
        return self.uri


class AlbumId(SpotifyId):
    base62 = Base62.create_instance_with_inverted_character_set()
    pattern = re.compile(r"spotify:album:(.{22})")
    __hex_id: str

    def __init__(self, hex_id: str):
        self.__hex_id = hex_id.lower()

    @staticmethod
    def from_uri(uri: str) -> AlbumId:
        matcher = AlbumId.pattern.search(uri)
        if matcher is not None:
            album_id = matcher.group(1)
            return AlbumId(util.bytes_to_hex(AlbumId.base62.decode(album_id.encode(), 16)))
        raise TypeError("Not a Spotify album ID: {}.".format(uri))

    @staticmethod
    def from_base62(base62: str) -> AlbumId:
        return AlbumId(util.bytes_to_hex(AlbumId.base62.decode(base62.encode(), 16)))

    @staticmethod
    def from_hex(hex_str: str) -> AlbumId:
        return AlbumId(hex_str)

    def to_mercury_uri(self) -> str:
        return "hm://metadata/4/album/{}".format(self.__hex_id)

    def hex_id(self) -> str:
        return self.__hex_id

    def to_spotify_uri(self) -> str:
        return "spotify:album:{}".format(
            AlbumId.base62.encode(util.hex_to_bytes(self.__hex_id)).decode())


class ArtistId(SpotifyId):
    base62 = Base62.create_instance_with_inverted_character_set()
    pattern = re.compile("spotify:artist:(.{22})")
    __hex_id: str

    def __init__(self, hex_id: str):
        self.__hex_id = hex_id.lower()

    @staticmethod
    def from_uri(uri: str) -> ArtistId:
        matcher = ArtistId.pattern.search(uri)
        if matcher is not None:
            artist_id = matcher.group(1)
            return ArtistId(
                util.bytes_to_hex(ArtistId.base62.decode(artist_id.encode(), 16)))
        raise TypeError("Not a Spotify artist ID: {}".format(uri))

    @staticmethod
    def from_base62(base62: str) -> ArtistId:
        return ArtistId(util.bytes_to_hex(ArtistId.base62.decode(base62.encode(), 16)))

    @staticmethod
    def from_hex(hex_str: str) -> ArtistId:
        return ArtistId(hex_str)

    def to_mercury_uri(self) -> str:
        return "hm://metadata/4/artist/{}".format(self.__hex_id)

    def to_spotify_uri(self) -> str:
        return "spotify:artist:{}".format(
            ArtistId.base62.encode(util.hex_to_bytes(self.__hex_id)).decode())

    def hex_id(self) -> str:
        return self.__hex_id


class EpisodeId(SpotifyId, PlayableId):
    pattern = re.compile(r"spotify:episode:(.{22})")
    __hex_id: str

    def __init__(self, hex_id: str):
        self.__hex_id = hex_id.lower()

    @staticmethod
    def from_uri(uri: str) -> EpisodeId:
        matcher = EpisodeId.pattern.search(uri)
        if matcher is not None:
            episode_id = matcher.group(1)
            return EpisodeId(
                util.bytes_to_hex(PlayableId.base62.decode(episode_id.encode(), 16)))
        raise TypeError("Not a Spotify episode ID: {}".format(uri))

    @staticmethod
    def from_base62(base62: str) -> EpisodeId:
        return EpisodeId(
            util.bytes_to_hex(PlayableId.base62.decode(base62.encode(), 16)))

    @staticmethod
    def from_hex(hex_str: str) -> EpisodeId:
        return EpisodeId(hex_str)

    def to_mercury_uri(self) -> str:
        return "hm://metadata/4/episode/{}".format(self.__hex_id)

    def to_spotify_uri(self) -> str:
        return "Spotify:episode:{}".format(
            PlayableId.base62.encode(util.hex_to_bytes(self.__hex_id)).decode())

    def hex_id(self) -> str:
        return self.__hex_id

    def get_gid(self) -> bytes:
        return util.hex_to_bytes(self.__hex_id)


class ShowId(SpotifyId):
    base62 = Base62.create_instance_with_inverted_character_set()
    pattern = re.compile("spotify:show:(.{22})")
    __hex_id: str

    def __init__(self, hex_id: str):
        self.__hex_id = hex_id

    @staticmethod
    def from_uri(uri: str) -> ShowId:
        matcher = ShowId.pattern.search(uri)
        if matcher is not None:
            show_id = matcher.group(1)
            return ShowId(util.bytes_to_hex(ShowId.base62.decode(show_id.encode(), 16)))
        raise TypeError("Not a Spotify show ID: {}".format(uri))

    @staticmethod
    def from_base62(base62: str) -> ShowId:
        return ShowId(util.bytes_to_hex(ShowId.base62.decode(base62.encode(), 16)))

    @staticmethod
    def from_hex(hex_str: str) -> ShowId:
        return ShowId(hex_str)

    def to_mercury_uri(self) -> str:
        return "hm://metadata/4/show/{}".format(self.__hex_id)

    def to_spotify_uri(self) -> str:
        return "spotify:show:{}".format(
            ShowId.base62.encode(util.hex_to_bytes(self.__hex_id)).decode())

    def hex_id(self) -> str:
        return self.__hex_id


class TrackId(PlayableId, SpotifyId):
    pattern = re.compile("spotify:track:(.{22})")
    __hex_id: str

    def __init__(self, hex_id: str):
        self.__hex_id = hex_id.lower()

    @staticmethod
    def from_uri(uri: str) -> TrackId:
        search = TrackId.pattern.search(uri)
        if search is not None:
            track_id = search.group(1)
            return TrackId(
                util.bytes_to_hex(PlayableId.base62.decode(track_id.encode(), 16)))
        raise RuntimeError("Not a Spotify track ID: {}".format(uri))

    @staticmethod
    def from_base62(base62: str) -> TrackId:
        return TrackId(util.bytes_to_hex(PlayableId.base62.decode(base62.encode(), 16)))

    @staticmethod
    def from_hex(hex_str: str) -> TrackId:
        return TrackId(hex_str)

    def to_mercury_uri(self) -> str:
        return "hm://metadata/4/track/{}".format(self.__hex_id)

    def to_spotify_uri(self) -> str:
        return "spotify:track:{}".format(TrackId.base62.encode(util.hex_to_bytes(self.__hex_id)).decode())

    def hex_id(self) -> str:
        return self.__hex_id

    def get_gid(self) -> bytes:
        return util.hex_to_bytes(self.__hex_id)
