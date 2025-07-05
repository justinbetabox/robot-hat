#!/usr/bin/env python3
""" Robot Hat Library """

# Core components
from .adc import ADC
from .filedb import fileDB
from .config import Config
from .i2c import I2C
from .music import Music
from .motor import Motor, Motors
from .pin import Pin
from .pwm import PWM
from .servo import Servo
from .tts import TTS

# Sensor and actuator modules
from .modules import Ultrasonic, ADXL345, RGB_LED, Buzzer, Grayscale_Module

# Utility functions
from .utils import (
    print_color, info, debug, warn, error,
    set_volume, run_command, command_exists, is_installed,
    mapping, get_ip, reset_mcu, get_battery_voltage,
    get_username, enable_speaker, disable_speaker,
)

# High-level interface
from .robot import Robot
from .device import Devices
from .version import __version__

# Singleton for device info
enabled_device = Devices()


def __usage__() -> None:
    """Show CLI usage."""
    print('''
Usage: robot_hat [option]
  reset_mcu          Reset MCU on Robot Hat
  enable_speaker     Enable speaker
  disable_speaker    Disable speaker
  version            Get Robot Hat library version
  info               Get hat information
''')
    quit()


def get_firmware_version() -> str:
    """Read firmware version from I²C."""
    ADDR = [0x14, 0x15]
    VERSION_REG_ADDR = 0x05
    i2c = I2C(ADDR)
    version = i2c.mem_read(3, VERSION_REG_ADDR)
    return f"{version[0]}.{version[1]}.{version[2]}"


def __main__() -> None:
    """CLI entry point."""
    import sys
    if len(sys.argv) == 2:
        option = sys.argv[1]
        if option == "reset_mcu":
            reset_mcu()
            info("Onboard MCU reset.")
        elif option == "enable_speaker":
            info("Enabling Robot Hat speaker.")
            enable_speaker()
        elif option == "disable_speaker":
            info("Disabling Robot Hat speaker.")
            disable_speaker()
        elif option == "version":
            info(f"Robot Hat library version: {__version__}")
        elif option == "info":
            info(f"HAT name: {enabled_device.name}")
            info(f"PCB ID: O{enabled_device.product_id}V{enabled_device.product_ver}")
            info(f"Vendor: {enabled_device.vendor}")
            firmware_ver = get_firmware_version()
            info(f"Firmware version: {firmware_ver}")
        else:
            warn("Unknown option.")
            __usage__()
    else:
        __usage__()


if __name__ == "__main__":
    __main__()
