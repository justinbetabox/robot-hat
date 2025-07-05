#!/usr/bin/env python3
"""
Servo motor class for Robot Hat using I2C PWM.
"""
from typing import Union, Optional, Any, List

from .pwm import PWM
from .utils import mapping


class Servo(PWM):
    """Servo motor control via I2C PWM channel."""

    MAX_PW: int = 2500
    """Maximum pulse width in microseconds."""
    MIN_PW: int = 500
    """Minimum pulse width in microseconds."""
    FREQ: int = 50
    """PWM frequency in Hz for servo."""
    PERIOD: int = 4095
    """PWM period count."""

    def __init__(
        self,
        channel: Union[int, str],
        address: Optional[Union[int, List[int]]] = None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """
        Initialize the Servo instance.

        :param channel: PWM channel number (0-14) or name "P0"-"P14".
        :param address: I2C address or list of addresses.
        """
        super().__init__(channel, address, *args, **kwargs)
        # Configure full range period and prescaler
        self.period(self.PERIOD)
        prescaler_value: float = self.CLOCK / self.FREQ / self.PERIOD
        self.prescaler(prescaler_value)

    def angle(self, angle: float) -> None:
        """
        Set the servo angle.

        :param angle: Desired angle in degrees (-90 to 90).
        """
        if not isinstance(angle, (int, float)):
            raise ValueError(f"Angle value should be int or float, not {type(angle)}")
        # Clamp angle to valid range
        clamped: float = max(-90.0, min(90.0, float(angle)))
        self.logger.debug(f"Set angle to: {clamped}")
        # Map angle to pulse width time
        pulse_width_time: float = mapping(clamped, -90.0, 90.0, self.MIN_PW, self.MAX_PW)
        self.logger.debug(f"Pulse width (us): {pulse_width_time}")
        self.pulse_width_time(pulse_width_time)

    def pulse_width_time(self, pulse_width_time: float) -> None:
        """
        Set the servo pulse width based on time in microseconds.

        :param pulse_width_time: Pulse width time (500 to 2500 us).
        """
        # Clamp pulse width to supported range
        clamped_pw: float = max(self.MIN_PW, min(self.MAX_PW, pulse_width_time))
        # Convert to duty cycle fraction
        duty_frac: float = clamped_pw / 20000.0  # period is 20ms
        self.logger.debug(f"Duty fraction: {duty_frac}")
        # Convert to PWM count
        value: int = int(duty_frac * self.PERIOD)
        self.logger.debug(f"PWM count value: {value}")
        self.pulse_width(value)


if __name__ == '__main__':
    # Example usage
    servo = Servo("P0", debug_level='debug')  # type: ignore
    servo.angle(45)
