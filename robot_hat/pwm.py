#!/usr/bin/env python3
import math
from typing import Union, Optional
from .i2c import I2C

# Global timer configuration for PWM
timer = [{"arr": 1} for _ in range(7)]


class PWM(I2C):
    """Pulse width modulation (PWM)"""

    REG_CHN = 0x20
    """Channel register prefix"""
    REG_PSC = 0x40
    """Prescaler register prefix"""
    REG_ARR = 0x44
    """Period register prefix"""
    REG_PSC2 = 0x50
    """Secondary prescaler register prefix"""
    REG_ARR2 = 0x54
    """Secondary period register prefix"""

    ADDR = [0x14, 0x15, 0x16]

    CLOCK = 72000000.0
    """Clock frequency"""

    def __init__(self, channel: Union[int, str], address: Optional[Union[int, list]] = None, *args, **kwargs) -> None:
        """
        Initialize PWM

        :param channel: PWM channel number (0-19 or "P0"-"P19")
        :type channel: int or str
        :param address: I2C device address or list of addresses, defaults to None
        """
        if address is None:
            super().__init__(self.ADDR, *args, **kwargs)
        else:
            super().__init__(address, *args, **kwargs)

        if isinstance(channel, str):
            if channel.startswith("P"):
                channel = int(channel[1:])
            else:
                raise ValueError(f'PWM channel should be between [P0, P19], not "{channel}"')
        if isinstance(channel, int):
            if channel < 0 or channel > 19:
                raise ValueError(f'Channel must be in range of 0-19, not "{channel}"')
        else:
            raise ValueError("Channel must be an int or str.")

        self.channel = channel
        if channel < 16:
            self.timer_index = channel // 4
        elif channel in (16, 17):
            self.timer_index = 4
        elif channel == 18:
            self.timer_index = 5
        elif channel == 19:
            self.timer_index = 6

        self._pulse_width = 0
        self._freq = 50
        self.freq(50)

    def _i2c_write(self, reg: int, value: int) -> None:
        """
        Write a value to an I2C register.
        
        :param reg: Register address.
        :param value: Value to write.
        """
        value_h = value >> 8
        value_l = value & 0xff
        self.write([reg, value_h, value_l])

    def freq(self, freq: Optional[float] = None) -> Union[float, None]:
        """
        Set/get frequency. Leave blank to get current frequency.
        
        :param freq: Frequency (Hz), defaults to None.
        :return: Frequency if getting, otherwise None.
        """
        if freq is None:
            return self._freq

        self._freq = int(freq)
        result_ap = []  # List to store [prescaler, arr] pairs
        result_acy = []  # List to store frequency error for each pair
        
        # Start search from an estimated middle value
        st = int(math.sqrt(self.CLOCK / self._freq)) - 5
        if st <= 0:
            st = 1

        for psc in range(st, st + 10):
            arr = int(self.CLOCK / self._freq / psc)
            result_ap.append([psc, arr])
            result_acy.append(abs(self._freq - self.CLOCK / psc / arr))
        i = result_acy.index(min(result_acy))
        psc, arr = result_ap[i]
        self.logger.debug(f"prescaler: {psc}, period: {arr}")
        self.prescaler(psc)
        self.period(arr)

    def prescaler(self, prescaler: Optional[float] = None) -> Union[int, None]:
        """
        Set/get prescaler. Leave blank to get current prescaler.
        
        :param prescaler: Prescaler value, defaults to None.
        :return: Current prescaler if getting, otherwise None.
        """
        if prescaler is None:
            return getattr(self, "_prescaler", None)

        self._prescaler = round(prescaler)
        # Update frequency based on new prescaler and current period
        self._freq = self.CLOCK / self._prescaler / timer[self.timer_index]["arr"]
        if self.timer_index < 4:
            reg = self.REG_PSC + self.timer_index
        else:
            reg = self.REG_PSC2 + self.timer_index - 4
        self.logger.debug(f"Set prescaler to: {self._prescaler}")
        self._i2c_write(reg, self._prescaler - 1)

    def period(self, arr: Optional[float] = None) -> Union[int, None]:
        """
        Set/get period. Leave blank to get current period.
        
        :param arr: Period value, defaults to None.
        :return: Current period if getting, otherwise None.
        """
        global timer
        if arr is None:
            return timer[self.timer_index]["arr"]

        timer[self.timer_index]["arr"] = round(arr)
        self._freq = self.CLOCK / self._prescaler / timer[self.timer_index]["arr"]

        if self.timer_index < 4:
            reg = self.REG_ARR + self.timer_index
        else:
            reg = self.REG_ARR2 + self.timer_index - 4

        self.logger.debug(f"Set arr to: {timer[self.timer_index]['arr']}")
        self._i2c_write(reg, timer[self.timer_index]["arr"])

    def pulse_width(self, pulse_width: Optional[float] = None) -> Union[float, None]:
        """
        Set/get pulse width. Leave blank to get current pulse width.
        
        :param pulse_width: Pulse width value, defaults to None.
        :return: Current pulse width if getting, otherwise None.
        """
        if pulse_width is None:
            return self._pulse_width

        self._pulse_width = int(pulse_width)
        reg = self.REG_CHN + self.channel
        self._i2c_write(reg, self._pulse_width)

    def pulse_width_percent(self, pulse_width_percent: Optional[float] = None) -> Union[float, None]:
        """
        Set/get pulse width percentage. Leave blank to get current percentage.
        
        :param pulse_width_percent: Pulse width percentage (0-100), defaults to None.
        :return: Current pulse width percentage if getting, otherwise None.
        """
        global timer
        if pulse_width_percent is None:
            return getattr(self, "_pulse_width_percent", None)

        self._pulse_width_percent = pulse_width_percent
        temp = self._pulse_width_percent / 100.0
        pulse_width = temp * timer[self.timer_index]["arr"]
        self.pulse_width(pulse_width)


def test():
    import time
    p = PWM(0, debug_level='debug')
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


def test2():
    p = PWM("P0", debug_level='debug')
    p.pulse_width_percent(50)


if __name__ == '__main__':
    test2()