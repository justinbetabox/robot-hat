#!/usr/bin/env python3
"""
Pulse width modulation (PWM) via I2C for Robot Hat.
"""
import math
from typing import Union, Optional, List, Dict
from .i2c import I2C

# Global timer configuration for PWM: list of dictionaries with 'arr' keys
timer: List[Dict[str, int]] = [{"arr": 1} for _ in range(7)]


def test() -> None:
    """Test PWM by sweeping values on channel 0."""
    import time
    p = PWM(0, debug_level='debug')  # type: ignore
    p.period(1000)
    p.prescaler(10)
    while True:
        for i in range(0, 4095, 10):
            p.pulse_width(i)
            print(i)
            time.sleep(1/4095)
        time.sleep(1)
        for i in range(4095, 0, -10):
            p.pulse_width(i)
            print(i)
            time.sleep(1/4095)
        time.sleep(1)


def test2() -> None:
    """Test PWM by setting channel P0 to 50%."""
    p = PWM("P0", debug_level='debug')  # type: ignore
    p.pulse_width_percent(50)


class PWM(I2C):
    """Pulse width modulation (PWM) controller over I2C."""

    REG_CHN: int = 0x20
    """Channel register prefix"""
    REG_PSC: int = 0x40
    """Prescaler register prefix"""
    REG_ARR: int = 0x44
    """Period register prefix"""
    REG_PSC2: int = 0x50
    """Secondary prescaler register prefix"""
    REG_ARR2: int = 0x54
    """Secondary period register prefix"""

    ADDR: List[int] = [0x14, 0x15, 0x16]

    CLOCK: float = 72000000.0
    """Clock frequency"""

    def __init__(
        self,
        channel: Union[int, str],
        address: Optional[Union[int, List[int]]] = None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """
        Initialize PWM channel.

        :param channel: Channel number (0-19) or name "P0"-"P19".
        :param address: I2C address or list of addresses.
        """
        if address is None:
            super().__init__(self.ADDR, *args, **kwargs)
        else:
            super().__init__(address, *args, **kwargs)  # type: ignore

        # Parse channel
        if isinstance(channel, str):
            if channel.startswith("P"):
                channel = int(channel[1:])  # type: ignore
            else:
                raise ValueError(f'PWM channel should be between [P0, P19], not "{channel}"')
        if not isinstance(channel, int) or not (0 <= channel <= 19):
            raise ValueError(f'Channel must be in range 0-19, not "{channel}"')

        self.channel: int = channel
        # Determine timer index
        if channel < 16:
            self.timer_index: int = channel // 4
        elif channel in (16, 17):
            self.timer_index = 4
        elif channel == 18:
            self.timer_index = 5
        else:
            self.timer_index = 6

        self._pulse_width: int = 0
        self._freq: int = 50
        # Initialize frequency
        self.freq(50)  # type: ignore

    def _i2c_write(self, reg: int, value: int) -> None:
        """
        Write a 16-bit value to a register via I2C.

        :param reg: Register address.
        :param value: Value to write.
        """
        value_h: int = value >> 8
        value_l: int = value & 0xFF
        self.write([reg, value_h, value_l])  # type: ignore

    def freq(self, freq: Optional[float] = None) -> Optional[float]:
        """
        Set or get PWM frequency.

        :param freq: Frequency in Hz.
        :return: Current frequency if getting, otherwise None.
        """
        if freq is None:
            return float(self._freq)

        self._freq = int(freq)
        candidates: List[List[int]] = []
        errors: List[float] = []
        # Estimate start prescaler
        start: int = int(math.sqrt(self.CLOCK / self._freq)) - 5
        start = max(start, 1)

        for psc in range(start, start + 10):
            arr = int(self.CLOCK / self._freq / psc)
            candidates.append([psc, arr])
            errors.append(abs(self._freq - self.CLOCK / psc / arr))
        idx: int = errors.index(min(errors))
        psc, arr = candidates[idx]
        self.logger.debug(f"Prescaler: {psc}, period: {arr}")
        self.prescaler(psc)
        self.period(arr)
        return None

    def prescaler(self, prescaler: Optional[float] = None) -> Optional[int]:
        """
        Set or get the prescaler.

        :param prescaler: Prescaler value.
        :return: Current prescaler if getting, otherwise None.
        """
        if prescaler is None:
            return getattr(self, '_prescaler', None)

        self._prescaler = round(prescaler)  # type: ignore
        # Update frequency based on timer arr
        self._freq = int(self.CLOCK / self._prescaler / timer[self.timer_index]['arr'])
        # Determine register
        if self.timer_index < 4:
            reg = self.REG_PSC + self.timer_index
        else:
            reg = self.REG_PSC2 + self.timer_index - 4
        self.logger.debug(f"Set prescaler to: {self._prescaler}")
        self._i2c_write(reg, self._prescaler - 1)
        return None

    def period(self, arr: Optional[float] = None) -> Optional[int]:
        """
        Set or get the period (ARR register).

        :param arr: Period value.
        :return: Current period if getting, otherwise None.
        """
        if arr is None:
            return timer[self.timer_index]['arr']

        timer[self.timer_index]['arr'] = round(arr)  # type: ignore
        self._freq = int(self.CLOCK / self._prescaler / timer[self.timer_index]['arr'])  # type: ignore
        if self.timer_index < 4:
            reg = self.REG_ARR + self.timer_index
        else:
            reg = self.REG_ARR2 + self.timer_index - 4
        self.logger.debug(f"Set period to: {timer[self.timer_index]['arr']}")
        self._i2c_write(reg, timer[self.timer_index]['arr'])
        return None

    def pulse_width(self, pulse_width: Optional[float] = None) -> Optional[float]:
        """
        Set or get the raw pulse width.

        :param pulse_width: Pulse width value.
        :return: Current pulse width if getting, otherwise None.
        """
        if pulse_width is None:
            return float(self._pulse_width)

        self._pulse_width = int(pulse_width)  # type: ignore
        reg: int = self.REG_CHN + self.channel
        self._i2c_write(reg, self._pulse_width)
        return None

    def pulse_width_percent(self, pulse_width_percent: Optional[float] = None) -> Optional[float]:
        """
        Set or get the pulse width as a percentage of period.

        :param pulse_width_percent: Percentage (0-100).
        :return: Current percentage if getting, otherwise None.
        """
        if pulse_width_percent is None:
            return getattr(self, '_pulse_width_percent', None)

        self._pulse_width_percent = pulse_width_percent  # type: ignore
        ratio: float = self._pulse_width_percent / 100.0
        width: float = ratio * timer[self.timer_index]['arr']
        self.pulse_width(width)
        return None


if __name__ == '__main__':
    test2()