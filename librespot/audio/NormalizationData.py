from __future__ import annotations
from librespot.standard import BytesInputStream, DataInputStream, InputStream
import logging
import math


class NormalizationData:
    _LOGGER: logging = logging.getLogger(__name__)
    track_gain_db: float
    track_peak: float
    album_gain_db: float
    album_peak: float

    def __init__(self, track_gain_db: float, track_peak: float,
                 album_gain_db: float, album_peak: float):
        self.track_gain_db = track_gain_db
        self.track_peak = track_peak
        self.album_gain_db = album_gain_db
        self.album_peak = album_peak

        self._LOGGER.debug(
            "Loaded normalization data, track_gain: {}, track_peak: {}, album_gain: {}, album_peak: {}"
            .format(track_gain_db, track_peak, album_gain_db, album_peak))

    @staticmethod
    def read(input_stream: InputStream) -> NormalizationData:
        data_input = DataInputStream(input_stream)
        data_input.mark(16)
        skip_bytes = data_input.skip_bytes(144)
        if skip_bytes != 144:
            raise IOError()

        data = bytearray(4 * 4)
        data_input.read_fully(data)
        data_input.reset()

        buffer = BytesInputStream(data, "<")
        return NormalizationData(buffer.read_float(), buffer.read_float(),
                                 buffer.read_float(), buffer.read_float())

    def get_factor(self, normalisation_pregain) -> float:
        normalisation_factor = float(
            math.pow(10, (self.track_gain_db + normalisation_pregain) / 20))
        if normalisation_factor * self.track_peak > 1:
            self._LOGGER.warning(
                "Reducing normalisation factor to prevent clipping. Please add negative pregain to avoid."
            )
            normalisation_factor = 1 / self.track_peak

        return normalisation_factor
