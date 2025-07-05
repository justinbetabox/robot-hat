#!/usr/bin/env python3
"""
Sensor and actuator modules for Robot Hat.
"""
import time
import logging
from typing import Union, List, Tuple, Optional, Any

from .pin import Pin
from .pwm import PWM
from .adc import ADC
from .i2c import I2C
from .basic import BasicClass

# Module-level logger for non-BasicClass components
logger = logging.getLogger(__name__)


class Ultrasonic:
    """Ultrasonic distance sensor interface."""
    SOUND_SPEED: float = 343.3  # m/s

    def __init__(self, trig: Pin, echo: Pin, timeout: float = 0.02) -> None:
        """
        :param trig: Trigger pin (must be robot_hat.Pin)
        :param echo: Echo pin (must be robot_hat.Pin)
        :param timeout: Timeout for pulse (seconds)
        """
        if not isinstance(trig, Pin):
            raise TypeError("trig must be robot_hat.Pin object")
        if not isinstance(echo, Pin):
            raise TypeError("echo must be robot_hat.Pin object")

        self.timeout: float = timeout
        # Reset pins
        trig.close()
        echo.close()
        self.trig: Pin = Pin(trig._pin_num)
        self.echo: Pin = Pin(echo._pin_num, mode=Pin.IN, pull=Pin.PULL_DOWN)

    def _read(self) -> Union[float, int]:
        self.trig.off()
        time.sleep(0.001)
        self.trig.on()
        time.sleep(0.00001)
        self.trig.off()

        pulse_start: float = 0.0
        pulse_end: float = 0.0
        start_time: float = time.time()

        while self.echo.gpio.value == 0:
            pulse_start = time.time()
            if pulse_start - start_time > self.timeout:
                return -1
        while self.echo.gpio.value == 1:
            pulse_end = time.time()
            if pulse_end - start_time > self.timeout:
                return -1
        if pulse_start == 0 or pulse_end == 0:
            return -2

        duration: float = pulse_end - pulse_start
        distance_cm: float = round(duration * self.SOUND_SPEED / 2 * 100, 2)
        return distance_cm

    def read(self, times: int = 10) -> Union[float, int]:
        """
        Take multiple readings and return the first valid one.

        :param times: Number of attempts.
        :return: Distance in cm or error code.
        """
        for _ in range(times):
            val = self._read()
            if val != -1:
                return val
        return -1


class ADXL345(I2C):
    """ADXL345 3-axis accelerometer module."""
    X = 0
    Y = 1
    Z = 2
    ADDR: int = 0x53
    _REG_DATA: List[int] = [0x32, 0x34, 0x36]
    _REG_POWER_CTL: int = 0x2D

    def __init__(
        self,
        *args: Any,
        address: int = ADDR,
        bus: int = 1,
        **kwargs: Any
    ) -> None:
        """
        :param address: I2C address (default 0x53)
        :param bus: I2C bus number.
        """
        super().__init__(address=address, bus=bus, *args, **kwargs)
        self.address = address
        self.logger.debug(f"Initialized ADXL345 at 0x{address:02X}")

    def read(self, axis: Optional[int] = None) -> Union[float, List[float]]:
        """
        Read acceleration in g.

        :param axis: X, Y, Z or None for all.
        :return: Single value or list of three.
        """
        if axis is None:
            return [self._read(i) for i in (self.X, self.Y, self.Z)]
        return self._read(axis)

    def _read(self, axis: int) -> float:
        raw_bytes: List[int] = []
        # Wake up and configure
        self.mem_write(0, 0x31)
        self.mem_write(8, self._REG_POWER_CTL)
        # Read two bytes
        raw_bytes = self.mem_read(2, self._REG_DATA[axis])  # type: ignore
        if raw_bytes[1] >> 7:
            raw_val = ((raw_bytes[1] ^ 0x80) ^ 0x7F) * -1
        else:
            raw_val = raw_bytes[1]
        value: float = ((raw_val << 8) | raw_bytes[0]) / 256.0
        self.logger.debug(f"ADXL345 axis {axis}: {value}g")
        return value


