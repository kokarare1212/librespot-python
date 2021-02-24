from __future__ import annotations
from librespot.core import Session


class SearchManager:
    _BASE_URL: str = "hm://searchview/km/v4/search/"
    _session: Session

    def __init__(self, session: Session):
        self._session = session
