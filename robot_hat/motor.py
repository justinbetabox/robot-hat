#!/usr/bin/env python3
"""
Motor and Motors classes for Robot Hat.

This module defines a single Motor class for controlling an individual motor
and a Motors collection for managing two motors with persistent settings.
"""
from typing import Optional, Any, List, Tuple
from .basic import BasicClass
from .pwm import PWM
from .pin import Pin
from .filedb import fileDB


class Motor:
    """Motor"""
    PERIOD: int = 4095
    PRESCALER: int = 10
    DEFAULT_FREQ: int = 100  # Hz

    '''
    motor mode 1: (TC1508S)
                pin_a: PWM    pin_b: IO
    forward      pwm            1
    backward     pwm            0
    stop         0              x

    motor mode 2: (TC618S)
                pin_a: PWM    pin_b: PWM
    forward      pwm            0
    backward     0             pwm
    stop         0              0
    brake        1              1
    '''

    def __init__(
        self,
        pwm: PWM,
        dir: Pin,
        is_reversed: bool = False,
        mode: Optional[int] = None,
        freq: int = DEFAULT_FREQ
    ) -> None:
        """
        Initialize a motor

        :param pwm: Motor speed control pwm pin
        :type pwm: robot_hat.pwm.PWM
        :param dir: Motor direction control pin
        :type dir: robot_hat.pin.Pin
        :param is_reversed: True or False
        :type is_reversed: bool
        :param mode: Motor mode (1 or 2)
        :type mode: int or None
        :param freq: PWM frequency in Hz
        :type freq: int
        """
        if mode is None:
            from .device import Devices
            dev = Devices()
            self.mode: int = dev.motor_mode
        else:
            self.mode = mode

        self._speed: float = 0.0
        self._is_reverse: bool = is_reversed

        if self.mode == 1:
            if not isinstance(pwm, PWM):
                raise TypeError("pin_a must be a class PWM")
            if not isinstance(dir, Pin):
                raise TypeError("pin_b must be a class Pin")

            self.pwm: PWM = pwm
            self.dir: Pin = dir
            self.freq: int = freq
            self.pwm.freq(self.freq)
            self.pwm.pulse_width_percent(0.0)

        elif self.mode == 2:
            if not isinstance(pwm, PWM):
                raise TypeError("pin_a must be a class PWM")
            if not isinstance(dir, PWM):
                raise TypeError("pin_b must be a class PWM")

            self.freq = freq
            self.pwm_a: PWM = pwm
            self.pwm_a.freq(self.freq)
            self.pwm_a.pulse_width_percent(0.0)
            self.pwm_b: PWM = dir
            self.pwm_b.freq(self.freq)
            self.pwm_b.pulse_width_percent(0.0)
        else:
            raise ValueError("Unknown motors mode")

    def speed(self, speed: Optional[float] = None) -> Optional[float]:
        """
        Get or set motor speed

        :param speed: Motor speed(-100.0~100.0)
        :type speed: float
        """
        if speed is None:
            return self._speed

        dir_bit = 1 if speed > 0 else 0
        if self._is_reverse:
            dir_bit ^= 1
        speed_val = abs(speed)
        self._speed = speed_val if not self._is_reverse else -speed_val

        if self.mode == 1:
            self.pwm.pulse_width_percent(speed_val)
            self.dir.value(dir_bit)
        elif self.mode == 2:
            if dir_bit == 1:
                self.pwm_a.pulse_width_percent(speed_val)
                self.pwm_b.pulse_width_percent(0.0)
            else:
                self.pwm_a.pulse_width_percent(0.0)
                self.pwm_b.pulse_width_percent(speed_val)
        else:
            raise ValueError("Unknown motors mode")
        return None

    def set_is_reverse(self, is_reversed: bool) -> None:
        """
        Set motor is reversed or not

        :param is_reversed: True or False
        :type is_reversed: bool
        """
        self._is_reverse = is_reversed


