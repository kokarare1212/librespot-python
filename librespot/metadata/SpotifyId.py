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
