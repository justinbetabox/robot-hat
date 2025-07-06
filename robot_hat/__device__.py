# robot_hat/__device__.py

"""
Auto-detected Robot Hat device info singleton.
This module exports the key attributes code expects:
  - spk_en        (GPIO pin for speaker enable)
  - motor_mode    (1 or 2 depending on your HAT version)
  - plus any other device info from Devices()
"""

from .device import Devices

# the singleton instance
_dev = Devices()

# expose the attributes your code imports
spk_en = _dev.spk_en
motor_mode = _dev.motor_mode

# if you ever need the full object, keep it too:
# __device__ = _dev