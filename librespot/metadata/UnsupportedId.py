from librespot.metadata import PlayableId


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
