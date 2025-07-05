#!/usr/bin/env python3
"""
I2C bus read/write functions for Robot Hat.
"""
from typing import Union, List, Optional, Any, Callable
from .basic import BasicClass
from .utils import run_command
from smbus2 import SMBus


def _retry_wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to retry I2C operations on OSError up to RETRY times."""
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        for _ in range(self.RETRY):
            try:
                return func(self, *args, **kwargs)
            except OSError:
                self.logger.debug(f"OSError in {func.__name__}")
                continue
        return False
    return wrapper


class I2C(BasicClass):
    """I2C bus read/write functions."""

    RETRY: int = 5

    def __init__(
        self,
        address: Union[int, List[int], None] = None,
        bus: int = 1,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """
        Initialize the I2C bus.

        :param address: I2C device address or list of addresses.
        :param bus: I2C bus number (default 1).
        """
        super().__init__(*args, **kwargs)
        self._bus: int = bus
        self._smbus: SMBus = SMBus(self._bus)
        self.address: Optional[int]
        if isinstance(address, list):
            connected: List[int] = self.scan()
            for addr in address:
                if addr in connected:
                    self.address = addr
                    break
            else:
                self.address = address[0]
        else:
            self.address = address

    @_retry_wrapper
    def _write_byte(self, data: int) -> Union[int, bool]:
        self.logger.debug(f"_write_byte: [0x{data:02X}]")
        return self._smbus.write_byte(self.address, data)  # type: ignore

    @_retry_wrapper
    def _write_byte_data(self, reg: int, data: int) -> Union[int, bool]:
        self.logger.debug(f"_write_byte_data: [0x{reg:02X}] [0x{data:02X}]")
        return self._smbus.write_byte_data(self.address, reg, data)  # type: ignore

    @_retry_wrapper
    def _write_word_data(self, reg: int, data: int) -> Union[int, bool]:
        self.logger.debug(f"_write_word_data: [0x{reg:02X}] [0x{data:04X}]")
        return self._smbus.write_word_data(self.address, reg, data)  # type: ignore

    @_retry_wrapper
    def _write_i2c_block_data(self, reg: int, data: List[int]) -> Union[int, bool]:
        self.logger.debug(
            f"_write_i2c_block_data: [0x{reg:02X}] {[f'0x{i:02X}' for i in data]}"
        )
        return self._smbus.write_i2c_block_data(self.address, reg, data)  # type: ignore

    @_retry_wrapper
    def _read_byte(self) -> Union[int, bool]:
        result: int = self._smbus.read_byte(self.address)  # type: ignore
        self.logger.debug(f"_read_byte: [0x{result:02X}]")
        return result

    @_retry_wrapper
    def _read_byte_data(self, reg: int) -> Union[int, bool]:
        result: int = self._smbus.read_byte_data(self.address, reg)
        self.logger.debug(f"_read_byte_data: [0x{reg:02X}] [0x{result:02X}]")
        return result

    @_retry_wrapper
    def _read_word_data(self, reg: int) -> Union[List[int], bool]:
        raw: int = self._smbus.read_word_data(self.address, reg)
        result: List[int] = [raw & 0xFF, (raw >> 8) & 0xFF]
        self.logger.debug(f"_read_word_data: [0x{reg:02X}] [0x{raw:04X}]")
        return result

    @_retry_wrapper
    def _read_i2c_block_data(self, reg: int, num: int) -> Union[List[int], bool]:
        data: List[int] = self._smbus.read_i2c_block_data(self.address, reg, num)
        self.logger.debug(
            f"_read_i2c_block_data: [0x{reg:02X}] {[f'0x{i:02X}' for i in data]}"
        )
        return data

    @_retry_wrapper
    def is_ready(self) -> bool:
        """Check if the I2C device is ready."""
        return bool(self.address in self.scan())

    def scan(self) -> List[int]:
        """
        Scan the I2C bus for connected devices.

        :return: List of I2C addresses found.
        """
        cmd = f"i2cdetect -y {self._bus}"
        _, output = run_command(cmd)
        lines = output.split('\n')[1:]
        addresses: List[int] = []
        for line in lines:
            parts = line.split(':')[1].strip().split()
            for addr in parts:
                if addr != '--':
                    addresses.append(int(addr, 16))
        self.logger.debug(f"Connected I2C devices: {addresses}")
        return addresses

    def write(self, data: Union[int, List[int], bytearray]) -> None:
        """
        Write bytes to the I2C device.

        :param data: Data to write.
        """
        if isinstance(data, bytearray):
            payload: List[int] = list(data)
        elif isinstance(data, int):
            payload = [data] if data else [0]
        elif isinstance(data, list):
            payload = data
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        length = len(payload)
        if length == 1:
            self._write_byte(payload[0])
        elif length == 2:
            self._write_byte_data(payload[0], payload[1])
        elif length == 3:
            reg, low, high = payload
            self._write_word_data(reg, (high << 8) | low)
        else:
            self._write_i2c_block_data(payload[0], payload[1:])

    def read(self, length: int = 1) -> List[int]:
        """
        Read bytes from the I2C device.

        :param length: Number of bytes to read (>=1).
        :return: List of read byte values.
        :raises ValueError: If length < 1.
        """
        if length < 1:
            raise ValueError("length must be >= 1")
        result: List[int] = []
        for _ in range(length):
            val = self._read_byte()
            if val is False:
                break
            result.append(val)  # type: ignore
        return result

    def mem_write(self, data: Union[int, List[int], bytearray], memaddr: int) -> None:
        """
        Write to a specific register address.

        :param data: Data to write.
        :param memaddr: Register address.
        """
        if isinstance(data, (int, list, bytearray)):
            payload: List[int] = [data] if isinstance(data, int) else list(data)  # type: ignore
            self._write_i2c_block_data(memaddr, payload)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

    def mem_read(self, length: int, memaddr: int) -> Union[List[int], bool]:
        """
        Read from a specific register address.

        :param length: Number of bytes to read.
        :param memaddr: Register address.
        :return: List of read bytes or False on failure.
        """
        return self._read_i2c_block_data(memaddr, length)

    def is_available(self) -> bool:
        """
        Check if the I2C device is available.

        :return: True if available, False otherwise.
        """
        return bool(self.address in self.scan())

    def __del__(self) -> None:
        if getattr(self, "_smbus", None):
            self._smbus.close()
            self._smbus = None


if __name__ == "__main__":
    # Example usage
    i2c = I2C(address=[0x17, 0x15], debug_level='debug')
    print(i2c.scan())
