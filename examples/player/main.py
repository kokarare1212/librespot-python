import os
import platform
import re
import subprocess
import time

import requests
from requests.structures import CaseInsensitiveDict

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
        if args[0] == "exit" or args[0] == "quit":
            return
        if (args[0] == "p" or args[0] == "play") and len(args) == 2:
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
        if args[0] == "q" or args[0] == "quality":
            if len(args) == 1:
                print("Current Quality: " + quality.name)
                wait()
            elif len(args) == 2:
                if args[1] == "normal" or args[1] == "96":
                    quality = AudioQuality.NORMAL
                elif args[1] == "high" or args[1] == "160":
                    quality = AudioQuality.HIGH
                elif args[1] == "veryhigh" or args[1] == "320":
                    quality = AudioQuality.VERY_HIGH
                print("Set Quality to %s" % quality.name)
                wait()
        if (args[0] == "s" or args[0] == "search") and len(args) >= 2:
            token = session.tokens().get("user-read-email")
            resp = requests.get(
                "https://api.spotify.com/v1/search",
                {
                    "limit": "5",
                    "offset": "0",
                    "q": cmd[2:],
                    "type": "track"
                },
                headers=CaseInsensitiveDict({"Authorization": "Bearer %s" % token}),
            )
            i = 1
            tracks = resp.json()["tracks"]["items"]
            for track in tracks:
                print("%d, %s | %s" % (
                    i,
                    track["name"],
                    ",".join([artist["name"] for artist in track["artists"]]),
                ))
                i += 1
            position = -1
            while True:
                num_str = input("Select [1-5]: ")
                if num_str == "exit" or num_str == "quit":
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
