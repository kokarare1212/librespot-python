from __future__ import annotations
from librespot.audio import NormalizationData, PlayableContentFeeder, HaltListener
from librespot.common import Utils
from librespot.core import Session
from librespot.proto import Metadata, StorageResolve
import logging
import random
import time
import typing


class CdnFeedHelper:
    _LOGGER: logging = logging.getLogger(__name__)

    @staticmethod
    def get_url(resp: StorageResolve.StorageResolveResponse) -> str:
        return random.choice(resp.cdnurl)

    @staticmethod
    def load_track(session: Session, track: Metadata.Track, file: Metadata.AudioFile,
                   resp_or_url: typing.Union[StorageResolve.StorageResolveResponse, str],
                   preload: bool, halt_listener: HaltListener)\
            -> PlayableContentFeeder.PlayableContentFeeder.LoadedStream:
        if type(resp_or_url) is str:
            url = resp_or_url
        else:
            url = CdnFeedHelper.get_url(resp_or_url)
        start = int(time.time() * 1000)
        key = session.audio_key().get_audio_key(track.gid, file.file_id)
        audio_key_time = int(time.time() * 1000) - start

        streamer = session.cdn().stream_file(file, key, url, halt_listener)
        input_stream = streamer.stream()
        normalization_data = NormalizationData.read(input_stream)
        if input_stream.skip(0xa7) != 0xa7:
            raise IOError("Couldn't skip 0xa7 bytes!")
        return PlayableContentFeeder.PlayableContentFeeder.LoadedStream(
            track, streamer, normalization_data,
            PlayableContentFeeder.PlayableContentFeeder.Metrics(
                file.file_id, preload, -1 if preload else audio_key_time))

    @staticmethod
    def load_episode_external(
        session: Session, episode: Metadata.Episode,
        halt_listener: HaltListener
    ) -> PlayableContentFeeder.PlayableContentFeeder.LoadedStream:
        resp = session.client().head(episode.external_url)

        if resp.status_code != 200:
            CdnFeedHelper._LOGGER.warning("Couldn't resolve redirect!")

        url = resp.url
        CdnFeedHelper._LOGGER.debug("Fetched external url for {}: {}".format(
            Utils.Utils.bytes_to_hex(episode.gid), url))

        streamer = session.cdn().stream_external_episode(
            episode, url, halt_listener)
        return PlayableContentFeeder.PlayableContentFeeder.LoadedStream(
            episode, streamer, None,
            PlayableContentFeeder.PlayableContentFeeder.Metrics(
                None, False, -1))

    @staticmethod
    def load_episode(
        session: Session, episode: Metadata.Episode, file: Metadata.AudioFile,
        resp_or_url: typing.Union[StorageResolve.StorageResolveResponse,
                                  str], halt_listener: HaltListener
    ) -> PlayableContentFeeder.PlayableContentFeeder.LoadedStream:
        if type(resp_or_url) is str:
            url = resp_or_url
        else:
            url = CdnFeedHelper.get_url(resp_or_url)
        start = int(time.time() * 1000)
        key = session.audio_key().get_audio_key(episode.gid, file.file_id)
        audio_key_time = int(time.time() * 1000) - start

        streamer = session.cdn().stream_file(file, key, url, halt_listener)
        input_stream = streamer.stream()
        normalization_data = NormalizationData.read(input_stream)
        if input_stream.skip(0xa7) != 0xa7:
            raise IOError("Couldn't skip 0xa7 bytes!")
        return PlayableContentFeeder.PlayableContentFeeder.LoadedStream(
            episode, streamer, normalization_data,
            PlayableContentFeeder.PlayableContentFeeder.Metrics(
                file.file_id, False, audio_key_time))
