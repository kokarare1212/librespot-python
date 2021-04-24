from __future__ import annotations

import logging
import typing

from librespot.audio.format.AudioQualityPicker import AudioQualityPicker
from librespot.audio.format.SuperAudioFormat import SuperAudioFormat
from librespot.player.codecs.AudioQuality import AudioQuality
from librespot.proto import Metadata


class VorbisOnlyAudioQuality(AudioQualityPicker):
    _LOGGER: logging = logging.getLogger(__name__)
    preferred: AudioQuality

    def __init__(self, preferred: AudioQuality):
        self.preferred = preferred

    @staticmethod
    def get_vorbis_file(files: typing.List[Metadata.AudioFile]):
        for file in files:
            if hasattr(file, "format") and SuperAudioFormat.get(
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
                self._LOGGER.warning(
                    "Using {} because preferred {} couldn't be found.".format(
                        vorbis.format, self.preferred))
            else:
                self._LOGGER.fatal(
                    "Couldn't find any Vorbis file, available: {}")

        return vorbis
