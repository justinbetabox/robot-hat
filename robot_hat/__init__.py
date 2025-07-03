#!/usr/bin/env python3
"""
Robot Hat Library
"""

from .adc import ADC
from .filedb import fileDB
from .config import Config
from .i2c import I2C
from .modules import *
from .music import Music
from .motor import Motor, Motors
from .pin import Pin
from .pwm import PWM
from .servo import Servo
from .tts import TTS
from .utils import *  # This should provide functions like reset_mcu, info, warn, enable_speaker, disable_speaker, etc.
from .robot import Robot
from .version import __version__

from .device import Devices
__device__ = Devices()


def __usage__() -> None:
    print('''
Usage: robot_hat [option]

reset_mcu               Reset MCU on Robot Hat
enable_speaker          Enable speaker
disable_speaker         Disable speaker
version                 Get Robot Hat library version
info                    Get hat information
    ''')
    quit()


def get_firmware_version() -> str:
    ADDR = [0x14, 0x15]
    VERSION_REG_ADDR = 0x05
    i2c = I2C(ADDR)
    version = i2c.mem_read(3, VERSION_REG_ADDR)
    # Format version as "X.Y.Z"
    return f"{version[0]}.{version[1]}.{version[2]}"


def __main__() -> None:
    import sys
    if len(sys.argv) == 2:
        option = sys.argv[1]
        if option == "reset_mcu":
            reset_mcu()
            info("Onboard MCU reset.")
        elif option == "enable_speaker":
            info("Enabling Robot-HAT speaker.")
            enable_speaker()
        elif option == "disable_speaker":
            info("Disabling Robot-HAT speaker.")
            disable_speaker()
        elif option == "version":
            info(f"Robot-HAT library version: {__version__}")
        elif option == "info":
            info(f'HAT name: {__device__.name}')
            info(f'PCB ID: O{__device__.product_id}V{__device__.product_ver}')
            info(f'Vendor: {__device__.vendor}')
            firmware_ver = get_firmware_version()
            info(f"Firmware version: {firmware_ver}")
        else:
            warn("Unknown option.")
            __usage__()
    else:
        __usage__()


if __name__ == "__main__":
    __main__()