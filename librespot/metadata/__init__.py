from __future__ import annotations

import re

from librespot.common import Base62
from librespot.common import Utils
from librespot.proto.ContextTrack import ContextTrack


class SpotifyId:
    STATIC_FROM_URI = "fromUri"
    STATIC_FROM_BASE62 = "fromBase62"
    STATIC_FROM_HEX = "fromHex"

    @staticmethod
    def from_base62(base62: str):
        pass

    @staticmethod
    def from_hex(hex_str: str):
        pass

    @staticmethod
    def from_uri(uri: str):
        pass

    def to_spotify_uri(self) -> str:
        pass

    class SpotifyIdParsingException(Exception):
        pass


class PlayableId:
    BASE62 = Base62.create_instance_with_inverted_character_set()

    @staticmethod
    def from_uri(uri: str) -> PlayableId:
        pass
        if not PlayableId.is_supported(uri):
            return UnsupportedId(uri)

        if TrackId.PATTERN.search(uri) is not None:
            return TrackId.from_uri(uri)
        elif EpisodeId.PATTERN.search(uri) is not None:
            return EpisodeId.from_uri(uri)
        else:
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
        pass

    def hex_id(self) -> str:
        pass

    def to_spotify_uri(self) -> str:
        pass


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


class ArtistId(SpotifyId):
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


class EpisodeId(SpotifyId, PlayableId):
    PATTERN = re.compile(r"spotify:episode:(.{22})")
    _hexId: str

    def __init__(self, hex_id: str):
        self._hexId = hex_id.lower()

    @staticmethod
    def from_uri(uri: str) -> EpisodeId:
        matcher = EpisodeId.PATTERN.search(uri)
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


class ShowId(SpotifyId):
    _PATTERN = re.compile("spotify:show:(.{22})")
    _BASE62 = Base62.create_instance_with_inverted_character_set()
    _hexId: str

    def __init__(self, hex_id: str):
        self._hexId = hex_id

    @staticmethod
    def from_uri(uri: str) -> ShowId:
        matcher = ShowId._PATTERN.search(uri)
        if matcher is not None:
            show_id = matcher.group(1)
            return ShowId(
                Utils.bytes_to_hex(ShowId._BASE62.decode(show_id, 16)))
        raise TypeError("Not a Spotify show ID: {}".format(uri))

    @staticmethod
    def from_base62(base62: str) -> ShowId:
        return ShowId(Utils.bytes_to_hex(ShowId._BASE62.decode(base62, 16)))

    @staticmethod
    def from_hex(hex_str: str) -> ShowId:
        return ShowId(hex_str)

    def to_mercury_uri(self) -> str:
        return "hm://metadata/4/show/{}".format(self._hexId)

    def to_spotify_uri(self) -> str:
        return "spotify:show:{}".format(
            ShowId._BASE62.encode(Utils.hex_to_bytes(self._hexId)))

    def hex_id(self) -> str:
        return self._hexId


class TrackId(PlayableId, SpotifyId):
    PATTERN = re.compile("spotify:track:(.{22})")
    _hexId: str

    def __init__(self, hex_id: str):
        self._hexId = hex_id.lower()

    @staticmethod
    def from_uri(uri: str) -> TrackId:
        search = TrackId.PATTERN.search(uri)
        if search is not None:
            track_id = search.group(1)
            return TrackId(
                Utils.bytes_to_hex(PlayableId.BASE62.decode(track_id, 16)))
        raise RuntimeError("Not a Spotify track ID: {}".format(uri))

    @staticmethod
    def from_base62(base62: str) -> TrackId:
        return TrackId(Utils.bytes_to_hex(PlayableId.BASE62.decode(base62,
                                                                   16)))

    @staticmethod
    def from_hex(hex_str: str) -> TrackId:
        return TrackId(hex_str)

    def to_spotify_uri(self) -> str:
        return "spotify:track:{}".format(self._hexId)

    def hex_id(self) -> str:
        return self._hexId

    def get_gid(self) -> bytes:
        return Utils.hex_to_bytes(self._hexId)
