from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from librespot.proto import Metadata_pb2


class AudioQualityPicker:
    def get_file(self,
                 files: typing.List[Metadata_pb2.AudioFile]) -> Metadata_pb2.AudioFile:
        pass
