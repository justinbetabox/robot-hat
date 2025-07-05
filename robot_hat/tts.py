# robot_hat/tts.py
"""
Text-to-Speech (TTS) engine interface for Robot Hat.
Supports multiple backends (e.g., pico2wave, pyaudio).
"""
import subprocess
import os

class TTS:
    """TTS engine wrapper."""
    def __init__(self, engine: str = 'pico2wave'):
        self.engine = engine.replace('-', '_')

    def say(self, text: str) -> None:
        """
        Speak the given text using the selected TTS engine.
        """
        # Dynamically dispatch to the appropriate method, avoiding eval
        method_name = self.engine
        if not hasattr(self, method_name):
            raise AttributeError(f"TTS engine '{self.engine}' is not supported.")
        method = getattr(self, method_name)
        method(text)

    def pico2wave(self, text: str):
        """Speak via the pico2wave CLI and aplay."""
        wav = '/tmp/tts.wav'
        subprocess.run(['pico2wave', '-w', wav, text], check=True)
        subprocess.run(['aplay', wav], check=True)
        os.remove(wav)

    def pyaudio(self, text: str):
        """Speak via PyAudio streaming (needs pyaudio installed)."""
        import pyaudio
        import wave
        # assume pre-recorded WAV for brevity
        wav = '/tmp/tts.wav'
        subprocess.run(['pico2wave', '-w', wav, text], check=True)
        wf = wave.open(wav, 'rb')
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pa.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )
        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)
        stream.stop_stream()
        stream.close()
        pa.terminate()
        os.remove(wav)