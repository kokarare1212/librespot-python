from librespot.proto import Metadata_pb2 as Metadata
import enum


class SuperAudioFormat(enum.Enum):
    MP3 = 0x00
    VORBIS = 0x01
    AAC = 0x02

    @staticmethod
    def get(audio_format: Metadata.AudioFile.Format):
        if audio_format in [
                Metadata.AudioFile.Format.OGG_VORBIS_96,
                Metadata.AudioFile.Format.OGG_VORBIS_160,
                Metadata.AudioFile.Format.OGG_VORBIS_320,
        ]:
            return SuperAudioFormat.VORBIS
        if audio_format in [
                Metadata.AudioFile.Format.MP3_256,
                Metadata.AudioFile.Format.MP3_320,
                Metadata.AudioFile.Format.MP3_160,
                Metadata.AudioFile.Format.MP3_96,
                Metadata.AudioFile.Format.MP3_160_ENC,
        ]:
            return SuperAudioFormat.MP3
        if audio_format in [
                Metadata.AudioFile.Format.AAC_24,
                Metadata.AudioFile.Format.AAC_48,
                Metadata.AudioFile.Format.AAC_24_NORM,
        ]:
            return SuperAudioFormat.AAC
        raise RuntimeError("Unknown audio format: {}".format(audio_format))
