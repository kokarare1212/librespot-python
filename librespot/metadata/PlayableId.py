from __future__ import annotations
from librespot.common.Base62 import Base62
# from librespot.metadata import EpisodeId, TrackId, UnsupportedId
from librespot.proto.context_track_pb2 import ContextTrack


class PlayableId:
    BASE62 = Base62.create_instance_with_inverted_character_set()

    @staticmethod
    def from_uri(uri: str) -> PlayableId:
        pass
        # if not PlayableId.is_supported(uri):
        #     return UnsupportedId(uri)

        # if TrackId._PATTERN.search(uri) is not None:
        #     return TrackId.from_uri(uri)
        # elif EpisodeId._PATTERN.search(uri) is not None:
        #     return EpisodeId.from_uri(uri)
        # else:
        #     raise TypeError("Unknown uri: {}".format(uri))

    @staticmethod
    def is_supported(uri: str):
        return not uri.startswith("spotify:local:") and \
            not uri == "spotify:delimiter" and \
            not uri == "spotify:meta:delimiter"

    @staticmethod
    def should_play(track: ContextTrack):
        return track.metadata_or_default

    def get_gid(self) -> bytes:
        pass

    def hex_id(self) -> str:
        pass

    def to_spotify_uri(self) -> str:
        pass