class Motors(BasicClass):
    """Motors"""

    DB_FILE: str = "motors.db"
    MOTOR_1_PWM_PIN: str = "P13"
    MOTOR_1_DIR_PIN: str = "D4"
    MOTOR_2_PWM_PIN: str = "P12"
    MOTOR_2_DIR_PIN: str = "D5"
    config_file: str = "/opt/robot_hat/default_motors.config"

    def __init__(
        self,
        db: str = config_file,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """
        Initialize motors with robot_hat.motor.Motor

        :param db: config file path
        :type db: str
        """
        super().__init__(*args, **kwargs)

        self.db = fileDB(db=db, mode='774', owner=None)
        self.left_id: int = int(self.db.get("left", default_value=0) or 0)
        self.right_id: int = int(self.db.get("right", default_value=0) or 0)
        left_reversed = bool(self.db.get("left_reverse", default_value=False))
        right_reversed = bool(self.db.get("right_reverse", default_value=False))

        self.motors: List[Motor] = [
            Motor(PWM(self.MOTOR_1_PWM_PIN), Pin(self.MOTOR_1_DIR_PIN)),
            Motor(PWM(self.MOTOR_2_PWM_PIN), Pin(self.MOTOR_2_DIR_PIN))
        ]
        if self.left_id != 0:
            self.left.set_is_reverse(left_reversed)
        if self.right_id != 0:
            self.right.set_is_reverse(right_reversed)

    def __getitem__(self, key: int) -> Motor:
        """Get specific motor"""
        return self.motors[key-1]

    def stop(self) -> None:
        """Stop all motors"""
        for motor in self.motors:
            motor.speed(0.0)

    @property
    def left(self) -> Motor:
        """left motor"""
        if self.left_id not in (1, 2):
            raise ValueError("left motor is not set yet, set it with set_left_id(1/2)")
        return self.motors[self.left_id-1]

    @property
    def right(self) -> Motor:
        """right motor"""
        if self.left_id not in (1, 2):
            raise ValueError("left motor is not set yet, set it with set_left_id(1/2)")
        return self.motors[self.right_id-1]

    def set_left_id(self, id: int) -> None:
        """
        Set left motor id, this function only need to run once
        It will save the motor id to config file, and load
        the motor id when the class is initialized

        :param id: motor id (1 or 2)
        :type id: int
        """
        if id not in (1, 2):
            raise ValueError("Motor id must be 1 or 2")
        self.left_id = id
        self.db.set("left", id)

    def set_right_id(self, id: int) -> None:
        """
        Set right motor id, this function only need to run once
        It will save the motor id to config file, and load
        the motor id when the class is initialized

        :param id: motor id (1 or 2)
        :type id: int
        """
        if id not in (1, 2):
            raise ValueError("Motor id must be 1 or 2")
        self.right_id = id
        self.db.set("right", id)

    def set_left_reverse(self) -> bool:
        """
        Set left motor reverse, this function only need to run once
        It will save the reversed status to config file, and load
        the reversed status when the class is initialized

        :return: if currently is reversed
        :rtype: bool
        """
        is_reversed = bool(self.db.get("left_reverse", default_value=False))
        is_reversed = not is_reversed
        self.db.set("left_reverse", is_reversed)
        self.left.set_is_reverse(is_reversed)
        return is_reversed

    def set_right_reverse(self) -> bool:
        """
        Set right motor reverse, this function only need to run once
        It will save the reversed status to config file, and load
        the reversed status when the class is initialized

        :return: if currently is reversed
        :rtype: bool
        """
        is_reversed = bool(self.db.get("right_reverse", default_value=False))
        is_reversed = not is_reversed
        self.db.set("right_reverse", is_reversed)
        self.right.set_is_reverse(is_reversed)
        return is_reversed

    def speed(self, left_speed: float, right_speed: float) -> None:
        """
        Set motor speed

        :param left_speed: left motor speed(-100.0~100.0)
        :type left_speed: float
        :param right_speed: right motor speed(-100.0~100.0)
        :type right_speed: float
        """
        self.left.speed(left_speed)
        self.right.speed(right_speed)

    def forward(self, speed: float) -> None:
        """
        Forward

        :param speed: Motor speed(-100.0~100.0)
        :type speed: float
        """
        self.speed(speed, speed)

    def backward(self, speed: float) -> None:
        """
        Backward

        :param speed: Motor speed(-100.0~100.0)
        :type speed: float
        """
        self.speed(-speed, -speed)

    def turn_left(self, speed: float) -> None:
        """
        Left turn

        :param speed: Motor speed(-100.0~100.0)
        :type speed: float
        """
        self.speed(-speed, speed)

    def turn_right(self, speed: float) -> None:
        """
        Right turn

        :param speed: Motor speed(-100.0~100.0)
        :type speed: float
        """
        self.speed(speed, -speed)
