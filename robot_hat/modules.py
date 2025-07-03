#!/usr/bin/env python3
from .pin import Pin
from .pwm import PWM
from .adc import ADC
from .i2c import I2C
from .basic import BasicClass
from typing import Union, List, Tuple, Optional
import time
import logging

# Optional: Create a module-level logger for classes that do not inherit from BasicClass.
logger = logging.getLogger(__name__)


class Ultrasonic:
    SOUND_SPEED: float = 343.3  # m/s

    def __init__(self, trig: Pin, echo: Pin, timeout: float = 0.02) -> None:
        if not isinstance(trig, Pin):
            raise TypeError("trig must be robot_hat.Pin object")
        if not isinstance(echo, Pin):
            raise TypeError("echo must be robot_hat.Pin object")

        self.timeout: float = timeout

        # Close and reinitialize to avoid conflicts.
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

        pulse_start: float = 0
        pulse_end: float = 0
        timeout_start: float = time.time()

        while self.echo.gpio.value == 0:
            pulse_start = time.time()
            if pulse_start - timeout_start > self.timeout:
                return -1
        while self.echo.gpio.value == 1:
            pulse_end = time.time()
            if pulse_end - timeout_start > self.timeout:
                return -1
        if pulse_start == 0 or pulse_end == 0:
            return -2

        during: float = pulse_end - pulse_start
        # Calculate distance in centimeters.
        cm: float = round(during * self.SOUND_SPEED / 2 * 100, 2)
        return cm

    def read(self, times: int = 10) -> Union[float, int]:
        for _ in range(times):
            a = self._read()
            if a != -1:
                return a
        return -1


class ADXL345(I2C):
    """ADXL345 accelerometer module."""

    X: int = 0
    Y: int = 1
    Z: int = 2
    ADDR: int = 0x53
    _REG_DATA_X: int = 0x32  # X-axis data start register (6 bytes for X/Y/Z)
    _REG_DATA_Y: int = 0x34  # Y-axis data start register
    _REG_DATA_Z: int = 0x36  # Z-axis data start register
    _REG_POWER_CTL: int = 0x2D  # Power-saving features control register
    _AXISES: List[int] = [_REG_DATA_X, _REG_DATA_Y, _REG_DATA_Z]

    def __init__(self, *args, address: int = ADDR, bus: int = 1, **kwargs) -> None:
        """
        Initialize ADXL345.

        :param address: I2C address of the ADXL345
        :param bus: I2C bus number (default 1)
        """
        super().__init__(address=address, bus=bus, *args, **kwargs)
        self.address = address
        self.logger.debug(f"Initialized ADXL345 at address: 0x{self.address:02X}")

    def read(self, axis: Optional[int] = None) -> Union[float, List[float]]:
        """
        Read acceleration value(s) in g.

        :param axis: Axis to read (ADXL345.X, ADXL345.Y, ADXL345.Z) or None for all axes.
        :return: A single value or a list of values.
        """
        if axis is None:
            return [self._read(i) for i in range(3)]
        else:
            return self._read(axis)

    def _read(self, axis: int) -> float:
        result = super().read()  # Call I2C read method (if needed for initialization)
        data = (0x08 << 8) + self._REG_POWER_CTL
        if result:
            self.write(data)
        self.mem_write(0, 0x31)
        self.mem_write(8, 0x2D)
        raw: List[int] = self.mem_read(2, self._AXISES[axis])
        # The first reading might be 0; read again.
        self.mem_write(0, 0x31)
        self.mem_write(8, 0x2D)
        raw = self.mem_read(2, self._AXISES[axis])
        if raw[1] >> 7 == 1:
            raw_1: int = raw[1] ^ 128 ^ 127
            raw_2: int = (raw_1 + 1) * -1
        else:
            raw_2 = raw[1]
        g: int = (raw_2 << 8) | raw[0]
        value: float = g / 256.0
        self.logger.debug(f"ADXL345 axis {axis} reading: {value} g")
        return value


