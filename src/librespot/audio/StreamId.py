from librespot.common.Utils import Utils
from librespot.proto import Metadata


class StreamId:
    file_id: bytes = None
    episode_gid: bytes = None

    def __init__(self,
                 file: Metadata.AudioFile = None,
                 episode: Metadata.Episode = None):
        if file is None and episode is None:
            return
        if file is not None:
            self.file_id = file.file_id
        if episode is not None:
            self.episode_gid = episode.gid

    def get_file_id(self):
        if self.file_id is None:
            raise RuntimeError("Not a file!")
        return Utils.bytes_to_hex(self.file_id)

    def is_episode(self):
        return self.episode_gid is not None

    def get_episode_gid(self):
        if self.episode_gid is None:
            raise RuntimeError("Not an episode!")
        return Utils.bytes_to_hex(self.episode_gid)
