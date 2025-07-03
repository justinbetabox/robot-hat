#!/usr/bin/env python3
from .pwm import PWM
from .utils import mapping


class Servo(PWM):
    """Servo motor class"""
    MAX_PW = 2500
    MIN_PW = 500
    FREQ = 50
    PERIOD = 4095

    def __init__(self, channel: int or str, address=None, *args, **kwargs) -> None:
        """
        Initialize the servo motor class

        :param channel: PWM channel number (0-14 or "P0"-"P14")
        :type channel: int or str
        """
        super().__init__(channel, address, *args, **kwargs)
        self.period(self.PERIOD)
        prescaler = self.CLOCK / self.FREQ / self.PERIOD
        self.prescaler(prescaler)

    def angle(self, angle: float) -> None:
        """
        Set the angle of the servo motor

        :param angle: Angle (-90 to 90)
        :type angle: float
        """
        if not isinstance(angle, (int, float)):
            raise ValueError("Angle value should be int or float, not %s" % type(angle))
        if angle < -90:
            angle = -90
        if angle > 90:
            angle = 90
        self.logger.debug(f"Set angle to: {angle}")
        pulse_width_time = mapping(angle, -90, 90, self.MIN_PW, self.MAX_PW)
        self.logger.debug(f"Pulse width: {pulse_width_time}")
        self.pulse_width_time(pulse_width_time)

    def pulse_width_time(self, pulse_width_time: float) -> None:
        """
        Set the pulse width of the servo motor

        :param pulse_width_time: Pulse width time (500 to 2500)
        :type pulse_width_time: float
        """
        if pulse_width_time > self.MAX_PW:
            pulse_width_time = self.MAX_PW
        if pulse_width_time < self.MIN_PW:
            pulse_width_time = self.MIN_PW

        pwr = pulse_width_time / 20000.0
        self.logger.debug(f"pulse width rate: {pwr}")
        value = int(pwr * self.PERIOD)
        self.logger.debug(f"pulse width value: {value}")
        self.pulse_width(value)