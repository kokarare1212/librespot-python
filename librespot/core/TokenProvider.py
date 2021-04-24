from __future__ import annotations
from librespot.core import Session, TimeProvider
from librespot.mercury import MercuryRequests
import logging
import typing


class TokenProvider:
    _LOGGER: logging = logging.getLogger(__name__)
    _TOKEN_EXPIRE_THRESHOLD = 10
    _session: Session = None
    _tokens: typing.List[TokenProvider.StoredToken] = []

    def __init__(self, session: Session):
        self._session = session

    def find_token_with_all_scopes(
            self, scopes: typing.List[str]) -> TokenProvider.StoredToken:
        for token in self._tokens:
            if token.has_scopes(scopes):
                return token

        # noinspection PyTypeChecker
        return None

    def get_token(self, *scopes) -> TokenProvider.StoredToken:
        scopes = list(scopes)
        if len(scopes) == 0:
            raise RuntimeError()

        token = self.find_token_with_all_scopes(scopes)
        if token is not None:
            if token.expired():
                self._tokens.remove(token)
            else:
                return token

        self._LOGGER.debug(
            "Token expired or not suitable, requesting again. scopes: {}, old_token: {}"
            .format(scopes, token))
        resp = self._session.mercury().send_sync_json(
            MercuryRequests.request_token(self._session.device_id(),
                                          ",".join(scopes)))
        token = TokenProvider.StoredToken(resp)

        self._LOGGER.debug(
            "Updated token successfully! scopes: {}, new_token: {}".format(
                scopes, token))
        self._tokens.append(token)

        return token

    def get(self, scope: str) -> str:
        return self.get_token(scope).access_token

    class StoredToken:
        expires_in: int
        access_token: str
        scopes: typing.List[str]
        timestamp: int

        def __init__(self, obj):
            self.timestamp = TimeProvider.TimeProvider().current_time_millis()
            self.expires_in = obj["expiresIn"]
            self.access_token = obj["accessToken"]
            self.scopes = obj["scope"]

        def expired(self) -> bool:
            return self.timestamp + (
                self.expires_in - TokenProvider._TOKEN_EXPIRE_THRESHOLD
            ) * 1000 < TimeProvider.TimeProvider().current_time_millis()

        def has_scope(self, scope: str) -> bool:
            for s in self.scopes:
                if s == scope:
                    return True

            return False

        def has_scopes(self, sc: typing.List[str]) -> bool:
            for s in sc:
                if not self.has_scope(s):
                    return False

            return True
