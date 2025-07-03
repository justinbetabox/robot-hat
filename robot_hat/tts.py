#!/usr/bin/env python3
from .basic import BasicClass
from .utils import is_installed, run_command
from .music import Music
from distutils.spawn import find_executable
from typing import Optional, Union, List

class TTS(BasicClass):
    """Text-to-Speech class"""

    _class_name: str = 'TTS'
    SUPPORTED_LANGUAGE: List[str] = [
        'en-US',
        'en-GB',
        'de-DE',
        'es-ES',
        'fr-FR',
        'it-IT',
    ]
    """Supported TTS languages for pico2wave"""

    ESPEAK: str = 'espeak'
    """espeak TTS engine"""
    ESPEAK_NG: str = 'espeak-ng'
    """espeak-ng TTS engine"""
    PICO2WAVE: str = 'pico2wave'
    """pico2wave TTS engine"""

    def __init__(self, engine: str = PICO2WAVE, lang: Optional[str] = None, *args, **kwargs) -> None:
        """
        Initialize TTS class.

        :param engine: TTS engine, TTS.PICO2WAVE, TTS.ESPEAK, or TTS.ESPEAK_NG
        :type engine: str
        :param lang: language to use
        :type lang: str, optional
        """
        super().__init__()  # Initialize BasicClass (sets up self.logger, etc.)
        self.engine: str = engine
        if engine in (self.ESPEAK, self.ESPEAK_NG):
            if not is_installed(engine):
                raise Exception(f"TTS engine: {engine} is not installed.")
            self._amp: int = 100
            self._speed: int = 175
            self._gap: int = 5
            self._pitch: int = 50
            self._lang: str = lang if lang is not None else "en-us"
            self._supported_lang: List[str] = _get_supported_lang_espeak(engine)
        elif engine == self.PICO2WAVE:
            if not is_installed("pico2wave"):
                raise Exception("TTS engine: pico2wave is not installed.")
            self._lang = lang if lang is not None else "en-US"
            self._supported_lang = self.SUPPORTED_LANGUAGE
        else:
            raise ValueError(f"Unsupported TTS engine: {engine}")

        self.logger.debug(f"TTS initialized using engine: {self.engine}, language: {self._lang}")

    def _check_executable(self, executable: str) -> bool:
        executable_path = find_executable(executable)
        return executable_path is not None

    def say(self, words: str) -> None:
        """
        Say words.

        :param words: Words to say.
        :type words: str
        """
        # Escape any single quotes in words.
        words = words.replace("'", "\\'")
        # Dynamically call the TTS engine method (e.g., self.espeak or self.pico2wave)
        eval(f"self.{self.engine.replace('-', '_')}('{words}')")

    def _espeak(self, engine: str, words: str) -> None:
        """
        Say words with espeak.

        :param engine: The espeak engine to use.
        :param words: Words to say.
        """
        self.logger.debug(f'{engine}: [{words}]')
        if not self._check_executable(engine):
            self.logger.debug(f'{engine} is busy. Pass')
            return

        cmd = (f'{engine} -v{self._lang} -a{self._amp} -s{self._speed} '
               f'-g{self._gap} -p{self._pitch} "{words}" --stdout | aplay 2>/dev/null & ')
        status, result = run_command(cmd)
        if len(result) != 0:
            raise Exception(f'tts-espeak:\n\t{result}')
        self.logger.debug(f'command: {cmd}')

    def espeak(self, words: str) -> None:
        self._espeak('espeak', words)

    def espeak_ng(self, words: str) -> None:
        self._espeak('espeak-ng', words)

    def pico2wave(self, words: str) -> None:
        """
        Say words with pico2wave.

        :param words: Words to say.
        :type words: str
        """
        self.logger.debug(f'pico2wave: [{words}]')
        if not self._check_executable('pico2wave'):
            self.logger.debug('pico2wave is busy. Pass')
            return

        cmd = f'pico2wave -l {self._lang} -w /tmp/tts.wav "{words}" && aplay /tmp/tts.wav 2>/dev/null & '
        status, result = run_command(cmd)
        if len(result) != 0:
            raise Exception(f'tts-pico2wave:\n\t{result}')
        self.logger.debug(f'command: {cmd}')

    def lang(self, *value: str) -> str:
        """
        Set or get language. Leave empty to get current language.

        :param value: Language string.
        :return: Current language.
        :rtype: str
        """
        if len(value) == 0:
            return self._lang
        elif len(value) == 1:
            v = value[0]
            if v in self._supported_lang:
                self._lang = v
                return self._lang
        raise ValueError(
            f'Argument "{value}" is not supported. Run tts.supported_lang() to get supported language types.'
        )

    def supported_lang(self) -> List[str]:
        """
        Get supported languages.

        :return: Supported languages.
        :rtype: list
        """
        return self._supported_lang

    def espeak_params(self, amp: Optional[int] = None, speed: Optional[int] = None,
                      gap: Optional[int] = None, pitch: Optional[int] = None) -> None:
        """
        Set espeak parameters.

        :param amp: Amplitude.
        :param speed: Speed.
        :param gap: Gap.
        :param pitch: Pitch.
        """
        amp = amp if amp is not None else self._amp
        speed = speed if speed is not None else self._speed
        gap = gap if gap is not None else self._gap
        pitch = pitch if pitch is not None else self._pitch

        if amp not in range(0, 200):
            raise ValueError(f'Amp should be in 0 to 200, not "{amp}"')
        if speed not in range(80, 260):
            raise ValueError(f'speed should be in 80 to 260, not "{speed}"')
        if pitch not in range(0, 99):
            raise ValueError(f'pitch should be in 0 to 99, not "{pitch}"')
        self._amp = amp
        self._speed = speed
        self._gap = gap
        self._pitch = pitch

def _get_supported_lang_espeak(name: str) -> List[str]:
    """
    Get supported languages for espeak.

    :param name: espeak command name.
    :return: List of supported languages.
    :rtype: list
    """
    status, result = run_command(f"{name} --voices")
    supported_lang: List[str] = []
    if not status:
        first = True
        for line in result.split('\n'):
            if first or not line:
                first = False
                continue
            # The language is assumed to be the second non-empty token on each line.
            lang = [v for v in line.split() if v][1]
            supported_lang.append(lang)
    return supported_lang