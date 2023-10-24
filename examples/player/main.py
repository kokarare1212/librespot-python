import os
import platform
import re
import subprocess
import time

import requests

from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.core import Session
from librespot.metadata import TrackId

quality: AudioQuality = AudioQuality.VERY_HIGH
session: Session = None


def clear():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def client():
    global quality, session
    while True:
        clear()
        splash()
        cmd = input("Player >>> ")
        args = cmd.split(" ")
        if args[0] in ["exit", "quit"]:
            return
        if args[0] in ["p", "play"] and len(args) == 2:
            track_uri_search = re.search(
                r"^spotify:track:(?P<TrackID>[0-9a-zA-Z]{22})$", args[1])
            track_url_search = re.search(
                r"^(https?://)?open\.spotify\.com/track/(?P<TrackID>[0-9a-zA-Z]{22})(\?si=.+?)?$",
                args[1],
            )
            if track_uri_search is not None or track_url_search is not None:
                track_id_str = (track_uri_search
                                if track_uri_search is not None else
                                track_url_search).group("TrackID")
                play(track_id_str)
                wait()
        if args[0] in ["q", "quality"]:
            if len(args) == 1:
                print(f"Current Quality: {quality.name}")
                wait()
            elif len(args) == 2:
                if args[1] in ["normal", "96"]:
                    quality = AudioQuality.NORMAL
                elif args[1] in ["high", "160"]:
                    quality = AudioQuality.HIGH
                elif args[1] in ["veryhigh", "320"]:
                    quality = AudioQuality.VERY_HIGH
                print(f"Set Quality to {quality.name}")
                wait()
        if args[0] in ["s", "search"] and len(args) >= 2:
            token = session.tokens().get("user-read-email")
            resp = requests.get(
                "https://api.spotify.com/v1/search",
                {"limit": "5", "offset": "0", "q": cmd[2:], "type": "track"},
                headers={"Authorization": f"Bearer {token}"},
            )
            tracks = resp.json()["tracks"]["items"]
            for i, track in enumerate(tracks, start=1):
                print("%d, %s | %s" % (
                    i,
                    track["name"],
                    ",".join([artist["name"] for artist in track["artists"]]),
                ))
            position = -1
            while True:
                num_str = input("Select [1-5]: ")
                if num_str in ["exit", "quit"]:
                    return
                try:
                    num = int(num_str)
                except ValueError:
                    continue
                if num in range(1, 5, 1):
                    position = num - 1
                    break
            play(tracks[position]["id"])
            wait()


def login():
    global session

    if os.path.isfile("credentials.json"):
        try:
            session = Session.Builder().stored_file().create()
            return
        except RuntimeError:
            pass
    while True:
        user_name = input("UserName: ")
        password = input("Password: ")
        try:
            session = Session.Builder().user_pass(user_name, password).create()
            return
        except RuntimeError:
            pass


def play(track_id_str: str):
    track_id = TrackId.from_base62(track_id_str)
    stream = session.content_feeder().load(track_id,
                                           VorbisOnlyAudioQuality(quality),
                                           False, None)
    ffplay = subprocess.Popen(
        ["ffplay", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    while True:
        byte = stream.input_stream.stream().read(1)
        if byte == -1:
            return
        ffplay.stdin.write(byte)


def splash():
    print("=================================\n"
          "| Librespot-Python Player       |\n"
          "|                               |\n"
          "| by kokarare1212               |\n"
          "=================================\n\n\n")


def main():
    login()
    client()


def wait(seconds: int = 3):
    for i in range(seconds)[::-1]:
        print("\rWait for %d second(s)..." % (i + 1), end="")
        time.sleep(1)


if __name__ == "__main__":
    main()