class RGB_LED:
    """3-pin RGB LED controller."""
    ANODE = 1
    CATHODE = 0

    def __init__(
        self,
        r_pin: PWM,
        g_pin: PWM,
        b_pin: PWM,
        common: int = ANODE
    ) -> None:
        """
        :param r_pin: PWM for red
        :param g_pin: PWM for green
        :param b_pin: PWM for blue
        :param common: ANODE or CATHODE
        """
        if not isinstance(r_pin, PWM):
            raise TypeError("r_pin must be robot_hat.PWM object")
        if not isinstance(g_pin, PWM):
            raise TypeError("g_pin must be robot_hat.PWM object")
        if not isinstance(b_pin, PWM):
            raise TypeError("b_pin must be robot_hat.PWM object")
        if common not in (self.ANODE, self.CATHODE):
            raise ValueError("common must be RGB_LED.ANODE or RGB_LED.CATHODE")
        self.r_pin = r_pin
        self.g_pin = g_pin
        self.b_pin = b_pin
        self.common = common

    def color(self, color: Union[str, Tuple[int, int, int], List[int], int]) -> None:
        """
        Set LED color.

        :param color: Hex string, int, or tuple/list.
        """
        if isinstance(color, str):
            color = int(color.strip('#'), 16)
        if isinstance(color, (tuple, list)):
            r, g, b = color  # type: ignore
        elif isinstance(color, int):
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
        else:
            raise TypeError("color must be str, int, tuple, or list")
        if self.common == self.ANODE:
            r, g, b = 255 - r, 255 - g, 255 - b
        # Convert to percent
        r_pct = r / 255.0 * 100.0
        g_pct = g / 255.0 * 100.0
        b_pct = b / 255.0 * 100.0
        self.r_pin.pulse_width_percent(r_pct)
        self.g_pin.pulse_width_percent(g_pct)
        self.b_pin.pulse_width_percent(b_pct)
        logger.debug(f"RGB_LED set to R:{r_pct}%,G:{g_pct}%,B:{b_pct}%")


class Buzzer:
    """Buzzer controller for passive or active buzzers."""

    def __init__(self, buzzer: Union[PWM, Pin]) -> None:
        """
        :param buzzer: PWM for passive or Pin for active buzzer.
        """
        if not isinstance(buzzer, (PWM, Pin)):
            raise TypeError("buzzer must be robot_hat.PWM or robot_hat.Pin")
        self.buzzer = buzzer
        self.buzzer.off()

    def on(self) -> None:
        """Turn buzzer on."""
        if isinstance(self.buzzer, PWM):
            self.buzzer.pulse_width_percent(50)
        else:
            self.buzzer.on()

    def off(self) -> None:
        """Turn buzzer off."""
        if isinstance(self.buzzer, PWM):
            self.buzzer.pulse_width_percent(0)
        else:
            self.buzzer.off()

    def freq(self, freq: float) -> None:
        """
        Set passive buzzer frequency.

        :param freq: Frequency in Hz.
        :raises TypeError: If using active buzzer.
        """
        if not isinstance(self.buzzer, PWM):
            raise TypeError("freq not supported for active buzzer")
        self.buzzer.freq(freq)

    def play(self, freq: float, duration: Optional[float] = None) -> None:
        """
        Play a tone.

        :param freq: Frequency in Hz.
        :param duration: Duration in seconds.
        :raises TypeError: If using active buzzer.
        """
        self.freq(freq)
        self.on()
        if duration is not None:
            time.sleep(duration)
            self.off()


class Grayscale_Module:
    """Three-channel grayscale sensor module."""
    LEFT = 0
    MIDDLE = 1
    RIGHT = 2

    REFERENCE_DEFAULT: List[int] = [1000, 1000, 1000]

    def __init__(
        self,
        pin0: ADC,
        pin1: ADC,
        pin2: ADC,
        reference: Optional[List[int]] = None
    ) -> None:
        """
        :param pin0: ADC for channel 0
        :param pin1: ADC for channel 1
        :param pin2: ADC for channel 2
        :param reference: Optional comparison thresholds.
        """
        self.pins: Tuple[ADC, ADC, ADC] = (pin0, pin1, pin2)
        for i, p in enumerate(self.pins):
            if not isinstance(p, ADC):
                raise TypeError(f"pin{i} must be robot_hat.ADC")
        self._reference: List[int] = reference if reference is not None else self.REFERENCE_DEFAULT

    def reference(self, ref: Optional[List[int]] = None) -> List[int]:
        """
        Get or set reference thresholds.

        :param ref: New thresholds list.
        :return: Current thresholds.
        """
        if ref is not None:
            if isinstance(ref, list) and len(ref) == 3:
                self._reference = ref
            else:
                raise TypeError("ref must be 3-element list.")
        return self._reference

    def read_status(self, datas: Optional[List[int]] = None) -> List[int]:
        """
        Get digital status compared to thresholds.

        :param datas: Optional raw values.
        :return: 0 for above threshold, 1 for below.
        """
        if datas is None:
            datas = [pin.read() for pin in self.pins]
        return [0 if datas[i] > self._reference[i] else 1 for i in range(3)]

    def read(self, channel: Optional[int] = None) -> List[int]:
        """
        Read raw sensor values.

        :param channel: Specific index or None for all.
        :return: List of readings.
        """
        if channel is None:
            return [pin.read() for pin in self.pins]
        return [self.pins[channel].read()]


if __name__ == '__main__':
    # Example usage
    tri = Pin(17)
    ech = Pin(27)
    us = Ultrasonic(tri, ech)
    print(us.read())
