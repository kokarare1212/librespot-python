import logging
import typing

import requests

from librespot.core.ApResolver import ApResolver
from librespot.metadata import AlbumId
from librespot.metadata import ArtistId
from librespot.metadata import EpisodeId
from librespot.metadata import ShowId
from librespot.metadata import TrackId
from librespot.proto import Connect_pb2
from librespot.proto import Metadata_pb2
from librespot.standard import Closeable


class ApiClient(Closeable):
    _LOGGER: logging = logging.getLogger(__name__)
    _session = None
    _baseUrl: str = None

    def __init__(self, session):
        self._session = session
        self._baseUrl = "https://{}".format(ApResolver.get_random_spclient())

    def build_request(
        self,
        method: str,
        suffix: str,
        headers: typing.Union[None, typing.Dict[str, str]],
        body: typing.Union[None, bytes],
    ) -> requests.PreparedRequest:
        request = requests.PreparedRequest()
        request.method = method
        request.data = body
        request.headers = {}
        if headers is not None:
            request.headers = headers
        request.headers["Authorization"] = "Bearer {}".format(
            self._session.tokens().get("playlist-read"))
        request.url = self._baseUrl + suffix
        return request

    def send(
        self,
        method: str,
        suffix: str,
        headers: typing.Union[None, typing.Dict[str, str]],
        body: typing.Union[None, bytes],
    ) -> requests.Response:
        resp = self._session.client().send(
            self.build_request(method, suffix, headers, body))
        return resp

    def put_connect_state(self, connection_id: str,
                          proto: Connect_pb2.PutStateRequest) -> None:
        resp = self.send(
            "PUT",
            "/connect-state/v1/devices/{}".format(self._session.device_id()),
            {
                "Content-Type": "application/protobuf",
                "X-Spotify-Connection-Id": connection_id,
            },
            proto.SerializeToString(),
        )

        if resp.status_code == 413:
            self._LOGGER.warning(
                "PUT state payload is too large: {} bytes uncompressed.".
                format(len(proto.SerializeToString())))
        elif resp.status_code != 200:
            self._LOGGER.warning("PUT state returned {}. headers: {}".format(
                resp.status_code, resp.headers))

    def get_metadata_4_track(self, track: TrackId) -> Metadata_pb2.Track:
        resp = self.send("GET", "/metadata/4/track/{}".format(track.hex_id()),
                         None, None)
        ApiClient.StatusCodeException.check_status(resp)

        body = resp.content
        if body is None:
            raise RuntimeError()
        proto = Metadata_pb2.Track()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_episode(self, episode: EpisodeId) -> Metadata_pb2.Episode:
        resp = self.send("GET",
                         "/metadata/4/episode/{}".format(episode.hex_id()),
                         None, None)
        ApiClient.StatusCodeException.check_status(resp)

        body = resp.content
        if body is None:
            raise IOError()
        proto = Metadata_pb2.Episode()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_album(self, album: AlbumId) -> Metadata_pb2.Album:
        resp = self.send("GET", "/metadata/4/album/{}".format(album.hex_id()),
                         None, None)
        ApiClient.StatusCodeException.check_status(resp)

        body = resp.content
        if body is None:
            raise IOError()
        proto = Metadata_pb2.Album()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_artist(self, artist: ArtistId) -> Metadata_pb2.Artist:
        resp = self.send("GET",
                         "/metadata/4/artist/{}".format(artist.hex_id()), None,
                         None)
        ApiClient.StatusCodeException.check_status(resp)

        body = resp.content
        if body is None:
            raise IOError()
        proto = Metadata_pb2.Artist()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_show(self, show: ShowId) -> Metadata_pb2.Show:
        resp = self.send("GET", "/metadata/4/show/{}".format(show.hex_id()),
                         None, None)
        ApiClient.StatusCodeException.check_status(resp)

        body = resp.content
        if body is None:
            raise IOError()
        proto = Metadata_pb2.Show()
        proto.ParseFromString(body)
        return proto

    class StatusCodeException(IOError):
        code: int

        def __init__(self, resp: requests.Response):
            super().__init__(resp.status_code)
            self.code = resp.status_code

        @staticmethod
        def check_status(resp: requests.Response) -> None:
            if resp.status_code != 200:
                raise ApiClient.StatusCodeException(resp)
