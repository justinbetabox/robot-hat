#!/usr/bin/env python3
from .basic import BasicClass
from .utils import enable_speaker, disable_speaker
import time
import threading
import pyaudio
import os
import struct
import math
from typing import Optional, Tuple, Union, List

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

    # MIDI-compatible note names (index corresponds to MIDI note number)
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
        Initialize Music. Configures the mixer, time signature, tempo, and key signature.
        """
        super().__init__()
        import warnings
        # Suppress pygame welcome message
        warnings_bk = warnings.filters
        warnings.filterwarnings("ignore")
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
        import pygame
        warnings.filters = warnings_bk

        self.pygame = pygame
        self.pygame.mixer.init()
        # Default time signature 4/4, tempo 120 bpm with quarter note beat, and key signature 0.
        self.time_signature(4, 4)
        self.tempo(120, self.QUARTER_NOTE)
        self.key_signature(0)
        enable_speaker()
        self.logger.debug("Music module initialized.")

    def time_signature(self, top: Optional[int] = None, bottom: Optional[int] = None) -> Tuple[int, int]:
        """
        Set or get the time signature.

        :param top: The numerator of the time signature.
        :param bottom: The denominator of the time signature.
        :return: A tuple (top, bottom) representing the time signature.
        """
        if top is None and bottom is None:
            return self._time_signature  # type: ignore
        if bottom is None:
            bottom = top  # type: ignore
        self._time_signature = (top, bottom)
        self.logger.debug(f"Time signature set to: {self._time_signature}")
        return self._time_signature

    def key_signature(self, key: Optional[Union[int, str]] = None) -> Union[int, None]:
        """
        Set or get the key signature.

        :param key: The key signature as an integer or a string (e.g. "##" for 2 sharps or "bbb" for 3 flats).
        :return: The current key signature as an integer.
        """
        if key is None:
            return self._key_signature  # type: ignore
        if isinstance(key, str):
            if "#" in key:
                key = len(key) * self.KEY_SIGNATURE_SHARP
            elif "b" in key:
                key = len(key) * self.KEY_SIGNATURE_FLAT
        self._key_signature = key
        self.logger.debug(f"Key signature set to: {self._key_signature}")
        return self._key_signature

    def tempo(self, tempo: Optional[float] = None, note_value: Optional[float] = None) -> Union[Tuple[float, float], None]:
        """
        Set or get the tempo (beats per minute) along with the note value for one beat.

        :param tempo: Beats per minute.
        :param note_value: The note value that corresponds to one beat (e.g., Music.QUARTER_NOTE).
        :return: A tuple (tempo, note_value) if setting; otherwise, the current tempo tuple.
        """
        if tempo is None and note_value is None:
            return self._tempo  # type: ignore
        if note_value is None:
            note_value = tempo  # type: ignore
        try:
            self._tempo = (tempo, note_value)  # type: ignore
            self.beat_unit = 60.0 / tempo  # seconds per beat at the given tempo
            self.logger.debug(f"Tempo set to: {self._tempo}, beat unit: {self.beat_unit}")
            return self._tempo
        except Exception as e:
            raise ValueError(f"tempo must be a number, got {tempo}") from e

    def beat(self, beat: float) -> float:
        """
        Calculate the delay (in seconds) for a given beat count based on the current tempo.

        :param beat: The beat count (can be fractional).
        :return: The delay in seconds for that beat.
        """
        delay = beat / self._tempo[1] * self.beat_unit  # type: ignore
        self.logger.debug(f"Calculated beat delay for {beat} beats: {delay} seconds")
        return delay

    def note(self, note: Union[str, int], natural: bool = False) -> float:
        """
        Get the frequency of a note.

        :param note: The note as a string (e.g., "A4") or its MIDI index.
        :param natural: If True, do not adjust the note by key signature.
        :return: Frequency of the note in Hertz.
        """
        if isinstance(note, str):
            if note in self.NOTES:
                note_index = self.NOTES.index(note)
            else:
                raise ValueError(f"Note {note} not found. Note must be in Music.NOTES")
        else:
            note_index = note
        if not natural:
            note_index += self.key_signature()  # type: ignore
            note_index = min(max(note_index, 0), len(self.NOTES) - 1)
        note_delta = note_index - self.NOTE_BASE_INDEX
        freq = self.NOTE_BASE_FREQ * (2 ** (note_delta / 12))
        self.logger.debug(f"Calculated frequency for note {note} (index {note_index}): {freq} Hz")
        return freq

    def sound_play(self, filename: str, volume: Optional[float] = None) -> None:
        """
        Play a sound effect from a file.

        :param filename: The sound effect file name.
        :param volume: Optional volume percentage (0-100).
        """
        sound = self.pygame.mixer.Sound(filename)
        if volume is not None:
            sound.set_volume(round(volume / 100.0, 2))
        duration = round(sound.get_length(), 2)
        self.logger.debug(f"Playing sound {filename} with duration {duration} seconds")
        sound.play()
        time.sleep(duration)

    def sound_play_threading(self, filename: str, volume: Optional[float] = None) -> None:
        """
        Play a sound effect in a separate thread.

        :param filename: The sound effect file name.
        :param volume: Optional volume percentage (0-100).
        """
        thread = threading.Thread(target=self.sound_play, kwargs={"filename": filename, "volume": volume})
        thread.start()
        self.logger.debug(f"Started sound_play thread for {filename}")

    def music_play(self, filename: str, loops: int = 1, start: float = 0.0, volume: Optional[float] = None) -> None:
        """
        Play a music file.

        :param filename: The music file name.
        :param loops: Number of loops (0 for infinite looping, 1 for play once, etc.).
        :param start: Start time in seconds.
        :param volume: Optional volume percentage (0-100).
        """
        if volume is not None:
            self.music_set_volume(volume)
        self.pygame.mixer.music.load(filename)
        self.pygame.mixer.music.play(loops, start)
        self.logger.debug(f"Started music play: {filename}, loops: {loops}, start: {start}")

    def music_set_volume(self, value: float) -> None:
        """
        Set the music volume.

        :param value: Volume percentage (0-100).
        """
        vol = round(value / 100.0, 2)
        self.pygame.mixer.music.set_volume(vol)
        self.logger.debug(f"Music volume set to: {vol}")

    def music_stop(self) -> None:
        """Stop the music."""
        self.pygame.mixer.music.stop()
        self.logger.debug("Music stopped.")

    def music_pause(self) -> None:
        """Pause the music."""
        self.pygame.mixer.music.pause()
        self.logger.debug("Music paused.")

    def music_resume(self) -> None:
        """Resume paused music."""
        self.pygame.mixer.music.unpause()
        self.logger.debug("Music resumed.")

    def music_unpause(self) -> None:
        """Unpause the music (alias for music_resume)."""
        self.music_resume()

    def sound_length(self, filename: str) -> float:
        """
        Get the duration of a sound effect.

        :param filename: The sound effect file name.
        :return: Duration in seconds.
        """
        sound = self.pygame.mixer.Sound(filename)
        length = round(sound.get_length(), 2)
        self.logger.debug(f"Sound length for {filename}: {length} seconds")
        return length

    def get_tone_data(self, freq: float, duration: float) -> bytes:
        """
        Generate tone data for a given frequency and duration.

        :param freq: Frequency in Hz.
        :param duration: Duration in seconds.
        :return: Packed binary tone data.
        """
        # Divide duration by 2 as per original design
        duration /= 2.0
        frame_count = int(self.RATE * duration)
        remainder_frames = frame_count % self.RATE
        wavedata: List[int] = []

        for i in range(frame_count):
            a = self.RATE / freq  # frames per wave
            b = i / a
            c = b * (2 * math.pi)
            d = math.sin(c) * 32767
            wavedata.append(int(d))

        wavedata.extend([0] * remainder_frames)
        number_of_bytes = str(len(wavedata))
        packed_data = struct.pack(number_of_bytes + 'h', *wavedata)
        self.logger.debug(f"Generated tone data: {len(packed_data)} bytes for freq {freq} Hz, duration {duration*2} sec")
        return packed_data

    def play_tone_for(self, freq: float, duration: float) -> None:
        """
        Play a tone for a specified duration.

        :param freq: Frequency in Hz.
        :param duration: Duration in seconds.
        """
        p = pyaudio.PyAudio()
        frames = self.get_tone_data(freq, duration)
        stream = p.open(format=self.FORMAT, channels=self.CHANNELS,
                        rate=self.RATE, output=True)
        stream.write(frames)
        stream.close()
        p.terminate()
        self.logger.debug(f"Played tone at {freq} Hz for {duration} sec")