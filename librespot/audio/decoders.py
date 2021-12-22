from __future__ import annotations
from librespot.audio import SuperAudioFormat
from librespot.proto import Metadata_pb2 as Metadata
from librespot.proto.Metadata_pb2 import AudioFile
from librespot.structure import AudioQualityPicker
import enum
import logging
import typing


class AudioQuality(enum.Enum):
    NORMAL = 0x00
    HIGH = 0x01
    VERY_HIGH = 0x02

    @staticmethod
    def get_quality(audio_format: AudioFile.Format) -> AudioQuality:
        if audio_format in [
                AudioFile.MP3_96,
                AudioFile.OGG_VORBIS_96,
                AudioFile.AAC_24_NORM,
        ]:
            return AudioQuality.NORMAL
        if audio_format in [
                AudioFile.MP3_160,
                AudioFile.MP3_160_ENC,
                AudioFile.OGG_VORBIS_160,
                AudioFile.AAC_24,
        ]:
            return AudioQuality.HIGH
        if audio_format in [
                AudioFile.MP3_320,
                AudioFile.MP3_256,
                AudioFile.OGG_VORBIS_320,
                AudioFile.AAC_48,
        ]:
            return AudioQuality.VERY_HIGH
        raise RuntimeError("Unknown format: {}".format(format))

    def get_matches(self,
                    files: typing.List[AudioFile]) -> typing.List[AudioFile]:
        file_list = []
        for file in files:
            if hasattr(file, "format") and AudioQuality.get_quality(
                    file.format) == self:
                file_list.append(file)
        return file_list


class VorbisOnlyAudioQuality(AudioQualityPicker):
    logger = logging.getLogger("Librespot:Player:VorbisOnlyAudioQuality")
    preferred: AudioQuality

    def __init__(self, preferred: AudioQuality):
        self.preferred = preferred

    @staticmethod
    def get_vorbis_file(files: typing.List[Metadata.AudioFile]):
        for file in files:
            if file.HasField("format") and SuperAudioFormat.get(
                    file.format) == SuperAudioFormat.VORBIS:
                return file
        return None

    def get_file(self, files: typing.List[Metadata.AudioFile]):
        matches: typing.List[Metadata.AudioFile] = self.preferred.get_matches(
            files)
        vorbis: Metadata.AudioFile = VorbisOnlyAudioQuality.get_vorbis_file(
            matches)
        if vorbis is None:
            vorbis: Metadata.AudioFile = VorbisOnlyAudioQuality.get_vorbis_file(
                files)
            if vorbis is not None:
                self.logger.warning(
                    "Using {} because preferred {} couldn't be found.".format(
                        Metadata.AudioFile.Format.Name(vorbis.format),
                        self.preferred))
            else:
                self.logger.fatal(
                    "Couldn't find any Vorbis file, available: {}")
        return vorbis
