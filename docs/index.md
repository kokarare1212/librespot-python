![](https://img.shields.io/github/license/kokarare1212/librespot-python.svg)
![](https://img.shields.io/github/stars/kokarare1212/librespot-python.svg)
![](https://img.shields.io/github/forks/kokarare1212/librespot-python.svg)
[![](https://deepsource.io/gh/kokarare1212/librespot-python.svg/?label=active+issues&show_trend=true)](https://deepsource.io/gh/kokarare1212/librespot-python/?ref=repository-badge)

# Get Started

## Contents

* [Get Started](index.md)
* [Supported Futures](supported.md)
* [API Reference](api.md)

## What's librespot-python?

librespot-python is a python port of Spotify's open source client library [librespot](https://github.com/librespot-org/librespot).

It was created to play Spotify on various platforms and devices.

## What do you need?

In order to develop with this library, you need to use Python.

Python can be downloaded from [the official website here](https://python.org/).

## Disclaimer

Please keep in mind that this library is not like Spotify approved.

Therefore, the worst that can happen is that you will be banned from Spotify.

Also, please keep in mind that this library is in alpha and may behave in unintended ways.

## Installation

You can download this library in the following way.  

Stable Version ***still not working.**

```commandline
pip install librespot
```

Snapshot Version ***Recommended**

```commandline
pip install git+https://github.com/kokarare1212/librespot-python
```

## Usage

### Get Spotify's OAuth token

```python
from librespot.core import Session


session = Session.Builder() \
    .user_pass("Username", "Password") \
    .create()

aceess_token = session.tokens().get("playlist-read")
```

### Get Music Stream

*Currently, music streaming is supported, but it may cause unintended behavior.

```python
from librespot.core import Session
from librespot.metadata import TrackId
from librespot.player.codecs import VorbisOnlyAudioQuality
from librespot.audio.decoders import AudioQuality

session = Session.Builder()
    .user_pass("Username", "Password")
    .create()

track_id = TrackId.from_uri("spotify:track:xxxxxxxxxxxxxxxxxxxxxx")
stream = session.content_feeder().load(track_id, VorbisOnlyAudioQuality(AudioQuality.AudioQuality.VERY_HIGH), False,
                                       None)
# stream.input_stream.stream().read() to get one byte of the music stream.
# ex: 1 (If there is no more voice data, -1 is received as the result.)
```

## Debug

To display the debug information, you need to inject the following code at the top of the code.

```python
import logging


logging.basicConfig(level=logging.DEBUG)
```