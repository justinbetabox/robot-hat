#!/usr/bin/env python3
from .basic import BasicClass
import gpiozero  # https://gpiozero.readthedocs.io/en/latest/installing.html
from gpiozero import OutputDevice, InputDevice, Button
from typing import Union, Optional, Dict, Any


class Pin(BasicClass):
    """Pin manipulation class"""

    OUT = 0x01
    """Pin mode output"""
    IN = 0x02
    """Pin mode input"""

    PULL_UP = 0x11
    """Pin internal pull up"""
    PULL_DOWN = 0x12
    """Pin internal pull down"""
    PULL_NONE = None
    """Pin internal pull none"""

    IRQ_FALLING = 0x21
    """Pin interrupt falling"""
    IRQ_RISING = 0x22
    """Pin interrupt rising"""
    IRQ_RISING_FALLING = 0x23
    """Pin interrupt both rising and falling"""

    _dict: Dict[str, int] = {
        "D0": 17,
        "D1": 4,   # Changed
        "D2": 27,
        "D3": 22,
        "D4": 23,
        "D5": 24,
        "D6": 25,  # Removed
        "D7": 4,   # Removed
        "D8": 5,   # Removed
        "D9": 6,
        "D10": 12,
        "D11": 13,
        "D12": 19,
        "D13": 16,
        "D14": 26,
        "D15": 20,
        "D16": 21,
        "SW": 25,  # Changed
        "USER": 25,
        "LED": 26,
        "BOARD_TYPE": 12,
        "RST": 16,
        "BLEINT": 13,
        "BLERST": 20,
        "MCURST": 5,  # Changed
        "CE": 8,
    }

    def __init__(self, pin: Union[int, str], mode: Optional[int] = None, pull: Optional[int] = None, active_state: Optional[bool] = None, *args, **kwargs) -> None:
        """
        Initialize a pin

        :param pin: Pin number (int) or board name (str) of Raspberry Pi
        :param mode: Pin mode (Pin.OUT or Pin.IN)
        :param pull: Pin pull up/down (Pin.PULL_UP, Pin.PULL_DOWN, or Pin.PULL_NONE)
        :param active_state: Active state of pin; if True, a HIGH hardware state maps to HIGH in software.
        """
        super().__init__(*args, **kwargs)

        # Parse pin input
        if isinstance(pin, str):
            if pin not in self.dict().keys():
                raise ValueError(f'Pin should be one of {list(self._dict.keys())}, not "{pin}"')
            self._board_name = pin
            self._pin_num = self.dict()[pin]
        elif isinstance(pin, int):
            if pin not in self.dict().values():
                raise ValueError(f'Pin should be one of {list(self._dict.values())}, not "{pin}"')
            # Save board name(s) associated with the pin
            self._board_name = {name for name, num in self._dict.items() if num == pin}
            self._pin_num = pin
        else:
            raise ValueError(f'Pin must be an int or a valid key from {list(self._dict.keys())}, not "{pin}"')

        # Setup initial state
        self._value = 0
        self.gpio: Optional[Any] = None
        self.setup(mode, pull, active_state)
        self.logger.info("Pin init finished.")

    def close(self) -> None:
        if self.gpio:
            self.gpio.close()

    def deinit(self) -> None:
        if self.gpio:
            self.gpio.close()
            if hasattr(self.gpio, "pin_factory") and self.gpio.pin_factory:
                self.gpio.pin_factory.close()

    def setup(self, mode: Optional[int], pull: Optional[int] = None, active_state: Optional[bool] = None) -> None:
        """
        Setup the pin

        :param mode: Pin mode (Pin.OUT or Pin.IN)
        :param pull: Pull configuration (Pin.PULL_UP, Pin.PULL_DOWN, or Pin.PULL_NONE)
        """
        # Validate mode
        if mode in [None, self.OUT, self.IN]:
            self._mode = mode
        else:
            raise ValueError('mode parameter error, should be None, Pin.OUT, or Pin.IN')
        # Validate pull
        if pull in [self.PULL_NONE, self.PULL_DOWN, self.PULL_UP]:
            self._pull = pull
        else:
            raise ValueError('pull parameter error, should be None, Pin.PULL_NONE, Pin.PULL_DOWN, or Pin.PULL_UP')

        # Close any existing gpio instance
        if self.gpio is not None:
            try:
                self.gpio.close()
            except Exception:
                pass

        # Initialize gpio based on mode
        if mode in [None, self.OUT]:
            self.gpio = OutputDevice(self._pin_num)
        else:
            if pull == self.PULL_UP:
                self.gpio = InputDevice(self._pin_num, pull_up=True, active_state=None)
            elif pull == self.PULL_DOWN:
                self.gpio = InputDevice(self._pin_num, pull_up=False, active_state=None)
            else:
                self.gpio = InputDevice(self._pin_num, pull_up=None, active_state=active_state)

    def dict(self, _dict: Optional[Dict[str, int]] = None) -> Dict[str, int]:
        """
        Set/get the pin dictionary

        :param _dict: Optional new pin dictionary.
        :return: Current pin dictionary.
        """
        if _dict is None:
            return self._dict
        else:
            if not isinstance(_dict, dict):
                raise ValueError(f'Argument should be a dict, not {_dict}')
            self._dict = _dict
            return self._dict

    def __call__(self, value: Optional[int] = None) -> int:
        """
        Set/get the pin value

        :param value: If provided, set the pin value (0 or 1). Otherwise, return current value.
        :return: Pin value (0 or 1).
        """
        return self.value(value)

    def value(self, value: Optional[bool] = None) -> int:
        """
        Set/get the pin value

        :param value: If provided, set the pin to 0 or 1; otherwise, return current value.
        :return: Pin value (0 or 1).
        """
        if value is None:
            if self._mode in [None, self.OUT]:
                self.setup(self.IN)
            result = self.gpio.value
            self.logger.debug(f"Read pin {self.gpio.pin}: {result}")
            return result
        else:
            if self._mode == self.IN:
                self.setup(self.OUT)
            if bool(value):
                self.gpio.on()
                value_int = 1
            else:
                self.gpio.off()
                value_int = 0
            return value_int

    def on(self) -> int:
        """Set pin on (high) and return value 1."""
        return self.value(1)

    def off(self) -> int:
        """Set pin off (low) and return value 0."""
        return self.value(0)

    def high(self) -> int:
        """Alias for on()."""
        return self.on()

    def low(self) -> int:
        """Alias for off()."""
        return self.off()

    def irq(self, handler, trigger: int, bouncetime: int = 200, pull: Optional[int] = None) -> None:
        """
        Set the pin interrupt

        :param handler: Interrupt handler callback function.
        :param trigger: Interrupt trigger (Pin.IRQ_RISING, Pin.IRQ_FALLING, or Pin.IRQ_RISING_FALLING).
        :param bouncetime: Debounce time in milliseconds.
        :param pull: Pull configuration (Pin.PULL_UP, Pin.PULL_DOWN, or Pin.PULL_NONE).
        """
        if trigger not in [self.IRQ_FALLING, self.IRQ_RISING, self.IRQ_RISING_FALLING]:
            raise ValueError('trigger parameter error, should be Pin.IRQ_FALLING, Pin.IRQ_RISING, or Pin.IRQ_RISING_FALLING')

        if pull in [self.PULL_NONE, self.PULL_DOWN, self.PULL_UP]:
            self._pull = pull
            _pull_up = True if pull == self.PULL_UP else False
        else:
            raise ValueError('pull parameter error, should be None, Pin.PULL_NONE, Pin.PULL_DOWN, or Pin.PULL_UP')

        pressed_handler = None
        released_handler = None

        if not isinstance(self.gpio, Button):
            if self.gpio is not None:
                self.gpio.close()
            self.gpio = Button(pin=self._pin_num, pull_up=_pull_up, bounce_time=float(bouncetime / 1000))
            self._bouncetime = bouncetime
        else:
            if bouncetime != getattr(self, "_bouncetime", bouncetime):
                pressed_handler = self.gpio.when_pressed
                released_handler = self.gpio.when_released
                self.gpio.close()
                self.gpio = Button(pin=self._pin_num, pull_up=_pull_up, bounce_time=float(bouncetime / 1000))
                self._bouncetime = bouncetime

        if trigger in [None, self.IRQ_FALLING]:
            pressed_handler = handler
        elif trigger == self.IRQ_RISING:
            released_handler = handler
        elif trigger == self.IRQ_RISING_FALLING:
            pressed_handler = handler
            released_handler = handler

        if pressed_handler is not None:
            self.gpio.when_pressed = pressed_handler
        if released_handler is not None:
            self.gpio.when_released = released_handler

    def name(self) -> str:
        """
        Get the pin name as a string (e.g., "GPIO17").

        :return: Pin name.
        """
        return f"GPIO{self._pin_num}"