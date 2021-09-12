from __future__ import annotations
from librespot.core import ApResolver
from librespot.metadata import AlbumId, ArtistId, EpisodeId, ShowId, TrackId
from librespot.proto import Connect_pb2 as Connect, Metadata_pb2 as Metadata
from librespot.structure import Closeable
import logging
import requests
import typing

if typing.TYPE_CHECKING:
    from librespot.core import Session
