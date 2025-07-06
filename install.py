#!/usr/bin/env python3
"""
robot-hat install.py

System/hardware/software setup for robot-hat on Raspberry Pi 4B, Bookworm 64-bit.

- Installs required apt packages (skips if already installed)
- Enables I2C/SPI interfaces
- Copies overlays if present
- Installs Python dependencies and robot-hat package via pip

Run with: sudo python3 install.py
"""

import os, sys, subprocess, time, threading

# --- Colored output helpers ---
def print_info(msg): print(f"\033[0;36m{msg}\033[0m")
def print_warn(msg): print(f"\033[0;33m{msg}\033[0m")
def print_err(msg): print(f"\033[0;31m{msg}\033[0m")
def print_success(msg): print(f"\033[0;32m{msg}\033[0m")

# --- Spinner ---
def working_tip():
    char = ['/', '-', '\\', '|']
    i = 0
    while at_work_tip_sw:
        i = (i + 1) % 4
        sys.stdout.write('\033[?25l' + f'{char[i]}\033[1D')
        sys.stdout.flush()
        time.sleep(0.3)
    sys.stdout.write(' \033[1D\033[?25h')
    sys.stdout.flush()

# --- Command runner ---
def run_command(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = p.stdout.read().decode()
    status = p.wait()
    return status, output.strip()

def do(msg, cmd):
    print(f" - {msg} ... ", end='', flush=True)
    global at_work_tip_sw
    at_work_tip_sw = True
    _thread = threading.Thread(target=working_tip)
    _thread.daemon = True
    _thread.start()
    status, result = run_command(cmd)
    at_work_tip_sw = False
    _thread.join()
    if status == 0:
        print("Done")
        return True
    else:
        print("Error")
        errors.append(f"{msg}:\n  {result}")
        return False

# --- Checks ---
def is_apt_package_installed(pkg):
    status, _ = run_command(f"dpkg -s {pkg}")
    return status == 0

def is_rpi_4b():
    try:
        with open('/proc/device-tree/model') as f:
            return 'Raspberry Pi 4' in f.read()
    except Exception:
        return False

def is_bookworm():
    try:
        with open('/etc/os-release') as f:
            return 'bookworm' in f.read()
    except Exception:
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    if os.geteuid() != 0:
        print_err("Script must be run as root. Try 'sudo python3 install.py'")
        sys.exit(1)

    print_info("robot-hat: System/Hardware/Software Setup (Bookworm 64, Pi 4B)")

    # Platform/OS warnings
    if not is_rpi_4b():
        print_warn("Warning: Not running on Raspberry Pi 4B. Proceed at your own risk.")
    if not is_bookworm():
        print_warn("Warning: Detected OS is not Bookworm. Proceed at your own risk.")

    errors = []
    at_work_tip_sw = False

    # --- System dependencies ---
    APT_INSTALL_LIST = [
        "raspi-config",
        "i2c-tools",
        "espeak",
        "libsdl2-dev",
        "libsdl2-mixer-dev",
        "portaudio19-dev",
        "sox",
        "libttspico-utils"
    ]

    print_info("\nInstalling system dependencies via apt...")
    do("apt-get update", "apt-get update")
    for pkg in APT_INSTALL_LIST:
        if not is_apt_package_installed(pkg):
            do(f"apt install {pkg}", f"apt-get install -y {pkg}")
        else:
            print_success(f" - {pkg} already installed.")

    # --- Interfaces ---
    print_info("\nEnabling I2C and SPI interfaces...")
    do("Enable I2C", "raspi-config nonint do_i2c 0")
    do("Enable SPI", "raspi-config nonint do_spi 0")

    # --- Overlays ---
    OVERLAYS_SRC = "./dtoverlays"
    OVERLAYS_DST = "/boot/firmware/overlays/"
    overlays_copied = False
    if os.path.isdir(OVERLAYS_SRC) and os.path.isdir(OVERLAYS_DST):
        for fname in os.listdir(OVERLAYS_SRC):
            src = os.path.join(OVERLAYS_SRC, fname)
            dst = os.path.join(OVERLAYS_DST, fname)
            if not os.path.isfile(dst) or (os.path.getmtime(src) > os.path.getmtime(dst)):
                do(f"Copy overlay {fname}", f"cp -u '{src}' '{dst}'")
                overlays_copied = True
        if not overlays_copied:
            print_success(" - All overlays already up to date.")
    else:
        print_warn("Overlay source or destination not found. Skipping overlay copy.")

    # --- Install Python dependencies and robot-hat package ---
    print_info("\nInstalling Python dependencies and robot-hat package (this may take a few minutes)...")
    # Use --break-system-packages if available (for Bookworm pip)
    status, _ = run_command("pip3 help install | grep break-system-packages")
    pip_extra = "--break-system-packages" if status == 0 else ""
    do("pip install .", f"python3 -m pip install . {pip_extra}")

    # --- Summary ---
    print_info("\n========== INSTALL SUMMARY ==========")
    if not errors:
        print_success("System, hardware, and Python setup finished successfully!")
    else:
        print_err("Some errors occurred during setup:")
        for e in errors:
            print_err(f"- {e}")
        print_warn("Please review the errors above before continuing.")

    print_info("\nPlease reboot your Pi before using robot-hat!")
    print_success("sudo reboot")

    # Always restore terminal on exit
    sys.stdout.write(' \033[1D\033[?25h')
    sys.stdout.flush()