from __future__ import annotations
from librespot import Version
from librespot.audio.decoders import AudioQuality
from librespot.core import Session
from librespot.mercury import MercuryRequests
from librespot.proto import Connect_pb2 as Connect
from librespot.structure import Closeable, MessageListener, RequestListener
import concurrent.futures
import logging
import typing
import urllib.parse


class DeviceStateHandler(Closeable, MessageListener, RequestListener):
    logger = logging.getLogger("Librespot:DeviceStateHandler")
    __closing = False
    __connection_id: str = None
    __device_info: Connect.DeviceInfo
    __put_state: Connect.PutStateRequest
    __put_state_worker = concurrent.futures.ThreadPoolExecutor()
    __session: Session

    def __init__(self, session: Session, conf: PlayerConfiguration):
        self.__session = session
        self.__device_info = self.initialize_device_info(session, conf)
        self.__put_state = Connect.PutStateRequest(
            device=Connect.Device(device_info=self.__device_info, ),
            member_type=Connect.MemberType.CONNECT_STATE,
        )
        self.__session.dealer().add_message_listener(self, [
            "hm://pusher/v1/connections/",
            "hm://connect-state/v1/connect/volume",
            "hm://connect-state/v1/cluster"
        ])
        self.__session.dealer().add_request_listener(self,
                                                     "hm://connect-state/v1/")

    def close(self) -> None:
        self.__closing = True
        self.__session.dealer().remove_message_listener(self)
        self.__session.dealer().remove_request_listener(self)
        self.__put_state_worker.shutdown()

    def initialize_device_info(self, session: Session,
                               conf: PlayerConfiguration) -> Connect.Device:
        return Connect.DeviceInfo(
            can_play=True,
            capabilities=Connect.Capabilities(
                can_be_player=True,
                command_acks=True,
                is_controllable=True,
                is_observable=True,
                gaia_eq_connect_id=True,
                needs_full_player_state=False,
                supported_types=["audio/episode", "audio/track"],
                supports_command_request=True,
                supports_gzip_pushes=True,
                supports_logout=True,
                supports_playlist_v2=True,
                supports_rename=False,
                supports_transfer_command=True,
                volume_steps=conf.volume_steps,
            ),
            client_id=MercuryRequests.keymaster_client_id,
            device_id=session.device_id(),
            device_software_version=Version.version_string(),
            device_type=session.device_type(),
            name=session.device_name(),
            spirc_version="3.2.6",
            volume=conf.initial_volume,
        )

    def put_connect_state(self, request: Connect.PutStateRequest):
        self.__session.api().put_connect_state(self.__connection_id, request)
        self.logger.info("Put state. [ts: {}, connId: {}, reason: {}]".format(
            request.client_side_timestamp, self.__connection_id,
            request.put_state_reason))

    def update_connection_id(self, newer: str) -> None:
        newer = urllib.parse.unquote(newer)
        if self.__connection_id is None or self.__connection_id != newer:
            self.__connection_id = newer
            self.logger.debug(
                "Updated Spotify-Connection-Id: {}".format(newer))


class Player:
    volume_max = 65536
    __conf: PlayerConfiguration
    __session: Session
    __state: StateWrapper

    def __init__(self, conf: PlayerConfiguration, session: Session):
        self.__conf = conf
        self.__session = session

    def init_state(self) -> None:
        self.__state = StateWrapper(self.__session, self, self.__conf)


class PlayerConfiguration:
    # Audio
    preferred_quality: AudioQuality
    enable_normalisation: bool
    normalisation_pregain: float
    autoplay_enabled: bool
    crossfade_duration: int
    preload_enabled: bool

    # Volume
    initial_volume: int
    volume_steps: int

    def __init__(
        self,
        preferred_quality: AudioQuality,
        enable_normalisation: bool,
        normalisation_pregain: float,
        autoplay_enabled: bool,
        crossfade_duration: int,
        preload_enabled: bool,
        initial_volume: int,
        volume_steps: int,
    ):
        self.preferred_quality = preferred_quality
        self.enable_normalisation = enable_normalisation
        self.normalisation_pregain = normalisation_pregain
        self.autoplay_enabled = autoplay_enabled
        self.crossfade_duration = crossfade_duration
        self.preload_enabled = preload_enabled
        self.initial_volume = initial_volume
        self.volume_steps = volume_steps

    class Builder:
        preferred_quality: AudioQuality = AudioQuality.NORMAL
        enable_normalisation: bool = True
        normalisation_pregain: float = 3.0
        autoplay_enabled: bool = True
        crossfade_duration: int = 0
        preload_enabled: bool = True

        # Volume
        initial_volume: int = 65536
        volume_steps: int = 64

        def set_preferred_quality(
                self, preferred_quality: AudioQuality) -> __class__:
            self.preferred_quality = preferred_quality
            return self

        def set_enable_normalisation(self,
                                     enable_normalisation: bool) -> __class__:
            self.enable_normalisation = enable_normalisation
            return self

        def set_normalisation_pregain(
                self, normalisation_pregain: float) -> __class__:
            self.normalisation_pregain = normalisation_pregain
            return self

        def set_autoplay_enabled(self, autoplay_enabled: bool) -> __class__:
            self.autoplay_enabled = autoplay_enabled
            return self

        def set_crossfade_duration(self, crossfade_duration: int) -> __class__:
            self.crossfade_duration = crossfade_duration
            return self

        def set_preload_enabled(self, preload_enabled: bool) -> __class__:
            self.preload_enabled = preload_enabled
            return self

        def build(self) -> PlayerConfiguration:
            return PlayerConfiguration(
                self.preferred_quality,
                self.enable_normalisation,
                self.normalisation_pregain,
                self.autoplay_enabled,
                self.crossfade_duration,
                self.preload_enabled,
                self.initial_volume,
                self.volume_steps,
            )


class StateWrapper(MessageListener):
    __conf: PlayerConfiguration
    __device: DeviceStateHandler
    __player: Player
    __session: Session

    def __init__(self, session: Session, player: Player,
                 conf: PlayerConfiguration):
        self.__session = session
        self.__player = player
        self.__device = DeviceStateHandler(session, conf)
        self.__conf = conf
        session.dealer().add_message_listener(self, [
            "spotify:user:attributes:update", "hm://playlist/",
            "hm://collection/collection/" + session.username() + "/json"
        ])

    def on_message(self, uri: str, headers: typing.Dict[str, str],
                   payload: bytes):
        pass
