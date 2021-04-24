from __future__ import annotations
from librespot.proto.Metadata import AudioFile
import enum
import typing


class AudioQuality(enum.Enum):
    NORMAL = 0x00
    HIGH = 0x01
    VERY_HIGH = 0x02

    @staticmethod
    def get_quality(audio_format: AudioFile.Format) -> AudioQuality:
        if audio_format == AudioFile.MP3_96 or \
                   audio_format == AudioFile.OGG_VORBIS_96 or \
                   audio_format == AudioFile.AAC_24_NORM:
            return AudioQuality.NORMAL
        if audio_format == AudioFile.MP3_160 or \
                        audio_format == AudioFile.MP3_160_ENC or \
                        audio_format == AudioFile.OGG_VORBIS_160 or \
                        audio_format == AudioFile.AAC_24:
            return AudioQuality.HIGH
        if audio_format == AudioFile.MP3_320 or \
                        audio_format == AudioFile.MP3_256 or \
                        audio_format == AudioFile.OGG_VORBIS_320 or \
                        audio_format == AudioFile.AAC_48:
            return AudioQuality.VERY_HIGH
        raise RuntimeError("Unknown format: {}".format(format))

    def get_matches(self, files: typing.List[AudioFile]) -> typing.List[AudioFile]:
        file_list = []
        for file in files:
            if hasattr(file, "format") and AudioQuality.get_quality(
                    file.format) == self:
                file_list.append(file)

        return file_list
