#!/usr/bin/env python3
"""
Install script for robot_hat: handles OS-level setup,
hardware interface toggles, overlay installation, amplifier configuration,
Python package installation using pyproject.toml,
and supports selective execution and uninstallation.
"""

import subprocess
import sys
import os
import shutil
import argparse

# Define CLI arguments
parser = argparse.ArgumentParser(description="Install or uninstall the robot_hat package and dependencies")
parser.add_argument('--skip-system', action='store_true', help='Skip OS-level package installation')
parser.add_argument('--skip-interfaces', action='store_true', help='Skip enabling hardware interfaces')
parser.add_argument('--skip-overlays', action='store_true', help='Skip copying device tree overlays')
parser.add_argument('--skip-amplifier', action='store_true', help='Skip I2S amplifier configuration')
parser.add_argument('--dry-run', action='store_true', help='Show commands without executing')
parser.add_argument('--uninstall', action='store_true', help='Uninstall robot_hat and clean up')
args = parser.parse_args()


def run(cmd):
    """Run a command (unless dry-run) and exit on failure."""
    print(f"Running: {' '.join(cmd)}")
    if not args.dry_run:
        subprocess.run(cmd, check=True)


def preflight_checks():
    """Fail fast if requirements are unmet."""
    if os.geteuid() != 0:
        sys.exit("⚠️  Please run this script with sudo or as root.")
    for cmd in ("apt", "raspi-config", sys.executable, "git", "ping"):
        if not shutil.which(cmd):
            sys.exit(f"⚠️  Required command not found: {cmd}")
    if subprocess.run(["ping", "-c", "1", "github.com"], stdout=subprocess.DEVNULL).returncode != 0:
        sys.exit("⚠️  Network check failed: cannot reach github.com")


def install_system_packages():
    """Install required OS-level packages via apt, skipping already installed."""
    pkgs = [
        'python3-pip', 'python3-setuptools', 'python3-wheel',
        'python3-dev', 'git', 'build-essential',
        'libi2c-dev', 'i2c-tools',
        'libttspico-utils',  # Provides pico2wave for TTS engine
    ]
    missing = []
    for pkg in pkgs:
        res = subprocess.run(['dpkg-query', '-W', '-f=${Status}', pkg], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if b"install ok installed" not in res.stdout:
            missing.append(pkg)
    if missing:
        run(['apt', 'update'])
        run(['apt', 'install', '-y'] + missing)
    else:
        print("✅ All system packages already installed.")


def enable_interfaces():
    """Enable Raspberry Pi hardware interfaces idempotently."""
    run(['raspi-config', 'nonint', 'do_i2c', '0'])
    run(['raspi-config', 'nonint', 'do_spi', '0'])
    # run(['raspi-config', 'nonint', 'do_camera', '0'])


def install_overlays():
    """Copy device tree overlays, skipping existing ones."""
    src = os.path.join(os.path.dirname(__file__), 'dtoverlays')
    dst = '/boot/firmware/overlays'
    if not os.path.isdir(src):
        print(f"No overlays directory at {src}, skipping overlays.")
        return
    for fname in os.listdir(src):
        if not fname.endswith('.dtbo'):
            continue
        dest = os.path.join(dst, fname)
        if os.path.isfile(dest):
            print(f"Overlay {fname} already present, skipping.")
        else:
            run(['cp', os.path.join(src, fname), dest])


def configure_i2s_amplifier():
    """Run the i2samp.sh script once to configure the I2S amplifier."""
    marker = '/etc/robot_hat_i2s_configured'
    script = os.path.join(os.path.dirname(__file__), 'i2samp.sh')
    if os.path.isfile(marker):
        print("Amplifier already configured, skipping.")
        return
    if os.path.isfile(script):
        run(['bash', script])
        with open(marker, 'w') as f:
            f.write('configured')
    else:
        print(f"i2samp.sh not found at {script}, skipping amplifier config.")


def install_python_package():
    """Install the Python package leveraging pyproject.toml."""
    pkg = os.path.dirname(__file__)
    run([
        sys.executable, '-m', 'pip', 'install',
        '--break-system-packages',
        '--upgrade', '--force-reinstall', '--no-cache-dir', pkg
    ])


def uninstall():
    """Uninstall robot_hat, remove overlays, revert interfaces, and clean marker."""
    print("🚮 Uninstalling robot_hat...")
    # Use break-system-packages to allow pip uninstall in system-managed env
    run([sys.executable, '-m', 'pip', 'uninstall', '--break-system-packages', '-y', 'robot-hat'])
    # Remove overlays
    src = os.path.join(os.path.dirname(__file__), 'dtoverlays')
    dst = '/boot/firmware/overlays'
    if os.path.isdir(src):
        for fname in os.listdir(src):
            if fname.endswith('.dtbo'):
                path = os.path.join(dst, fname)
                if os.path.isfile(path):
                    run(['rm', path])
    # Revert interfaces
    run(['raspi-config', 'nonint', 'do_i2c', '1'])
    run(['raspi-config', 'nonint', 'do_spi', '1'])
    # Remove marker
    marker = '/etc/robot_hat_i2s_configured'
    if os.path.isfile(marker):
        run(['rm', marker])
    print("✅ Uninstallation complete.")


def main():
    if args.uninstall:
        uninstall()
        sys.exit(0)

    preflight_checks()
    if not args.skip_system:
        install_system_packages()
    if not args.skip_interfaces:
        enable_interfaces()
    if not args.skip_overlays:
        install_overlays()
    if not args.skip_amplifier:
        configure_i2s_amplifier()
    install_python_package()
    print("\n✅ Installation complete. Please reboot to apply changes if necessary.")


if __name__ == '__main__':
    main()
