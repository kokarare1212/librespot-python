![License](https://img.shields.io/github/license/kokarare1212/librespot-python.svg?style=for-the-badge)
![Stars](https://img.shields.io/github/stars/kokarare1212/librespot-python.svg?style=for-the-badge)
![Forks](https://img.shields.io/github/forks/kokarare1212/librespot-python.svg?style=for-the-badge)
# Librespot-Python
Open Source Spotify Client
## About The Project
This project was developed to make the music streaming service Spotify available on any device.
## Note
It is still in the idea stage, so there is a possibility of unintended behavior or major specification changes.  
We **DO NOT** encourage piracy and **DO NOT** support any form of downloader/recorder designed with the help of this repository and in general anything that goes against the Spotify ToS.
## Getting Started
### Prerequisites
* [Python](https://python.org/)
### Installation
Stable Version
```commandline
pip install librespot
```
Snapshot Version
```commandline
pip install git+https://github.com/kokarare1212/librespot-python
```
## Usage
Get Spotify's OAuth token
```python
from librespot.core import Session


session = Session.Builder() \
    .user_pass("<Username>", "<Password>") \
    .create()

aceess_token = session.tokens().get("playlist-read")
```
Please read [this document](https://librespot-python.rtfd.io) for detailed specifications.
## Roadmap
Please read [ROADMAP.md](https://github.com/kokarare1212/librespot-python/blob/main/ROADMAP.md).
## License
Distributed under the Apache-2.0 License. See `LICENSE.txt` for more information.
## Related Projects
* [Librespot](https://github.com/librespot-org/librespot) (Concept)
* [Librespot-Java](https://github.com/librespot-org/librespot-java) (Core)
## Special thanks
Coming soon
