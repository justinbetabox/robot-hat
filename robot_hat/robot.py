#!/usr/bin/env python3
from .basic import BasicClass
from .pwm import PWM
from .servo import Servo
import time
from .filedb import fileDB
import os
from typing import List, Optional, Union

# Get user and user home directory
User = os.popen('echo ${SUDO_USER:-$LOGNAME}').readline().strip()
UserHome = os.popen('getent passwd %s | cut -d: -f6' % User).readline().strip()
config_file = f'{UserHome}/.config/robot-hat/robot-hat.conf'


class Robot(BasicClass):
    """
    Robot class for making a servo robot with Robot HAT.
    
    This class supports servo initialization, controlled movement with speed settings,
    servo offset management, and more. It is used by various Pi-series robots from SunFounder.
    """

    move_list = {}  # Preset actions
    max_dps: int = 428  # degrees per second (e.g. 60°/0.14s ≈ 428 dps)

    def __init__(self, pin_list: List[int], db: str = config_file,
                 name: Optional[str] = None, init_angles: Optional[List[float]] = None,
                 init_order: Optional[List[int]] = None, **kwargs) -> None:
        """
        Initialize the Robot class.

        :param pin_list: List of pin numbers (e.g. [0, 1, 2, ...]) for servos.
        :param db: Config file path.
        :param name: Robot name.
        :param init_angles: List of initial servo angles.
        :param init_order: List defining the initialization order for servos.
                           This helps to stagger servo movements to prevent power dips.
        """
        super().__init__(**kwargs)
        self.servo_list: List[Servo] = []
        self.pin_num: int = len(pin_list)
        self.name: str = name if name is not None else 'other'

        self.offset_value_name: str = f"{self.name}_servo_offset_list"
        # Get offset from fileDB or create new list of zeros
        self.db = fileDB(db=db, mode='774', owner=User)
        temp = self.db.get(self.offset_value_name, default_value=str(self.new_list(0)))
        temp_list = [float(i.strip()) for i in temp.strip("[]").split(",")]
        self.offset: List[float] = temp_list

        # Initialize parameters
        self.servo_positions: List[float] = self.new_list(0)
        self.origin_positions: List[float] = self.new_list(0)
        self.calibrate_position: List[float] = self.new_list(0)
        self.direction: List[int] = self.new_list(1)

        # Initialize servo angles (if not provided, default to 0)
        if init_angles is None:
            init_angles = [0] * self.pin_num
        elif len(init_angles) != self.pin_num:
            raise ValueError('The number of initial angles does not match the number of pins.')

        if init_order is None:
            init_order = list(range(self.pin_num))

        # Create servo instances and set initial positions.
        for i, pin in enumerate(pin_list):
            self.servo_list.append(Servo(pin))
            self.servo_positions[i] = init_angles[i]
        # Move servos one by one in the specified order.
        for i in init_order:
            angle_to_set = self.offset[i] + self.servo_positions[i]
            self.servo_list[i].angle(angle_to_set)
            self.logger.debug(f"Servo {i} set to angle {angle_to_set}")
            time.sleep(0.15)

        self.last_move_time: float = time.time()

    def new_list(self, default_value: Union[int, float]) -> List[Union[int, float]]:
        """
        Create a list with length equal to the number of servos, all elements set to default_value.

        :param default_value: The default value for each servo.
        :return: A list of default values.
        """
        return [default_value] * self.pin_num

    def servo_write_raw(self, angle_list: List[float]) -> None:
        """
        Set servo angles to specific raw angles.

        :param angle_list: List of servo angles.
        """
        for i in range(self.pin_num):
            self.servo_list[i].angle(angle_list[i])
            self.logger.debug(f"Raw angle for servo {i}: {angle_list[i]}")

    def servo_write_all(self, angles: List[float]) -> None:
        """
        Set servo angles to specific angles, taking into account the origin and offset.

        :param angles: List of servo angles.
        """
        rel_angles: List[float] = []
        for i in range(self.pin_num):
            # Calculate relative angle: direction * (origin + given angle + offset)
            rel = self.direction[i] * (self.origin_positions[i] + angles[i] + self.offset[i])
            rel_angles.append(rel)
        self.servo_write_raw(rel_angles)
        self.logger.debug(f"Servos set to angles: {rel_angles}")

    def servo_move(self, targets: List[float], speed: Union[int, float] = 50, bpm: Optional[Union[int, float]] = None) -> None:
        """
        Move servos to specific target angles with a given speed or bpm.

        :param targets: List of target servo angles.
        :param speed: Speed of movement (0 to 100).
        :param bpm: Beats per minute (optional).
        """
        speed = max(0, speed)
        speed = min(100, speed)
        step_time: float = 10  # in milliseconds

        delta: List[float] = []
        absdelta: List[float] = []
        steps: List[float] = []

        for i in range(self.pin_num):
            diff = targets[i] - self.servo_positions[i]
            delta.append(diff)
            absdelta.append(abs(diff))

        max_delta = int(max(absdelta))
        if max_delta == 0:
            time.sleep(step_time / 1000)
            return

        if bpm:
            total_time = 60 / bpm * 1000  # total time per beat in milliseconds
        else:
            total_time = -9.9 * speed + 1000  # linear mapping from speed to time in ms

        current_max_dps = max_delta / total_time * 1000  # degrees per second
        if current_max_dps > self.max_dps:
            total_time = max_delta / self.max_dps * 1000

        max_step = int(total_time / step_time)

        for i in range(self.pin_num):
            steps.append(delta[i] / max_step)

        self.logger.debug(f"Moving servos with max delta: {max_delta}, steps: {max_step}")

        for _ in range(max_step):
            start_time = time.time()
            for j in range(self.pin_num):
                self.servo_positions[j] += steps[j]
            self.servo_write_all(self.servo_positions)
            elapsed = time.time() - start_time
            delay = max(0, step_time / 1000 - elapsed)
            time.sleep(delay)

    def do_action(self, motion_name: str, step: int = 1, speed: Union[int, float] = 50) -> None:
        """
        Execute a preset action.

        :param motion_name: Name of the preset action.
        :param step: Number of times to execute the action.
        :param speed: Speed of motion.
        """
        if motion_name not in self.move_list:
            raise ValueError(f"Motion '{motion_name}' is not defined in move_list.")
        for _ in range(step):
            for motion in self.move_list[motion_name]:
                self.servo_move(motion, speed)
                self.logger.debug(f"Action '{motion_name}' executed step with motion: {motion}")

    def set_offset(self, offset_list: List[float]) -> None:
        """
        Set the servo offsets and save them to the configuration file.

        :param offset_list: List of servo offset angles.
        """
        # Limit offset values to between -20 and 20
        offset_list = [min(max(offset, -20), 20) for offset in offset_list]
        self.db.set(self.offset_value_name, str(offset_list))
        self.offset = offset_list
        self.logger.debug(f"Servo offsets updated: {offset_list}")

    def calibration(self) -> None:
        """Move all servos to the calibration (home) position."""
        self.servo_positions = self.calibrate_position
        self.servo_write_all(self.servo_positions)
        self.logger.debug("Servos calibrated to home position.")

    def reset(self, lst: Optional[List[float]] = None) -> None:
        """
        Reset servos to their original positions.

        :param lst: Optional list of positions; if not provided, resets to zeros.
        """
        if lst is None:
            self.servo_positions = self.new_list(0)
        else:
            self.servo_positions = lst
        self.servo_write_all(self.servo_positions)
        self.logger.debug(f"Servos reset to positions: {self.servo_positions}")

    def soft_reset(self) -> None:
        """Perform a soft reset by moving servos to zero positions."""
        temp_list = self.new_list(0)
        self.servo_write_all(temp_list)
        self.logger.debug("Performed soft reset on servos.")