# Robot Hat Python Library

A modern, easy-to-use Python library for the Betabox Robot Hat expansion board on Raspberry Pi.

Supports motor control, sensors, PWM, TTS, audio, I2C/SPI peripherals, and more.

---

## Features

- Simple Python API for robot control
- Compatible with Raspberry Pi 4B, Bookworm 64-bit (desktop)
- Motor, servo, sensor, I2C, SPI, and audio support
- Example scripts included

---

## Requirements

- **Hardware:** Raspberry Pi 4B (recommended)
- **OS:** Raspberry Pi OS Bookworm (64-bit, desktop/full image)
- **Internet access:** Required for install

---

## Installation

1. **Clone the Repository**

    ```sh
    git clone https://github.com/justinbetabox/robot-hat.git
    cd robot-hat
    ```

2. **Run the Installer (one step)**

    ```sh
    sudo python3 install.py
    ```

    This will:
    - Install all required system and Python dependencies
    - Enable I2C and SPI hardware interfaces
    - Copy device tree overlays (if present)
    - Install the robot-hat Python library

3. **Reboot**

    ```sh
    sudo reboot
    ```

---

## Post-Install Check

Test if installation succeeded:

```sh
python3 -c "from robot_hat import version; print('robot-hat version:', version.__version__)"
```

If no errors, install succeeded!

---

## Quick Start Example

Here’s a simple example to test your hardware:

```python
from robot_hat import Motor
import time

motor = Motor(5, 6)
motor.set_speed(50)
time.sleep(2)
motor.set_speed(0)
```

---

## Device Tree Overlays

- The installer copies overlays from `./dtoverlays` to `/boot/firmware/overlays/` (if present).
- **Note:** You may need to manually add a line to `/boot/firmware/config.txt` to enable overlays, e.g.:
    ```
    dtoverlay=myoverlay
    ```
- **Reboot is required** after enabling overlays.

---

## Troubleshooting

- If you see `ModuleNotFoundError` for any library, re-run the install or ensure your Pi OS is up to date.
- Make sure you are running on Raspberry Pi OS Bookworm (64-bit).
- If hardware (motors, sensors) are not detected, ensure I2C and SPI are enabled (`raspi-config`) and overlays (if needed) are active in `config.txt`.

---

## Permissions

- The installer must be run with `sudo` to set up system dependencies and hardware interfaces.
- For regular use, you can run Python scripts as your normal user (except when accessing hardware that needs root).

---

## Platform Support

This library is **intended for use only on Raspberry Pi 4B with Bookworm 64-bit (desktop/full image)**.

Other platforms or OS versions are not officially supported.

---

## Issues & Contributions

- [Open an Issue](https://github.com/justinbetabox/robot-hat/issues) for bugs or questions.
- Contributions and PRs are welcome!

---

## License

GNU GPLv3 (see [LICENSE](LICENSE))
