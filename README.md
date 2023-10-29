![License](https://img.shields.io/github/license/kokarare1212/librespot-python.svg)
![Stars](https://img.shields.io/github/stars/kokarare1212/librespot-python.svg)
![Forks](https://img.shields.io/github/forks/kokarare1212/librespot-python.svg)
[![DeepSource](https://deepsource.io/gh/kokarare1212/librespot-python.svg/?label=active+issues&show_trend=true)](https://deepsource.io/gh/kokarare1212/librespot-python/?ref=repository-badge)

![Counter](https://count.getloli.com/get/@librespot-python?theme=moebooru)

# Librespot-Python

Open Source Spotify Client

## Support Project
If you find our project useful and want to support its development, please consider making a donation. Your contribution will help us maintain and improve the project, ensuring that it remains free and accessible to everyone.<br><br>
[![GitHub Sponsor](https://img.shields.io/github/sponsors/kokarare1212?label=GitHub%20Sponsor&logo=GitHub)](https://github.com/sponsors/kokarare1212)
[![Liberapay receiving](https://img.shields.io/liberapay/receives/kokarare1212?label=Liberapay&logo=Liberapay)](https://liberapay.com/kokarare1212/)

## About The Project

This project was developed to make the music streaming service Spotify available
on any device.

## Attention!

This repository has been completely rewritten from the transplant.<br>
There may be some functions that are not implemented yet.<br>
If so, please feel free to open an issue.<br>

## Note

It is still in the idea stage, so there is a possibility of unintended behavior
or major specification changes.<br>
We **DO NOT** encourage piracy and **DO NOT** support any form of downloader/recorder designed with the help of this repository and in general anything that goes against the Spotify ToS.<br>
For other guidelines, please see [CODE_OF_CONDUCT.md](https://github.com/kokarare1212/librespot-python/blob/main/CODE_OF_CONDUCT.md).<br>

## Getting Started

### Prerequisites

- [Python](https://python.org/)

### Installation

Stable Version

```commandline
pip install librespot
```

Snapshot Version \***Recommended**

```commandline
pip install git+https://github.com/kokarare1212/librespot-python
```

## Usage

### Use Zeroconf for Login

```python
from librespot.zeroconf import ZeroconfServer

zeroconf = ZeroconfServer.Builder().create()
```

### Get Spotify's OAuth token

```python
from librespot.core import Session


session = Session.Builder() \
    .user_pass("Username", "Password") \
    .create()

access_token = session.tokens().get("playlist-read")
```

### Get Music Stream

*Currently, music streaming is supported, but it may cause unintended behavior.<br>

```python
from librespot.core import Session
from librespot.metadata import TrackId
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality

session = Session.Builder() \
    .user_pass("Username", "Password") \
    .create()

track_id = TrackId.from_uri("spotify:track:xxxxxxxxxxxxxxxxxxxxxx")
stream = session.content_feeder().load(track_id, VorbisOnlyAudioQuality(AudioQuality.VERY_HIGH), False, None)
# stream.input_stream.stream().read() to get one byte of the music stream.
```

Other uses are
[examples](https://github.com/kokarare1212/librespot-python/tree/main/examples)
or read [this document](https://librespot-python.rtfd.io) for detailed
specifications.

## Debug

To display the debug information, you need to inject the following code at the
top of the code.

```python
import logging


logging.basicConfig(level=logging.DEBUG)
```

## Contributing

Pull requests are welcome.

## License

Distributed under the Apache-2.0 License. See
[LICENSE.txt](https://github.com/kokarare1212/librespot-python/blob/main/LICENSE.txt)
for more information.

## Related Projects

- [Librespot](https://github.com/librespot-org/librespot) (Concept)
- [Librespot-Java](https://github.com/librespot-org/librespot-java) (Core)
