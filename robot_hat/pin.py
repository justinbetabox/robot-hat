#!/usr/bin/env python3
"""
Pin manipulation class for Robot Hat.
"""
import gpiozero  # https://gpiozero.readthedocs.io/en/latest/installing.html
from gpiozero import OutputDevice, InputDevice, Button
from typing import Union, Optional, Dict, Any, Callable

from .basic import BasicClass


class Pin(BasicClass):
    """Pin manipulation class"""

    OUT: int = 0x01
    """Pin mode output"""
    IN: int = 0x02
    """Pin mode input"""

    PULL_UP: int = 0x11
    """Pin internal pull up"""
    PULL_DOWN: int = 0x12
    """Pin internal pull down"""
    PULL_NONE: Optional[int] = None
    """Pin internal pull none"""

    IRQ_FALLING: int = 0x21
    """Pin interrupt falling"""
    IRQ_RISING: int = 0x22
    """Pin interrupt rising"""
    IRQ_RISING_FALLING: int = 0x23
    """Pin interrupt both rising and falling"""

    _dict: Dict[str, int] = {
        "D0": 17,
        "D1": 4,
        "D2": 27,
        "D3": 22,
        "D4": 23,
        "D5": 24,
        "D6": 25,
        "D7": 4,
        "D8": 5,
        "D9": 6,
        "D10": 12,
        "D11": 13,
        "D12": 19,
        "D13": 16,
        "D14": 26,
        "D15": 20,
        "D16": 21,
        "SW": 25,
        "USER": 25,
        "LED": 26,
        "BOARD_TYPE": 12,
        "RST": 16,
        "BLEINT": 13,
        "BLERST": 20,
        "MCURST": 5,
        "CE": 8,
    }

    def __init__(
        self,
        pin: Union[int, str],
        mode: Optional[int] = None,
        pull: Optional[int] = None,
        active_state: Optional[bool] = None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """
        Initialize a pin.

        :param pin: Pin number (int) or board name (str).
        :param mode: Pin mode (Pin.OUT or Pin.IN).
        :param pull: Pull configuration (Pin.PULL_UP, Pin.PULL_DOWN, or Pin.PULL_NONE).
        :param active_state: Active state mapping for input pulls.
        """
        super().__init__(*args, **kwargs)

        # Parse pin input
        if isinstance(pin, str):
            if pin not in self._dict:
                raise ValueError(f'Pin should be one of {list(self._dict.keys())}, not "{pin}"')
            self._board_name: str = pin
            self._pin_num: int = self._dict[pin]
        elif isinstance(pin, int):
            if pin not in self._dict.values():
                raise ValueError(f'Pin should be one of {list(self._dict.values())}, not "{pin}"')
            self._board_name = {name for name, num in self._dict.items() if num == pin}  # type: ignore
            self._pin_num = pin
        else:
            raise ValueError(f'Pin must be int or str, not {type(pin)}')

        self._mode: Optional[int] = None
        self._pull: Optional[int] = None
        self._value: int = 0
        self.gpio: Optional[Any] = None

        self.setup(mode, pull, active_state)
        self.logger.info("Pin init finished.")

    def close(self) -> None:
        """Close the underlying gpio device."""
        if self.gpio:
            self.gpio.close()

    def deinit(self) -> None:
        """Deinitialize the gpio device and factory."""
        if self.gpio:
            self.gpio.close()
            if hasattr(self.gpio, "pin_factory") and self.gpio.pin_factory:
                self.gpio.pin_factory.close()

    def setup(
        self,
        mode: Optional[int],
        pull: Optional[int] = None,
        active_state: Optional[bool] = None
    ) -> None:
        """
        Configure pin mode and pull.

        :param mode: Pin mode (None, Pin.OUT, or Pin.IN).
        :param pull: Pull configuration (PULL_UP, PULL_DOWN, or PULL_NONE).
        :param active_state: Active state for input device.
        """
        if mode not in (None, self.OUT, self.IN):
            raise ValueError('mode must be None, Pin.OUT, or Pin.IN')
        if pull not in (self.PULL_NONE, self.PULL_DOWN, self.PULL_UP):
            raise ValueError('pull must be None, Pin.PULL_NONE, Pin.PULL_DOWN, or Pin.PULL_UP')

        self._mode = mode
        self._pull = pull

        if self.gpio is not None:
            try:
                self.gpio.close()
            except Exception:
                pass

        if mode in (None, self.OUT):
            self.gpio = OutputDevice(self._pin_num)
        else:
            pull_up = True if pull == self.PULL_UP else False
            if pull == self.PULL_NONE:
                pull_arg = None
            else:
                pull_arg = pull_up
            self.gpio = InputDevice(self._pin_num, pull_up=pull_arg, active_state=active_state)

    def dict(self, _dict: Optional[Dict[str, int]] = None) -> Dict[str, int]:
        """
        Get or set the pin mapping dictionary.

        :param _dict: New dictionary to set, or None to retrieve.
        :return: Current pin dictionary.
        """
        if _dict is None:
            return self._dict
        if not isinstance(_dict, dict):
            raise ValueError(f'Argument should be a dict, not {_dict}')
        self._dict = _dict
        return self._dict

    def __call__(self, value: Optional[int] = None) -> int:
        """Alias to get or set pin value."""
        return self.value(value)

    def value(self, value: Optional[bool] = None) -> int:
        """
        Get or set the pin state.

        :param value: If provided, set pin to high (True) or low (False). Otherwise read.
        :return: Pin state as 0 or 1.
        """
        if value is None:
            if self._mode in (None, self.OUT):
                self.setup(self.IN)
            result: int = int(self.gpio.value)  # type: ignore
            self.logger.debug(f"Read pin {self._pin_num}: {result}")
            return result
        else:
            if self._mode == self.IN:
                self.setup(self.OUT)
            level = bool(value)
            if level:
                self.gpio.on()  # type: ignore
                return 1
            else:
                self.gpio.off()  # type: ignore
                return 0

    def on(self) -> int:
        """Set pin high and return 1."""
        return self.value(True)

    def off(self) -> int:
        """Set pin low and return 0."""
        return self.value(False)

    def high(self) -> int:
        """Alias for on()."""
        return self.on()

    def low(self) -> int:
        """Alias for off()."""
        return self.off()

    def irq(
        self,
        handler: Callable[..., Any],
        trigger: int,
        bouncetime: int = 200,
        pull: Optional[int] = None
    ) -> None:
        """
        Configure an interrupt on the pin.

        :param handler: Callback for interrupt events.
        :param trigger: Pin.IRQ_FALLING, IRQ_RISING, or IRQ_RISING_FALLING.
        :param bouncetime: Debounce in ms.
        :param pull: Pull configuration (PULL_UP, PULL_DOWN, or PULL_NONE).
        """
        if trigger not in (self.IRQ_FALLING, self.IRQ_RISING, self.IRQ_RISING_FALLING):
            raise ValueError('Invalid trigger for irq')
        if pull not in (self.PULL_NONE, self.PULL_DOWN, self.PULL_UP):
            raise ValueError('Invalid pull for irq')

        # Prepare Button instance
        pull_up = True if pull == self.PULL_UP else False
        if not isinstance(self.gpio, Button):
            if self.gpio:
                self.gpio.close()
            self.gpio = Button(pin=self._pin_num, pull_up=pull_up, bounce_time=bouncetime/1000)
        else:
            if bouncetime != getattr(self, '_bouncetime', None):
                prev_pressed = self.gpio.when_pressed
                prev_released = self.gpio.when_released
                self.gpio.close()
                self.gpio = Button(pin=self._pin_num, pull_up=pull_up, bounce_time=bouncetime/1000)
                self.gpio.when_pressed = prev_pressed  # type: ignore
                self.gpio.when_released = prev_released  # type: ignore
        self._bouncetime = bouncetime

        # Assign handlers based on trigger
        if trigger in (None, self.IRQ_FALLING):
            self.gpio.when_pressed = handler  # type: ignore
        elif trigger == self.IRQ_RISING:
            self.gpio.when_released = handler  # type: ignore
        else:
            self.gpio.when_pressed = handler  # type: ignore
            self.gpio.when_released = handler  # type: ignore

    def name(self) -> str:
        """
        Get the GPIO name (e.g., 'GPIO17').

        :return: Name string.
        """
        return f"GPIO{self._pin_num}"
