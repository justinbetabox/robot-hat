#!/usr/bin/env python3
"""
Play music, sound effects, and tone control via PyAudio and pygame.
"""
import os
import time
import threading
import struct
import math
import logging
from typing import Optional, Union, Tuple, List, Any

import pyaudio
import pygame

from .basic import BasicClass
from .utils import enable_speaker, disable_speaker


class Music(BasicClass):
    """Play music, sound effects, and note control."""

    FORMAT: int = pyaudio.paInt16
    CHANNELS: int = 1
    RATE: int = 44100

    # Key signatures (sharps: positive, flats: negative)
    KEY_G_MAJOR: int = 1
    KEY_D_MAJOR: int = 2
    KEY_A_MAJOR: int = 3
    KEY_E_MAJOR: int = 4
    KEY_B_MAJOR: int = 5
    KEY_F_SHARP_MAJOR: int = 6
    KEY_C_SHARP_MAJOR: int = 7

    KEY_F_MAJOR: int = -1
    KEY_B_FLAT_MAJOR: int = -2
    KEY_E_FLAT_MAJOR: int = -3
    KEY_A_FLAT_MAJOR: int = -4
    KEY_D_FLAT_MAJOR: int = -5
    KEY_G_FLAT_MAJOR: int = -6
    KEY_C_FLAT_MAJOR: int = -7

    KEY_SIGNATURE_SHARP: int = 1
    KEY_SIGNATURE_FLAT: int = -1

    # Note durations
    WHOLE_NOTE: float = 1.0
    HALF_NOTE: float = 1/2
    QUARTER_NOTE: float = 1/4
    EIGHTH_NOTE: float = 1/8
    SIXTEENTH_NOTE: float = 1/16

    # Base note for frequency calculations (A4)
    NOTE_BASE_FREQ: float = 440.0
    NOTE_BASE_INDEX: int = 69

    # MIDI-compatible note names
    NOTES: List[Optional[str]] = [
        None, None, None, None, None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None, None, "A0", "A#0", "B0",
        "C1", "C#1", "D1", "D#1", "E1", "F1", "F#1", "G1", "G#1", "A1", "A#1", "B1",
        "C2", "C#2", "D2", "D#2", "E2", "F2", "F#2", "G2", "G#2", "A2", "A#2", "B2",
        "C3", "C#3", "D3", "D#3", "E3", "F3", "F#3", "G3", "G#3", "A3", "A#3", "B3",
        "C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4",
        "C5", "C#5", "D5", "D#5", "E5", "F5", "F#5", "G5", "G#5", "A5", "A#5", "B5",
        "C6", "C#6", "D6", "D#6", "E6", "F6", "F#6", "G6", "G#6", "A6", "A#6", "B6",
        "C7", "C#7", "D7", "D#7", "E7", "F7", "F#7", "G7", "G#7", "A7", "A#7", "B7",
        "C8"
    ]

    def __init__(self) -> None:
        """
        Initialize Music: mixer, tempo, key signature, and enable speaker.
        """
        super().__init__()
        # Suppress pygame welcome prompt
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
        pygame.mixer.init()
        # Default settings: 4/4 time, 120 bpm quarter-note, key 0
        self.time_signature(4, 4)
        self.tempo(120.0, self.QUARTER_NOTE)
        self.key_signature(0)
        enable_speaker()
        self.logger.debug("Music module initialized.")

    def time_signature(self, top: Optional[int] = None, bottom: Optional[int] = None) -> Tuple[int, int]:
        """
        Set or get the time signature.

        :param top: Numerator.
        :param bottom: Denominator.
        :return: (top, bottom)
        """
        if top is None and bottom is None:
            return self._time_signature  # type: ignore
        if bottom is None:
            bottom = top  # type: ignore
        self._time_signature = (top, bottom)  # type: ignore
        self.logger.debug(f"Time signature set to: {self._time_signature}")
        return self._time_signature

    def key_signature(self, key: Optional[Union[int, str]] = None) -> int:
        """
        Set or get key signature.

        :param key: Integer or string (# for sharps, b for flats).
        :return: Current key signature.
        """
        if key is None:
            return self._key_signature  # type: ignore
        if isinstance(key, str):
            if '#' in key:
                key = len(key) * self.KEY_SIGNATURE_SHARP
            elif 'b' in key:
                key = len(key) * self.KEY_SIGNATURE_FLAT
        self._key_signature = key  # type: ignore
        self.logger.debug(f"Key signature set to: {self._key_signature}")
        return self._key_signature

    def tempo(self, tempo: Optional[float] = None, note_value: Optional[float] = None) -> Tuple[float, float]:
        """
        Set or get tempo and beat unit.

        :param tempo: Beats per minute.
        :param note_value: Note value for one beat.
        :return: (tempo, note_value)
        """
        if tempo is None and note_value is None:
            return self._tempo  # type: ignore
        if note_value is None:
            note_value = tempo  # type: ignore
        self._tempo = (tempo, note_value)  # type: ignore
        self.beat_unit = 60.0 / tempo  # seconds per beat
        self.logger.debug(f"Tempo set to: {self._tempo}, beat unit: {self.beat_unit}")
        return self._tempo

    def beat(self, beat: float) -> float:
        """
        Calculate delay for given beats.

        :param beat: Beat count (can be fractional).
        :return: Delay in seconds.
        """
        delay = beat / self._tempo[1] * self.beat_unit  # type: ignore
        self.logger.debug(f"Beat delay for {beat}: {delay}s")
        return delay

    def note(self, note: Union[str, int], natural: bool = False) -> float:
        """
        Get frequency for a note.

        :param note: Note name or MIDI index.
        :param natural: If True, ignores key signature.
        :return: Frequency in Hz.
        """
        if isinstance(note, str):
            if note not in self.NOTES:
                raise ValueError(f"Note {note} not found")
            idx = self.NOTES.index(note)
        else:
            idx = note
        if not natural:
            idx += self.key_signature()  # type: ignore
            idx = max(0, min(idx, len(self.NOTES)-1))
        delta = idx - self.NOTE_BASE_INDEX
        freq = self.NOTE_BASE_FREQ * (2 ** (delta / 12))
        self.logger.debug(f"Note {note} frequency: {freq}Hz")
        return freq

    def sound_play(self, filename: str, volume: Optional[float] = None) -> None:
        """
        Play a sound file synchronously.

        :param filename: Path to sound file.
        :param volume: Volume (0-100).
        """
        sound = pygame.mixer.Sound(filename)
        if volume is not None:
            sound.set_volume(volume/100.0)
        length = sound.get_length()
        self.logger.debug(f"Playing {filename} for {length}s")
        sound.play()
        time.sleep(length)

    def sound_play_threading(self, filename: str, volume: Optional[float] = None) -> None:
        """
        Play a sound file in a separate thread.

        :param filename: Path to sound file.
        :param volume: Volume (0-100).
        """
        thread = threading.Thread(target=self.sound_play, args=(filename, volume))
        thread.start()
        self.logger.debug(f"Started thread for {filename}")

    def music_play(self, filename: str, loops: int = 1, start: float = 0.0, volume: Optional[float] = None) -> None:
        """
        Play music with optional looping.

        :param filename: Path to music file.
        :param loops: Number of loops (0 infinite).
        :param start: Start position in seconds.
        :param volume: Volume (0-100).
        """
        if volume is not None:
            self.music_set_volume(volume)
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play(loops, start)
        self.logger.debug(f"Music play: {filename}, loops={loops}, start={start}")

    def music_set_volume(self, value: float) -> None:
        """
        Set music playback volume.

        :param value: Volume (0-100).
        """
        pygame.mixer.music.set_volume(value/100.0)
        self.logger.debug(f"Music volume: {value}")

    def music_stop(self) -> None:
        """Stop music playback."""
        pygame.mixer.music.stop()
        self.logger.debug("Music stopped")

    def music_pause(self) -> None:
        """Pause music playback."""
        pygame.mixer.music.pause()
        self.logger.debug("Music paused")

    def music_resume(self) -> None:
        """Resume music playback."""
        pygame.mixer.music.unpause()
        self.logger.debug("Music resumed")

    def sound_length(self, filename: str) -> float:
        """
        Get length of a sound file.

        :param filename: Path to sound file.
        :return: Duration in seconds.
        """
        length = pygame.mixer.Sound(filename).get_length()
        self.logger.debug(f"Sound length for {filename}: {length}s")
        return length

    def get_tone_data(self, freq: float, duration: float) -> bytes:
        """
        Generate raw PCM tone data.

        :param freq: Frequency in Hz.
        :param duration: Duration in seconds.
        :return: PCM byte string.
        """
        half = duration/2.0
        frame_count = int(self.RATE * half)
        remainder = frame_count % self.RATE
        data: List[int] = []
        for i in range(frame_count):
            val = math.sin(2*math.pi*(i*self.RATE/freq)/self.RATE) * 32767
            data.append(int(val))
        data.extend([0]*remainder)
        packed = struct.pack(f'{len(data)}h', *data)
        self.logger.debug(f"Tone data {len(packed)} bytes for {freq}Hz, {duration}s")
        return packed

    def play_tone_for(self, freq: float, duration: float) -> None:
        """
        Play a generated tone for a duration.

        :param freq: Frequency in Hz.
        :param duration: Duration in seconds.
        """
        p = pyaudio.PyAudio()
        frames = self.get_tone_data(freq, duration)
        stream = p.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, output=True)
        stream.write(frames)
        stream.close()
        p.terminate()
        self.logger.debug(f"Played tone {freq}Hz for {duration}s")
