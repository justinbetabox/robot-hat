#!/usr/bin/env python3
"""
Console script entry point for robot_hat configuration and utilities.
"""
import argparse
import os
import sys
from typing import NoReturn
from .version import __version__

OVERLAYS_DIR: str = '/boot/firmware/overlays'


def list_overlays() -> None:
    """List installed Device Tree overlays."""
    try:
        files = [f for f in os.listdir(OVERLAYS_DIR) if f.endswith('.dtbo')]
        if not files:
            print(f"No overlays found in {OVERLAYS_DIR}.")
        else:
            print("Installed overlays:")
            for f in files:
                print(f"  - {f}")
    except FileNotFoundError:
        print(f"Overlays directory not found: {OVERLAYS_DIR}")


def main() -> None:
    """CLI entry point for robot-hat-config."""
    parser = argparse.ArgumentParser(
        prog="robot-hat-config",
        description="Configure and inspect robot_hat settings"
    )
    parser.add_argument(
        '--version', action='store_true', help='Show robot_hat version'
    )
    parser.add_argument(
        '--list-overlays', action='store_true', help='List installed device tree overlays'
    )
    args = parser.parse_args()

    if args.version:
        print(__version__)
    elif args.list_overlays:
        list_overlays()
    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    main()
