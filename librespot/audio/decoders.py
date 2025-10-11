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
    LOSSLESS = 0x03

    @staticmethod
    def get_quality(audio_format: AudioFile.Format) -> AudioQuality:
        if audio_format in [
                AudioFile.MP3_96,
                AudioFile.OGG_VORBIS_96,
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
        if audio_format in [
                AudioFile.FLAC_FLAC,
                AudioFile.FLAC_FLAC_24BIT,
        ]:
            return AudioQuality.LOSSLESS
        raise RuntimeError("Unknown format: {}".format(audio_format))

    def get_matches(self,
                    files: typing.List[AudioFile]) -> typing.List[AudioFile]:
        file_list = []
        for file in files:
            if hasattr(file, "format") and AudioQuality.get_quality(
                    file.format) == self:
                file_list.append(file)
        return file_list


class FormatOnlyAudioQuality(AudioQualityPicker):
    # Generic quality picker; filters files by container format

    logger = logging.getLogger("Librespot:Player:FormatOnlyAudioQuality")
    preferred: AudioQuality
    format_filter: SuperAudioFormat

    def __init__(self, preferred: AudioQuality, format_filter: SuperAudioFormat):
        self.preferred = preferred
        self.format_filter = format_filter

    @staticmethod
    def get_file_by_format(files: typing.List[Metadata.AudioFile],
                           format_type: SuperAudioFormat) -> typing.Optional[Metadata.AudioFile]:
        for file in files:
            if file.HasField("format") and SuperAudioFormat.get(
                    file.format) == format_type:
                return file
        return None

    def get_file(self, files: typing.List[Metadata.AudioFile]) -> typing.Optional[Metadata.AudioFile]:
        quality_matches: typing.List[Metadata.AudioFile] = self.preferred.get_matches(files)

        selected_file = self.get_file_by_format(quality_matches, self.format_filter)

        if selected_file is None:
            # Try using any file matching the format, regardless of quality
            selected_file = self.get_file_by_format(files, self.format_filter)

            if selected_file is not None:
                # Found format match (different quality than preferred)
                self.logger.warning(
                    "Using {} format file with {} quality because preferred {} quality couldn't be found.".format(
                        self.format_filter.name,
                        AudioQuality.get_quality(selected_file.format).name,
                        self.preferred.name))
            else:
                available_formats = [SuperAudioFormat.get(f.format).name
                                   for f in files if f.HasField("format")]
                self.logger.fatal(
                    "Couldn't find any {} file. Available formats: {}".format(
                        self.format_filter.name,
                        ", ".join(set(available_formats)) if available_formats else "none"))

        return selected_file


# Backward-compatible wrapper classes

class VorbisOnlyAudioQuality(FormatOnlyAudioQuality):
    logger = logging.getLogger("Librespot:Player:VorbisOnlyAudioQuality")

    def __init__(self, preferred: AudioQuality):
        super().__init__(preferred, SuperAudioFormat.VORBIS)

    @staticmethod
    def get_vorbis_file(files: typing.List[Metadata.AudioFile]) -> typing.Optional[Metadata.AudioFile]:
        return FormatOnlyAudioQuality.get_file_by_format(files, SuperAudioFormat.VORBIS)

class LosslessOnlyAudioQuality(FormatOnlyAudioQuality):
    logger = logging.getLogger("Librespot:Player:LosslessOnlyAudioQuality")

    def __init__(self, preferred: AudioQuality):
        super().__init__(preferred, SuperAudioFormat.FLAC)

    @staticmethod
    def get_flac_file(files: typing.List[Metadata.AudioFile]) -> typing.Optional[Metadata.AudioFile]:
        return FormatOnlyAudioQuality.get_file_by_format(files, SuperAudioFormat.FLAC)
