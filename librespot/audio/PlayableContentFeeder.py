from __future__ import annotations

from librespot.audio import GeneralAudioStream, HaltListener, NormalizationData
from librespot.audio.cdn import CdnFeedHelper
from librespot.audio.format import AudioQualityPicker
from librespot.common.Utils import Utils
from librespot.core import Session
from librespot.metadata.PlayableId import PlayableId
from librespot.metadata.TrackId import TrackId
from librespot.proto import Metadata, StorageResolve
import logging
import typing


class PlayableContentFeeder:
    _LOGGER: logging = logging.getLogger(__name__)
    STORAGE_RESOLVE_INTERACTIVE: str = "/storage-resolve/files/audio/interactive/{}"
    STORAGE_RESOLVE_INTERACTIVE_PREFETCH: str = "/storage-resolve/files/audio/interactive_prefetch/{}"
    session: Session

    def __init__(self, session: Session):
        self.session = session

    def pick_alternative_if_necessary(self, track: Metadata.Track):
        if len(track.file) > 0:
            return track

        for alt in track.alternative_list:
            if len(alt.file) > 0:
                pass

        return None

    def load(self, playable_id: PlayableId,
             audio_quality_picker: AudioQualityPicker, preload: bool,
             halt_listener: HaltListener):
        if type(playable_id) is TrackId:
            return self.load_track(playable_id, audio_quality_picker, preload,
                                   halt_listener)

    def resolve_storage_interactive(
            self, file_id: bytes,
            preload: bool) -> StorageResolve.StorageResolveResponse:
        resp = self.session.api().send(
            "GET", (self.STORAGE_RESOLVE_INTERACTIVE_PREFETCH
                    if preload else self.STORAGE_RESOLVE_INTERACTIVE).format(
                        Utils.bytes_to_hex(file_id)), None, None)
        if resp.status_code != 200:
            raise RuntimeError(resp.status_code)

        body = resp.content
        if body is None:
            RuntimeError("Response body is empty!")

        storage_resolve_response = StorageResolve.StorageResolveResponse()
        storage_resolve_response.ParseFromString(body)
        return storage_resolve_response

    def load_track(self, track_id_or_track: typing.Union[TrackId,
                                                         Metadata.Track],
                   audio_quality_picker: AudioQualityPicker, preload: bool,
                   halt_listener: HaltListener):
        if type(track_id_or_track) is TrackId:
            original = self.session.api().get_metadata_4_track(
                track_id_or_track)
            track = self.pick_alternative_if_necessary(original)
            if track is None:
                raise
        else:
            track = track_id_or_track
        file = audio_quality_picker.get_file(track.file)
        if file is None:
            self._LOGGER.fatal(
                "Couldn't find any suitable audio file, available")
            raise

        return self.load_stream(file, track, None, preload, halt_listener)

    def load_stream(self, file: Metadata.AudioFile, track: Metadata.Track,
                    episode: Metadata.Episode, preload: bool,
                    halt_lister: HaltListener):
        if track is None and episode is None:
            raise RuntimeError()

        resp = self.resolve_storage_interactive(file.file_id, preload)
        if resp.result == StorageResolve.StorageResolveResponse.Result.CDN:
            if track is not None:
                return CdnFeedHelper.load_track(self.session, track, file,
                                                resp, preload, halt_lister)
            return CdnFeedHelper.load_episode(self.session, episode, file,
                                              resp, preload, halt_lister)
        elif resp.result == StorageResolve.StorageResolveResponse.Result.STORAGE:
            if track is None:
                # return StorageFeedHelper
                pass
        elif resp.result == StorageResolve.StorageResolveResponse.Result.RESTRICTED:
            raise RuntimeError("Content is restricted!")
        elif resp.result == StorageResolve.StorageResolveResponse.Response.UNRECOGNIZED:
            raise RuntimeError("Content is unrecognized!")
        else:
            raise RuntimeError("Unknown result: {}".format(resp.result))

    class LoadedStream:
        episode: Metadata.Episode
        track: Metadata.Track
        input_stream: GeneralAudioStream
        normalization_data: NormalizationData
        metrics: PlayableContentFeeder.Metrics

        def __init__(self, track_or_episode: typing.Union[Metadata.Track,
                                                          Metadata.Episode],
                     input_stream: GeneralAudioStream,
                     normalization_data: NormalizationData,
                     metrics: PlayableContentFeeder.Metrics):
            if type(track_or_episode) is Metadata.Track:
                self.track = track_or_episode
                self.episode = None
            elif type(track_or_episode) is Metadata.Episode:
                self.track = None
                self.episode = track_or_episode
            else:
                raise TypeError()
            self.input_stream = input_stream
            self.normalization_data = normalization_data
            self.metrics = metrics

    class Metrics:
        file_id: str
        preloaded_audio_key: bool
        audio_key_time: int

        def __init__(self, file_id: bytes, preloaded_audio_key: bool,
                     audio_key_time: int):
            self.file_id = None if file_id is None else Utils.bytes_to_hex(
                file_id)
            self.preloaded_audio_key = preloaded_audio_key
            self.audio_key_time = audio_key_time

            if preloaded_audio_key and audio_key_time != -1:
                raise RuntimeError()
