import os
import re
import socket
import threading

from librespot.audio.decoders import AudioQuality
from librespot.core import Session
from librespot.metadata import TrackId
from librespot.player.codecs import VorbisOnlyAudioQuality

session: Session
sock: socket


def handler(client: socket.socket, address: str):
    req_raw = client.recv(1024 * 1024)
    if len(req_raw) == 0:
        return
    req_arr = req_raw.split(b"\r\n")
    req_http_raw = req_arr[0]
    req_http_arr = req_http_raw.split(b" ")
    req_method = req_http_arr[0]
    req_uri = req_http_arr[1]
    req_http_version = req_http_arr[2]
    status, headers, content, manually = response(client, req_uri.decode())
    if not manually:
        client.send(req_http_version + b" " + status.encode() + b"\r\n")
        client.send(b"Access-Control-Allow-Origin: *\r\n")
        for header in headers:
            client.send(header.encode() + "\r\n")
        client.send(b"\r\n")
        client.send(content)
    client.close()


class HttpCode:
    http_200 = "200 OK"
    http_204 = "204 No Content"
    http_400 = "400 Bad Request"
    http_403 = "403 Forbidden"
    http_404 = "404 Not Found"
    http_500 = "500 Internal Server Error"


def main():
    global session, sock
    session = None
    if os.path.isfile("credentials.json"):
        try:
            session = Session.Builder().stored_file().create()
        except RuntimeError:
            pass
    if session is None or not session.is_valid():
        username = input("Username: ")
        password = input("Password: ")
        session = Session.Builder().user_pass(username, password).create()
    if not session.is_valid():
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 8080))
    sock.listen(5)
    while True:
        threading.Thread(target=handler, args=sock.accept()).start()


def response(client: socket.socket, uri: str) -> tuple[str, list, bytes, bool]:
    if re.search(r"^/audio/track/([0-9a-zA-Z]{22})$", uri) is not None:
        track_id_search = re.search(r"^/audio/track/(?P<TrackID>[0-9a-zA-Z]{22})$", uri)
        track_id_str = track_id_search.group("TrackID")
        track_id = TrackId.from_base62(track_id_str)
        stream = session.content_feeder().load(
            track_id, VorbisOnlyAudioQuality(AudioQuality.VERY_HIGH), False, None
        )
        client.send(b"HTTP/1.0 200 OK\r\n")
        client.send(b"Access-Control-Allow-Origin: *\r\n")
        client.send(b"Content-Type: audio/ogg\r\n")
        client.send(b"\r\n")
        while True:
            byte = stream.input_stream.stream().read()
            if byte == -1:
                break
            client.send(bytes([byte]))
        return "", [], b"", True
    else:
        return HttpCode.http_404, [], HttpCode.http_404.encode(), False


if __name__ == "__main__":
    main()
