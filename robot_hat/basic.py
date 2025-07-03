#!/usr/bin/env python3
import logging
from typing import Union, Optional

class BasicClass:
    """
    A basic class for all classes with integrated logging functionality.
    """
    DEBUG_LEVELS = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL,
    }
    DEBUG_NAMES = ['critical', 'error', 'warning', 'info', 'debug']

    def __init__(self, debug_level: Union[str, int] = 'warning', logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the basic class with a logger and set the debug level.
        
        :param debug_level: Debug level, specified as an int (0-4) or string.
        :param logger: Optional external logger.
        """
        # Use provided logger or create one based on the class name.
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Add a handler only if the logger has none
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s\t[%(levelname)s]\t%(message)s")
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)
        
        # Set the logging level using the property setter.
        self.debug_level = debug_level

    @property
    def debug_level(self) -> str:
        """Get the current debug level."""
        return self._debug_level

    @debug_level.setter
    def debug_level(self, debug: Union[str, int]) -> None:
        """Set the debug level, accepting either an integer or string."""
        if isinstance(debug, int):
            if 0 <= debug < len(self.DEBUG_NAMES):
                self._debug_level = self.DEBUG_NAMES[debug]
            else:
                raise ValueError("Integer debug value must be between 0 and 4.")
        elif isinstance(debug, str):
            if debug in self.DEBUG_NAMES:
                self._debug_level = debug
            else:
                raise ValueError("String debug value must be one of: " + ", ".join(self.DEBUG_NAMES))
        else:
            raise ValueError("Debug value must be an integer or string.")

        level = self.DEBUG_LEVELS[self._debug_level]
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)
        self.logger.debug(f'Set logging level to [{self._debug_level}]')