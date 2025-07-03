#!/usr/bin/env python3
import os
import re
import sys
import time
import subprocess
import struct
import math
from typing import List, Union, Optional, Tuple, Any

from .pin import Pin

# ANSI color definitions
GRAY = '1;30'
RED = '0;31'
GREEN = '0;32'
YELLOW = '0;33'
BLUE = '0;34'
PURPLE = '0;35'
DARK_GREEN = '0;36'
WHITE = '0;37'

_adc_obj: Optional[Any] = None

def print_color(msg: str, end: str = '\n', file: Any = sys.stdout, flush: bool = False, color: str = '') -> None:
    """Print message with ANSI color."""
    print(f'\033[{color}m{msg}\033[0m', end=end, file=file, flush=flush)

def info(msg: str, end: str = '\n', file: Any = sys.stdout, flush: bool = False) -> None:
    """Print informational message in white."""
    print_color(msg, end=end, file=file, flush=flush, color=WHITE)

def debug(msg: str, end: str = '\n', file: Any = sys.stdout, flush: bool = False) -> None:
    """Print debug message in gray."""
    print_color(msg, end=end, file=file, flush=flush, color=GRAY)

def warn(msg: str, end: str = '\n', file: Any = sys.stdout, flush: bool = False) -> None:
    """Print warning message in yellow."""
    print_color(msg, end=end, file=file, flush=flush, color=YELLOW)

def error(msg: str, end: str = '\n', file: Any = sys.stdout, flush: bool = False) -> None:
    """Print error message in red."""
    print_color(msg, end=end, file=file, flush=flush, color=RED)

def set_volume(value: int) -> None:
    """
    Set the system volume.

    :param value: Volume level (0-100)
    """
    value = min(100, max(0, value))
    cmd = f"sudo amixer -M sset 'PCM' {value}%"
    os.system(cmd)

def run_command(cmd: str) -> Tuple[int, str]:
    """
    Run a shell command and return its exit status and output.

    :param cmd: Command to execute.
    :return: A tuple (status, output)
    """
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = process.stdout.read().decode('utf-8')
    status = process.poll()
    return status, result

def command_exists(cmd: str) -> bool:
    """
    Check if a command exists in the system.

    :param cmd: Command name.
    :return: True if the command exists, False otherwise.
    """
    try:
        subprocess.check_output(['which', cmd], stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError:
        return False

def is_installed(cmd: str) -> bool:
    """
    Check if a command is installed.

    :param cmd: Command name.
    :return: True if installed, otherwise False.
    """
    status, _ = run_command(f"which {cmd}")
    return status == 0

def mapping(x: Union[int, float], in_min: Union[int, float], in_max: Union[int, float],
            out_min: Union[int, float], out_max: Union[int, float]) -> Union[int, float]:
    """
    Map a value from one range to another.

    :param x: Input value.
    :param in_min: Input range minimum.
    :param in_max: Input range maximum.
    :param out_min: Output range minimum.
    :param out_max: Output range maximum.
    :return: Mapped value.
    """
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def get_ip(ifaces: Union[str, List[str]] = ['wlan0', 'eth0']) -> Union[str, bool]:
    """
    Get the IPv4 address for a given network interface.

    :param ifaces: Interface name or list of interface names.
    :return: IP address as a string, or False if not found.
    """
    if isinstance(ifaces, str):
        ifaces = [ifaces]
    for iface in ifaces:
        result = os.popen(f'ip addr show {iface}').read()
        match = re.search(r'(?<=inet\s)(\d+\.\d+\.\d+\.\d+)', result)
        if match:
            return match.group(0)
    return False

def reset_mcu() -> None:
    """
    Reset the MCU on the Robot Hat.
    
    Useful if the MCU gets stuck in an I2C loop.
    """
    mcu_reset = Pin("MCURST")
    mcu_reset.off()
    time.sleep(0.01)
    mcu_reset.on()
    time.sleep(0.01)
    mcu_reset.close()

def get_battery_voltage() -> float:
    """
    Get the battery voltage.

    :return: Battery voltage in volts.
    """
    global _adc_obj
    from .adc import ADC
    if not isinstance(_adc_obj, ADC):
        _adc_obj = ADC("A4")
    raw_voltage = _adc_obj.read_voltage()
    voltage = raw_voltage * 3
    return voltage

def get_username() -> str:
    """
    Get the username of the current user.

    :return: Username as a string.
    """
    return os.popen('echo ${SUDO_USER:-$LOGNAME}').readline().strip()

def enable_speaker() -> None:
    """
    Enable the speaker on the device.
    """
    from . import __device__
    pincmd = ''
    if command_exists("pinctrl"):
        pincmd = 'pinctrl'
    elif command_exists("raspi-gpio"):
        pincmd = 'raspi-gpio'
    else:
        error("Can't find `pinctrl` or `raspi-gpio` to enable speaker")
        return

    debug(f"{pincmd} set {__device__.spk_en} op dh")
    run_command(f"{pincmd} set {__device__.spk_en} op dh")
    # Play a short sound to initialize speaker
    run_command("play -n trim 0.0 0.5 2>/dev/null")

def disable_speaker() -> None:
    """
    Disable the speaker on the device.
    """
    from . import __device__
    pincmd = ''
    if command_exists("pinctrl"):
        pincmd = 'pinctrl'
    elif command_exists("raspi-gpio"):
        pincmd = 'raspi-gpio'
    else:
        error("Can't find `pinctrl` or `raspi-gpio` to disable speaker")
        return

    debug(f"{pincmd} set {__device__.spk_en} op dl")
    run_command(f"{pincmd} set {__device__.spk_en} op dl")