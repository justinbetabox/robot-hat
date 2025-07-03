#!/usr/bin/env python3
import os
from typing import Optional, Dict, Any, List

class Devices:
    HAT_DEVICE_TREE: str = "/proc/device-tree/"
    HAT_UUIDs: List[str] = [
        "9daeea78-0000-076e-0032-582369ac3e02",  # robothat5 1902v50
    ]

    DEVICES: Dict[str, Dict[str, Any]] = {
        "robot_hat_v4x": {
            "uuid": None,
            "speaker_enable_pin": 20,
            "motor_mode": 1,
        },
        "robot_hat_v5x": {
            "uuid": HAT_UUIDs[0],
            "speaker_enable_pin": 12,
            "motor_mode": 2,
        }
    }

    name: str = ""
    product_id: int = 0
    product_ver: int = 0
    uuid: str = ""
    vendor: str = ""
    spk_en: int = 20
    motor_mode: int = 1

    def __init__(self) -> None:
        hat_path: Optional[str] = None

        # Search for a hat in the device tree
        for entry in os.listdir(self.HAT_DEVICE_TREE):
            if 'hat' in entry:
                uuid_path = os.path.join(self.HAT_DEVICE_TREE, entry, "uuid")
                if os.path.exists(uuid_path) and os.path.isfile(uuid_path):
                    with open(uuid_path, "r") as f:
                        uuid = f.read().rstrip("\x00").strip()
                    if uuid in self.HAT_UUIDs:
                        hat_path = os.path.join(self.HAT_DEVICE_TREE, entry)
                        break

        if hat_path is not None:
            product_path = os.path.join(hat_path, "product")
            product_id_path = os.path.join(hat_path, "product_id")
            product_ver_path = os.path.join(hat_path, "product_ver")
            uuid_path = os.path.join(hat_path, "uuid")
            vendor_path = os.path.join(hat_path, "vendor")

            with open(product_path, "r") as f:
                self.name = f.read().strip()

            with open(product_id_path, "r") as f:
                prod_id_str = f.read().rstrip("\x00").strip()
                self.product_id = int(prod_id_str, 16)

            with open(product_ver_path, "r") as f:
                prod_ver_str = f.read().rstrip("\x00").strip()
                self.product_ver = int(prod_ver_str, 16)

            with open(uuid_path, "r") as f:
                self.uuid = f.read().rstrip("\x00").strip()

            with open(vendor_path, "r") as f:
                self.vendor = f.read().strip()

            # Match the device and set speaker enable pin and motor mode
            for device_key, device_data in self.DEVICES.items():
                if device_data.get("uuid") == self.uuid:
                    self.spk_en = device_data.get("speaker_enable_pin", self.spk_en)
                    self.motor_mode = device_data.get("motor_mode", self.motor_mode)
                    break

if __name__ == "__main__":
    device = Devices()
    print(f'name: {device.name}')
    print(f'product_id: {device.product_id}')
    print(f'product_ver: {device.product_ver}')
    print(f'vendor: {device.vendor}')
    print(f'uuid: {device.uuid}')
    print(f'speaker_enable_pin: {device.spk_en}')
    print(f'motor_mode: {device.motor_mode}')