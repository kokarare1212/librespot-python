from __future__ import annotations
from librespot.audio import SuperAudioFormat
from librespot.audio.decoders import AudioQuality
from librespot.proto import Metadata_pb2 as Metadata
from librespot.structure import AudioQualityPicker
import logging
import typing


class VorbisOnlyAudioQuality(AudioQualityPicker):
    logger = logging.getLogger("Librespot:Player:VorbisOnlyAudioQuality")
    preferred: AudioQuality

    def __init__(self, preferred: AudioQuality):
        self.preferred = preferred

    @staticmethod
    def get_vorbis_file(files: typing.List[Metadata.AudioFile]):
        for file in files:
            if hasattr(file, "format") and SuperAudioFormat.get(file.format) == SuperAudioFormat.VORBIS:
                return file
        return None

    def get_file(self, files: typing.List[Metadata.AudioFile]):
        matches: typing.List[Metadata.AudioFile] = self.preferred.get_matches(files)
        vorbis: Metadata.AudioFile = VorbisOnlyAudioQuality.get_vorbis_file(matches)
        if vorbis is None:
            vorbis: Metadata.AudioFile = VorbisOnlyAudioQuality.get_vorbis_file(files)
            if vorbis is not None:
                self.logger.warning("Using {} because preferred {} couldn't be found."
                                    .format(vorbis.format, self.preferred))
            else:
                self.logger.fatal("Couldn't find any Vorbis file, available: {}")
        return vorbis