class RGB_LED:
    """Simple 3-pin RGB LED controller."""

    ANODE: int = 1
    CATHODE: int = 0

    def __init__(self, r_pin: PWM, g_pin: PWM, b_pin: PWM, common: int = ANODE) -> None:
        """
        Initialize RGB LED.

        :param r_pin: PWM object for red LED
        :param g_pin: PWM object for green LED
        :param b_pin: PWM object for blue LED
        :param common: RGB_LED.ANODE or RGB_LED.CATHODE (default is ANODE)
        """
        if not isinstance(r_pin, PWM):
            raise TypeError("r_pin must be robot_hat.PWM object")
        if not isinstance(g_pin, PWM):
            raise TypeError("g_pin must be robot_hat.PWM object")
        if not isinstance(b_pin, PWM):
            raise TypeError("b_pin must be robot_hat.PWM object")
        if common not in (self.ANODE, self.CATHODE):
            raise ValueError("common must be RGB_LED.ANODE or RGB_LED.CATHODE")
        self.r_pin: PWM = r_pin
        self.g_pin: PWM = g_pin
        self.b_pin: PWM = b_pin
        self.common: int = common

    def color(self, color: Union[str, Tuple[int, int, int], List[int], int]) -> None:
        """
        Set the LED color.

        :param color: Color specified as a hex string (e.g. "#FF00FF"), 24-bit integer, or (R, G, B) tuple/list.
        """
        if not isinstance(color, (str, int, tuple, list)):
            raise TypeError("color must be str, int, tuple or list")
        if isinstance(color, str):
            color = color.strip("#")
            color = int(color, 16)
        if isinstance(color, (tuple, list)):
            r, g, b = color
        if isinstance(color, int):
            r = (color & 0xff0000) >> 16
            g = (color & 0x00ff00) >> 8
            b = (color & 0x0000ff)
        if self.common == self.ANODE:
            r = 255 - r
            g = 255 - g
            b = 255 - b
        # Convert to percentage for PWM
        r_perc: float = r / 255.0 * 100.0
        g_perc: float = g / 255.0 * 100.0
        b_perc: float = b / 255.0 * 100.0

        self.r_pin.pulse_width_percent(r_perc)
        self.g_pin.pulse_width_percent(g_perc)
        self.b_pin.pulse_width_percent(b_perc)
        logger.debug(f"RGB_LED set to R:{r_perc}%, G:{g_perc}%, B:{b_perc}%")


class Buzzer:
    """Buzzer controller."""

    def __init__(self, buzzer: Union[PWM, Pin]) -> None:
        """
        Initialize buzzer.

        :param buzzer: PWM object for passive buzzer or Pin object for active buzzer.
        """
        if not isinstance(buzzer, (PWM, Pin)):
            raise TypeError("buzzer must be robot_hat.PWM or robot_hat.Pin object")
        self.buzzer: Union[PWM, Pin] = buzzer
        self.buzzer.off()

    def on(self) -> None:
        """Turn on buzzer."""
        if isinstance(self.buzzer, PWM):
            self.buzzer.pulse_width_percent(50)
        elif isinstance(self.buzzer, Pin):
            self.buzzer.on()

    def off(self) -> None:
        """Turn off buzzer."""
        if isinstance(self.buzzer, PWM):
            self.buzzer.pulse_width_percent(0)
        elif isinstance(self.buzzer, Pin):
            self.buzzer.off()

    def freq(self, freq: float) -> None:
        """
        Set frequency of passive buzzer.

        :param freq: Frequency in Hz.
        :raises TypeError: if buzzer is active (Pin)
        """
        if isinstance(self.buzzer, Pin):
            raise TypeError("freq is not supported for active buzzer")
        self.buzzer.freq(freq)

    def play(self, freq: float, duration: Optional[float] = None) -> None:
        """
        Play a tone.

        :param freq: Frequency in Hz.
        :param duration: Duration in seconds (None for continuous).
        :raises TypeError: if buzzer is active (Pin)
        """
        if isinstance(self.buzzer, Pin):
            raise TypeError("play is not supported for active buzzer")
        self.freq(freq)
        self.on()
        if duration is not None:
            time.sleep(duration / 2)
            self.off()
            time.sleep(duration / 2)


class Grayscale_Module:
    """3-channel grayscale sensor module."""

    LEFT: int = 0
    MIDDLE: int = 1
    RIGHT: int = 2

    REFERENCE_DEFAULT: List[int] = [1000, 1000, 1000]

    def __init__(self, pin0: ADC, pin1: ADC, pin2: ADC, reference: Optional[List[int]] = None) -> None:
        """
        Initialize Grayscale Module.

        :param pin0: ADC object for channel 0
        :param pin1: ADC object for channel 1
        :param pin2: ADC object for channel 2
        :param reference: Optional 3-element list for reference voltage values.
        """
        self.pins: Tuple[ADC, ADC, ADC] = (pin0, pin1, pin2)
        for i, pin in enumerate(self.pins):
            if not isinstance(pin, ADC):
                raise TypeError(f"pin{i} must be robot_hat.ADC")
        self._reference: List[int] = reference if reference is not None else self.REFERENCE_DEFAULT

    def reference(self, ref: Optional[List[int]] = None) -> List[int]:
        """
        Get or set the reference values.

        :param ref: A 3-element list to set as reference.
        :return: The current reference list.
        """
        if ref is not None:
            if isinstance(ref, list) and len(ref) == 3:
                self._reference = ref
            else:
                raise TypeError("ref parameter must be a 3-element list.")
        return self._reference

    def read_status(self, datas: Optional[List[int]] = None) -> List[int]:
        """
        Read the sensor status.

        :param datas: Optional list of grayscale values; if None, readings are taken from sensors.
        :return: List of status values (0 for white, 1 for black).
        """
        if self._reference is None:
            raise ValueError("Reference value is not set")
        if datas is None:
            datas = self.read()
        return [0 if data > self._reference[i] else 1 for i, data in enumerate(datas)]

    def read(self, channel: Optional[int] = None) -> List[int]:
        """
        Read grayscale sensor values.

        :param channel: Optional channel index (0, 1, or 2); if None, all channels are read.
        :return: List of grayscale readings.
        """
        if channel is None:
            return [self.pins[i].read() for i in range(3)]
        else:
            return [self.pins[channel].read()]