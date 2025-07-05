#!/usr/bin/env python3
"""
Utility functions for Robot Hat: shell commands, printing, ADC-based battery, speaker control, networking.
"""
import os
import re
import sys
import time
import subprocess
import struct
import math
from typing import List, Union, Optional, Tuple, Any

from .pin import Pin
from .adc import ADC

# ANSI color definitions
GRAY: str = '1;30'
RED: str = '0;31'
GREEN: str = '0;32'
YELLOW: str = '0;33'
BLUE: str = '0;34'
PURPLE: str = '0;35'
DARK_GREEN: str = '0;36'
WHITE: str = '0;37'

_adc_obj: Optional[ADC] = None


def print_color(
    msg: str,
    end: str = '\n',
    file: Any = sys.stdout,
    flush: bool = False,
    color: str = ''
) -> None:
    """
    Print a message with ANSI color.

    :param msg: Message text.
    :param end: End-of-line string.
    :param file: Output file-like object.
    :param flush: Whether to flush after print.
    :param color: ANSI color code string.
    """
    print(f'\033[{color}m{msg}\033[0m', end=end, file=file, flush=flush)


def info(
    msg: str,
    end: str = '\n',
    file: Any = sys.stdout,
    flush: bool = False
) -> None:
    """Print informational message in white."""
    print_color(msg, end=end, file=file, flush=flush, color=WHITE)


def debug(
    msg: str,
    end: str = '\n',
    file: Any = sys.stdout,
    flush: bool = False
) -> None:
    """Print debug message in gray."""
    print_color(msg, end=end, file=file, flush=flush, color=GRAY)


def warn(
    msg: str,
    end: str = '\n',
    file: Any = sys.stdout,
    flush: bool = False
) -> None:
    """Print warning message in yellow."""
    print_color(msg, end=end, file=file, flush=flush, color=YELLOW)


def error(
    msg: str,
    end: str = '\n',
    file: Any = sys.stdout,
    flush: bool = False
) -> None:
    """Print error message in red."""
    print_color(msg, end=end, file=file, flush=flush, color=RED)


def set_volume(value: int) -> None:
    """
    Set the system volume via amixer PCM control.

    :param value: Volume level (0-100).
    """
    level: int = max(0, min(100, value))
    cmd: str = f"sudo amixer -M sset 'PCM' {level}%"
    os.system(cmd)


def run_command(cmd: str) -> Tuple[int, str]:
    """
    Run a shell command and return its exit status and output.

    :param cmd: Command string to execute.
    :return: Tuple of (exit status, combined stdout/stderr output).
    """
    process = subprocess.Popen(
        cmd, shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    output_bytes: bytes = process.stdout.read()  # type: ignore
    result: str = output_bytes.decode('utf-8')
    status: int = process.poll() or 0
    return status, result


def command_exists(cmd: str) -> bool:
    """
    Check if a command exists in PATH.

    :param cmd: Command name.
    :return: True if command found, False otherwise.
    """
    try:
        subprocess.check_output(['which', cmd], stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError:
        return False


def is_installed(cmd: str) -> bool:
    """
    Alias for command_exists; check installation.

    :param cmd: Command name.
    :return: True if installed, False otherwise.
    """
    status, _ = run_command(f"which {cmd}")
    return status == 0


def mapping(
    x: Union[int, float],
    in_min: Union[int, float],
    in_max: Union[int, float],
    out_min: Union[int, float],
    out_max: Union[int, float]
) -> float:
    """
    Map a value from one range to another.

    :param x: Input value.
    :param in_min: Lower bound of input range.
    :param in_max: Upper bound of input range.
    :param out_min: Lower bound of output range.
    :param out_max: Upper bound of output range.
    :return: Mapped output value (float).
    """
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min  # type: ignore


def get_ip(ifaces: Union[str, List[str]] = ['wlan0', 'eth0']) -> Union[str, bool]:
    """
    Get the IPv4 address for one of the provided interfaces.

    :param ifaces: Interface name or list of names.
    :return: IP string if found, False otherwise.
    """
    names = [ifaces] if isinstance(ifaces, str) else ifaces
    for iface in names:
        output: str = os.popen(f'ip addr show {iface}').read()
        match = re.search(r'(?<=inet\s)(\d+\.\d+\.\d+\.\d+)', output)
        if match:
            return match.group(0)
    return False


def reset_mcu() -> None:
    """
    Reset the MCU on the Robot Hat via its reset pin.
    """
    global _adc_obj
    mcu_reset: Pin = Pin("MCURST")
    mcu_reset.off()
    time.sleep(0.01)
    mcu_reset.on()
    time.sleep(0.01)
    mcu_reset.close()


def get_battery_voltage() -> float:
    """
    Read battery voltage via ADC channel A4.

    :return: Battery voltage in volts.
    """
    global _adc_obj
    if not _adc_obj:
        _adc_obj = ADC("A4")  # type: ignore
    raw_v: float = _adc_obj.read_voltage()  # type: ignore
    return raw_v * 3.0


def get_username() -> str:
    """
    Get the current user's username.

    :return: Username string.
    """
    return os.popen('echo ${SUDO_USER:-$LOGNAME}').readline().strip()


def enable_speaker() -> None:
    """
    Enable the speaker via GPIO pin control.
    """
    from . import __device__  # type: ignore
    cmd_tool: str = 'pinctrl' if command_exists('pinctrl') else 'raspi-gpio' if command_exists('raspi-gpio') else ''
    if not cmd_tool:
        error("Can't find `pinctrl` or `raspi-gpio` to enable speaker")
        return
    debug(f"{cmd_tool} set {__device__.spk_en} op dh")
    run_command(f"{cmd_tool} set {__device__.spk_en} op dh")
    # Play short sound to activate speaker
    run_command("play -n trim 0.0 0.5 2>/dev/null")


def disable_speaker() -> None:
    """
    Disable the speaker via GPIO pin control.
    """
    from . import __device__  # type: ignore
    cmd_tool: str = 'pinctrl' if command_exists('pinctrl') else 'raspi-gpio' if command_exists('raspi-gpio') else ''
    if not cmd_tool:
        error("Can't find `pinctrl` or `raspi-gpio` to disable speaker")
        return
    debug(f"{cmd_tool} set {__device__.spk_en} op dl")
    run_command(f"{cmd_tool} set {__device__.spk_en} op dl")
