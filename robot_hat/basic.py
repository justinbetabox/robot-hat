#!/usr/bin/env python3
"""
BasicClass: provides integrated logging functionality with configurable debug levels.
"""
import logging
from typing import Union, Optional, Dict, List


class BasicClass:
    """
    A base class for other classes, offering a named logger and debug-level control.
    """
    DEBUG_LEVELS: Dict[str, int] = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL,
    }
    DEBUG_NAMES: List[str] = ['critical', 'error', 'warning', 'info', 'debug']

    def __init__(
        self,
        debug_level: Union[str, int] = 'warning',
        logger: Optional[logging.Logger] = None
    ) -> None:
        """
        Initialize the BasicClass, setting up a logger and debug level.

        :param debug_level: Debug level name or index.
        :param logger: Optional external logger instance.
        """
        self.logger: logging.Logger = logger or logging.getLogger(self.__class__.__name__)
        # Configure handler if none present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s\t[%(levelname)s]\t%(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        # Apply the requested debug level
        self.debug_level = debug_level

    @property
    def debug_level(self) -> str:
        """
        Get the current debug level name.

        :return: Debug level as a string.
        """
        return self._debug_level  # type: ignore

    @debug_level.setter
    def debug_level(self, debug: Union[str, int]) -> None:
        """
        Set the debug level, accepting either an integer index or level name.

        :param debug: Level name or index.
        :raises ValueError: If the provided value is invalid.
        """
        # Determine level name
        if isinstance(debug, int):
            if 0 <= debug < len(self.DEBUG_NAMES):
                level_name: str = self.DEBUG_NAMES[debug]
            else:
                raise ValueError(f"Integer debug value must be between 0 and {len(self.DEBUG_NAMES)-1}.")
        elif isinstance(debug, str):
            if debug in self.DEBUG_NAMES:
                level_name = debug
            else:
                valid = ', '.join(self.DEBUG_NAMES)
                raise ValueError(f"String debug value must be one of: {valid}")
        else:
            raise ValueError("Debug value must be an integer or string.")

        # Apply to logger
        self._debug_level = level_name
        level = self.DEBUG_LEVELS[level_name]
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)
        self.logger.debug(f"Set logging level to [{level_name}]")
