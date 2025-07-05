# robot_hat/tts.py
"""
Text-to-Speech (TTS) engine interface for Robot Hat.
Supports multiple backends (e.g., pico2wave, pyaudio).
"""
import subprocess
import os
from typing import Callable, Any


class TTS:
    """TTS engine wrapper supporting multiple backends."""

    def __init__(self, engine: str = 'pico2wave') -> None:
        """
        Initialize TTS with chosen engine.

        :param engine: Engine name ('pico2wave' or 'pyaudio').
        """
        # Normalize engine name to valid method identifier
        self.engine: str = engine.replace('-', '_')

    def say(self, text: str) -> None:
        """
        Speak the given text using the selected TTS engine.

        :param text: Text to speak.
        :raises AttributeError: If the chosen engine is unsupported.
        """
        method_name: str = self.engine
        if not hasattr(self, method_name):
            raise AttributeError(f"TTS engine '{self.engine}' is not supported.")
        method: Callable[[str], Any] = getattr(self, method_name)
        method(text)

    def pico2wave(self, text: str) -> None:
        """
        Speak via the pico2wave CLI and aplay.

        :param text: Text to speak.
        """
        wav: str = '/tmp/tts.wav'
        subprocess.run(['pico2wave', '-w', wav, text], check=True)
        subprocess.run(['aplay', wav], check=True)
        os.remove(wav)

    def pyaudio(self, text: str) -> None:
        """
        Speak via PyAudio streaming (requires pyaudio installed).

        :param text: Text to speak.
        """
        import pyaudio
        import wave

        wav: str = '/tmp/tts.wav'
        # Generate WAV via pico2wave
        subprocess.run(['pico2wave', '-w', wav, text], check=True)
        # Play via PyAudio
        wf = wave.open(wav, 'rb')
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pa.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )
        data: bytes = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)
        stream.stop_stream()
        stream.close()
        pa.terminate()
        os.remove(wav)
