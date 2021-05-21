from __future__ import annotations
from librespot.audio.decoders import AudioQuality


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

    def __init__(self, preferred_quality: AudioQuality,
                 enable_normalisation: bool, normalisation_pregain: float,
                 autoplay_enabled: bool, crossfade_duration: int,
                 preload_enabled: bool, initial_volume: int,
                 volume_steps: int):
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

        def __init__(self):
            pass

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
                self.preferred_quality, self.enable_normalisation,
                self.normalisation_pregain, self.autoplay_enabled,
                self.crossfade_duration, self.preload_enabled,
                self.initial_volume, self.volume_steps)
