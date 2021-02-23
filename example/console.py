from librespot.core import Session
from librespot.metadata import TrackId
from librespot.player.codecs import AudioQuality, VorbisOnlyAudioQuality
import logging
import os
import platform
import requests
import subprocess

logging.basicConfig(level=logging.DEBUG)


def streaming(session: Session, uri: str, quality: AudioQuality):
    stream = session.content_feeder().load(TrackId.from_uri(uri), VorbisOnlyAudioQuality(quality), False, None)
    process = subprocess.Popen(
        ["ffplay", "-autoexit", "-nodisp", "-loglevel", "quiet", "-"],
        stdin=subprocess.PIPE)
    while True:
        i = stream.input_stream.stream().read()
        if i == -1:
            process.kill()
            break
        process.stdin.write(bytes([i]))


def main():
    session = Session.Builder().stored().create()

    quality: AudioQuality = AudioQuality.AudioQuality.VERY_HIGH
    running: bool = True
    while running:
        try:
            command = input("Librespot >>> ")
            argv = command.split(" ")

            if argv[0] == "clear" or argv[0] == "cls":
                if platform.system() == "Windows":
                    os.system("cls")
                else:
                    os.system("clear")
                continue
            elif argv[0] == "play" or argv[0] == "p":
                try:
                    track = argv[1]
                except IndexError:
                    continue

                streaming(session, track, quality)
                continue
            elif argv[0] == "search" or argv[0] == "s":
                try:
                    keyword = argv[1]
                except IndexError:
                    continue
                access_token = session.tokens().get("playlist-read")
                resp = requests.get("https://api.spotify.com/v1/search?type=track&limit=5&q={}".format(keyword), headers={
                    "Authorization": "Bearer {}".format(access_token),
                    "Accept-Language": "ja"
                })
                obj = resp.json()
                i = 1
                for track in obj["tracks"]["items"]:
                    print("{}, {} - {}".format(i, track["name"], ",".join([artist["name"] for artist in track["artists"]])))
                    i += 1
                user_str = input("SELECT (1~5) | Librespot >>> ")
                try:
                    selected_number = int(user_str)
                except ValueError:
                    continue
                if selected_number not in range(1, 6):
                    continue
                streaming(session, obj["tracks"]["items"][selected_number - 1]["uri"], quality)
            elif argv[0] == "quality":
                try:
                    new_quality = argv[1]
                except IndexError:
                    print("Current Quality: {}".format(quality))
                    continue
                if new_quality.lower() == "very_high":
                    quality = AudioQuality.AudioQuality.VERY_HIGH
                elif new_quality.lower() == "high":
                    quality = AudioQuality.AudioQuality.HIGH
                elif new_quality.lower() == "normal":
                    quality = AudioQuality.AudioQuality.NORMAL
                else:
                    print("Unsupported Quality: {}".format(new_quality))
                continue
            elif argv[0] == "quit" or argv[0] == "q" or argv[0] == "exit":
                running = False
                session.close()
                continue
        except KeyboardInterrupt:
            running = False
            session.close()


if __name__ == "__main__":
    main()
