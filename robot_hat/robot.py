#!/usr/bin/env python3
"""
Robot class for making a servo robot with Robot HAT.

This class supports servo initialization, controlled movement with speed settings,
servo offset management, and more.
"""
import os
import time
from typing import List, Optional, Union, Dict, Any

from .basic import BasicClass
from .pwm import PWM
from .servo import Servo
from .filedb import fileDB

# Determine the current user and config file path
User: str = os.popen('echo ${SUDO_USER:-$LOGNAME}').readline().strip()
UserHome: str = os.popen(f'getent passwd {User} | cut -d: -f6').readline().strip()
config_file: str = f'{UserHome}/.config/robot-hat/robot-hat.conf'


class Robot(BasicClass):
    """
    Robot class for making a servo robot with Robot HAT.

    Supports servo initialization, controlled movement with speed settings,
    servo offset management, and more.
    """
    # Predefined move sequences
    move_list: Dict[str, List[List[float]]] = {}
    # Maximum degrees per second to prevent over-speeding
    max_dps: float = 428.0  # degrees per second

    def __init__(
        self,
        pin_list: List[int],
        db: str = config_file,
        name: Optional[str] = None,
        init_angles: Optional[List[float]] = None,
        init_order: Optional[List[int]] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize the Robot.

        :param pin_list: List of pin numbers for servos.
        :param db: Path to configuration file.
        :param name: Optional robot name.
        :param init_angles: Optional list of initial angles for each servo.
        :param init_order: Optional list specifying servo initialization order.
        """
        super().__init__(**kwargs)
        self.pin_num: int = len(pin_list)
        self.name: str = name if name is not None else 'other'
        # Configuration key for servo offsets
        self.offset_value_name: str = f"{self.name}_servo_offset_list"
        # Load or initialize servo offsets
        self.db = fileDB(db=db, mode='774', owner=User)
        raw_offsets: str = self.db.get(self.offset_value_name, default_value=str(self.new_list(0)))  # type: ignore
        self.offset: List[float] = [float(x) for x in raw_offsets.strip('[]').split(',')]
        # Initialize position trackers
        self.servo_positions: List[float] = self.new_list(0)
        self.origin_positions: List[float] = self.new_list(0)
        self.calibrate_position: List[float] = self.new_list(0)
        self.direction: List[int] = self.new_list(1)  # 1 or -1
        # Initialize angles
        if init_angles is None:
            init_angles = [0.0] * self.pin_num
        if len(init_angles) != self.pin_num:
            raise ValueError('Initial angles length must match number of pins.')
        # Default initialization order
        if init_order is None:
            init_order = list(range(self.pin_num))
        # Create servo objects
        self.servo_list: List[Servo] = []
        for angle, pin in zip(init_angles, pin_list):
            servo = Servo(pin)
            self.servo_list.append(servo)
            self.servo_positions[len(self.servo_list)-1] = angle
        # Move servos to starting positions in the given order
        for idx in init_order:
            angle_to_set: float = self.offset[idx] + self.servo_positions[idx]
            self.servo_list[idx].angle(angle_to_set)
            self.logger.debug(f"Servo {idx} set to angle {angle_to_set}")
            time.sleep(0.15)
        self.last_move_time: float = time.time()

    def new_list(self, default_value: Union[int, float]) -> List[Union[int, float]]:
        """
        Create a list of length equal to number of servos, filled with default_value.

        :param default_value: Value to fill the list with.
        :return: List of default values.
        """
        return [default_value] * self.pin_num

    def servo_write_raw(self, angle_list: List[float]) -> None:
        """
        Directly write raw angles to servos.

        :param angle_list: List of angles for each servo.
        """
        for i, angle in enumerate(angle_list):
            self.servo_list[i].angle(angle)
            self.logger.debug(f"Raw angle written to servo {i}: {angle}")

    def servo_write_all(self, angles: List[float]) -> None:
        """
        Write angles to servos, applying offsets and origins.

        :param angles: List of target angles.
        """
        rel_angles: List[float] = []
        for i in range(self.pin_num):
            rel = self.direction[i] * (self.origin_positions[i] + angles[i] + self.offset[i])
            rel_angles.append(rel)
        self.servo_write_raw(rel_angles)
        self.logger.debug(f"Servo angles set to: {rel_angles}")

    def servo_move(
        self,
        targets: List[float],
        speed: Union[int, float] = 50,
        bpm: Optional[Union[int, float]] = None
    ) -> None:
        """
        Smoothly move servos to target angles at given speed or bpm.

        :param targets: Target angles for each servo.
        :param speed: Movement speed (0-100).
        :param bpm: Optional beats per minute timing.
        """
        speed = max(0, min(100, speed))
        step_time_ms: float = 10.0
        deltas: List[float] = []
        for i in range(self.pin_num):
            diff = targets[i] - self.servo_positions[i]
            deltas.append(diff)
        max_delta: float = max(abs(d) for d in deltas)
        if max_delta == 0:
            time.sleep(step_time_ms / 1000)
            return
        # Determine total time (ms)
        if bpm is not None:
            total_time_ms: float = 60_000 / bpm
        else:
            total_time_ms = -9.9 * speed + 1000
        # Cap based on max degrees per second
        max_steps: int = int(total_time_ms / step_time_ms)
        step_increments: List[float] = [d / max_steps for d in deltas]
        self.logger.debug(f"Moving servos: max_delta={max_delta}, steps={max_steps}")
        for _ in range(max_steps):
            start = time.time()
            for i in range(self.pin_num):
                self.servo_positions[i] += step_increments[i]
            self.servo_write_all(self.servo_positions)
            elapsed = (time.time() - start)
            time.sleep(max(0, step_time_ms/1000 - elapsed))

    def do_action(self, motion_name: str, step: int = 1, speed: Union[int, float] = 50) -> None:
        """
        Execute a predefined sequence of moves.

        :param motion_name: Key in move_list.
        :param step: Number of repetitions.
        :param speed: Speed for each move.
        """
        if motion_name not in self.move_list:
            raise ValueError(f"Motion '{motion_name}' not defined.")
        for _ in range(step):
            for m in self.move_list[motion_name]:
                self.servo_move(m, speed)
                self.logger.debug(f"Executed motion '{motion_name}': {m}")

    def set_offset(self, offset_list: List[float]) -> None:
        """
        Update servo offsets and persist to config.

        :param offset_list: New offset angles.
        """
        clipped: List[float] = [max(-20, min(20, o)) for o in offset_list]
        self.db.set(self.offset_value_name, str(clipped))
        self.offset = clipped
        self.logger.debug(f"Servo offsets set: {clipped}")

    def calibration(self) -> None:
        """Move all servos to calibration (home) positions."""
        self.servo_positions = list(self.calibrate_position)
        self.servo_write_all(self.servo_positions)
        self.logger.debug("Servos calibrated to home positions.")

    def reset(self, lst: Optional[List[float]] = None) -> None:
        """
        Reset servos to original or given positions.

        :param lst: Optional list of reset positions.
        """
        if lst is None:
            self.servo_positions = self.new_list(0)
        else:
            self.servo_positions = lst
        self.servo_write_all(self.servo_positions)
        self.logger.debug(f"Servos reset to: {self.servo_positions}")

    def soft_reset(self) -> None:
        """Soft reset by moving all servos to zero positions."""
        zeros: List[float] = self.new_list(0)
        self.servo_write_all(zeros)
        self.logger.debug("Performed soft reset on servos.")