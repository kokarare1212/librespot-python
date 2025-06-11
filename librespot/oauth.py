import base64
import logging
import random
import urllib
from hashlib import sha256
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from librespot.proto import Authentication_pb2 as Authentication
import requests


class OAuth:
    logger = logging.getLogger("Librespot:OAuth")
    __spotify_auth = "https://accounts.spotify.com/authorize?response_type=code&client_id=%s&redirect_uri=%s&code_challenge=%s&code_challenge_method=S256&scope=%s"
    __scopes = ["app-remote-control", "playlist-modify", "playlist-modify-private", "playlist-modify-public", "playlist-read", "playlist-read-collaborative", "playlist-read-private", "streaming", "ugc-image-upload", "user-follow-modify", "user-follow-read", "user-library-modify", "user-library-read", "user-modify", "user-modify-playback-state", "user-modify-private", "user-personalized", "user-read-birthdate", "user-read-currently-playing", "user-read-email", "user-read-play-history", "user-read-playback-position", "user-read-playback-state", "user-read-private", "user-read-recently-played", "user-top-read"]
    __spotify_token = "https://accounts.spotify.com/api/token"
    __spotify_token_data = {"grant_type": "authorization_code", "client_id": "", "redirect_uri": "", "code": "", "code_verifier": ""}
    __client_id = ""
    __redirect_url = ""
    __code_verifier = ""
    __code = ""
    __token = ""
    __server = None
    __oauth_url_callback = None

    def __init__(self, client_id, redirect_url, oauth_url_callback):
        self.__client_id = client_id
        self.__redirect_url = redirect_url
        self.__oauth_url_callback = oauth_url_callback

    def __generate_generate_code_verifier(self):
        possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        verifier = ""
        for i in range(128):
            verifier += possible[random.randint(0, len(possible) - 1)]
        return verifier

    def __generate_code_challenge(self, code_verifier):
        digest = sha256(code_verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')

    def get_auth_url(self):
        self.__code_verifier = self.__generate_generate_code_verifier()
        auth_url = self.__spotify_auth % (self.__client_id, self.__redirect_url, self.__generate_code_challenge(self.__code_verifier), "+".join(self.__scopes))
        if self.__oauth_url_callback:
            self.__oauth_url_callback(auth_url)
        return auth_url

    def set_code(self, code):
        self.__code = code

    def request_token(self):
        if not self.__code:
            raise RuntimeError("You need to provide a code before!")
        request_data = self.__spotify_token_data
        request_data["client_id"] = self.__client_id
        request_data["redirect_uri"] = self.__redirect_url
        request_data["code"] = self.__code
        request_data["code_verifier"] = self.__code_verifier
        request = requests.post(
            self.__spotify_token,
            data=request_data,
        )
        if request.status_code != 200:
            raise RuntimeError("Received status code %d: %s" % (request.status_code, request.reason))
        self.__token = request.json()["access_token"]

    def get_credentials(self):
        if not self.__token:
            raise RuntimeError("You need to request a token bore!")
        return Authentication.LoginCredentials(
            typ=Authentication.AuthenticationType.AUTHENTICATION_SPOTIFY_TOKEN,
            auth_data=self.__token.encode("utf-8")
        )

    class CallbackServer(HTTPServer):
        callback_path = None

        def __init__(self, server_address, RequestHandlerClass, callback_path, set_code):
            self.callback_path = callback_path
            self.set_code = set_code
            super().__init__(server_address, RequestHandlerClass)

    class CallbackRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if(self.path.startswith(self.server.callback_path)):
                query = urllib.parse.parse_qs(urlparse(self.path).query)
                if not query.__contains__("code"):
                    self.wfile.write(b"Request doesn't contain 'code'")
                    return
                self.server.set_code(query.get("code")[0])
                self.wfile.write(b"librespot-python received callback")
            pass

    def __start_server(self):
        try:
            self.__server.handle_request()
        except KeyboardInterrupt:
            return
        if not self.__code:
            self.__start_server()

    def run_callback_server(self):
        url = urlparse(self.__redirect_url)
        self.__server = self.CallbackServer(
            (url.hostname, url.port),
            self.CallbackRequestHandler,
            url.path,
            self.set_code
        )
        logging.info("OAuth: Waiting for callback on %s", url.hostname + ":" + str(url.port))
        self.__start_server()

    def flow(self):
        logging.info("OAuth: Visit in your browser and log in: %s ", self.get_auth_url())
        self.run_callback_server()
        self.request_token()
        return self.get_credentials()

    def __close(self):
        if self.__server:
            self.__server.shutdown()

