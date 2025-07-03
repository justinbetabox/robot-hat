#!/usr/bin/env python3
from time import sleep
from robot_hat import Music, TTS
from os import geteuid

if geteuid() != 0:
    print("\033[0;33mThe program needs to be run using sudo, otherwise there may be no sound.\033[0m")

music = Music()
tts = TTS()

def main():
    music.music_set_volume(100)
    tts.lang("en-US")

    words = "Hello"
    print(words)
    tts.say(words)
    sleep(1)

if __name__ == "__main__":
    main()