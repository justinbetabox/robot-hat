#!/usr/bin/env python3
"""
I2C bus read/write functions for Robot Hat.
"""
import multiprocessing
from typing import Union, List, Optional

from smbus2 import SMBus

from .basic import BasicClass
from .utils import run_command


def _retry_wrapper(func):
    def wrapper(self, *args, **kwargs):
        for _ in range(self.RETRY):
            try:
                return func(self, *args, **kwargs)
            except OSError:
                self.logger.debug(f"OSError in {func.__name__}")
                continue
        return False
    return wrapper


class I2C(BasicClass):
    """
    I2C bus read/write functions.
    """
    RETRY: int = 5

    def __init__(
        self,
        address: Union[int, List[int], None] = None,
        bus: int = 1,
        *args,
        **kwargs
    ) -> None:
        """
        Initialize the I2C bus.

        :param address: I2C device address or list of addresses.
        :param bus: I2C bus number.
        """
        super().__init__(*args, **kwargs)
        self._bus: int = bus
        self._smbus: SMBus = SMBus(self._bus)
        if isinstance(address, list):
            connected: List[int] = self.scan()
            for _addr in address:
                if _addr in connected:
                    self.address = _addr
                    break
            else:
                self.address = address[0]
        else:
            self.address = address

    @_retry_wrapper
    def _write_byte(self, data: int) -> Optional[int]:
        self.logger.debug(f"_write_byte: [0x{data:02X}]")
        return self._smbus.write_byte(self.address, data)

    @_retry_wrapper
    def _write_byte_data(self, reg: int, data: int) -> Optional[int]:
        self.logger.debug(f"_write_byte_data: [0x{reg:02X}] [0x{data:02X}]")
        return self._smbus.write_byte_data(self.address, reg, data)

    @_retry_wrapper
    def _write_word_data(self, reg: int, data: int) -> Optional[int]:
        self.logger.debug(f"_write_word_data: [0x{reg:02X}] [0x{data:04X}]")
        return self._smbus.write_word_data(self.address, reg, data)

    @_retry_wrapper
    def _write_i2c_block_data(self, reg: int, data: List[int]) -> Optional[int]:
        self.logger.debug(f"_write_i2c_block_data: [0x{reg:02X}] {[f'0x{i:02X}' for i in data]}")
        return self._smbus.write_i2c_block_data(self.address, reg, data)

    @_retry_wrapper
    def _read_byte(self) -> int:
        result: int = self._smbus.read_byte(self.address)
        self.logger.debug(f"_read_byte: [0x{result:02X}]")
        return result

    @_retry_wrapper
    def _read_byte_data(self, reg: int) -> int:
        result: int = self._smbus.read_byte_data(self.address, reg)
        self.logger.debug(f"_read_byte_data: [0x{reg:02X}] [0x{result:02X}]")
        return result

    @_retry_wrapper
    def _read_word_data(self, reg: int) -> List[int]:
        result = self._smbus.read_word_data(self.address, reg)
        data: List[int] = [result & 0xFF, (result >> 8) & 0xFF]
        self.logger.debug(f"_read_word_data: [0x{reg:02X}] [0x{result:04X}]")
        return data

    @_retry_wrapper
    def _read_i2c_block_data(self, reg: int, num: int) -> List[int]:
        result: List[int] = self._smbus.read_i2c_block_data(self.address, reg, num)
        self.logger.debug(f"_read_i2c_block_data: [0x{reg:02X}] {[f'0x{i:02X}' for i in result]}")
        return result

    @_retry_wrapper
    def is_ready(self) -> bool:
        """
        Check if the I2C device is ready.
        """
        return self.address in self.scan()

    def scan(self) -> List[int]:
        """
        Scan the I2C bus for connected addresses.

        :return: List of device addresses found.
        """
        cmd: str = f"i2cdetect -y {self._bus}"
        _, output = run_command(cmd)

        lines: List[str] = output.split('\n')
        addresses: List[int] = []
        addresses_str: List[str] = []
        for line in lines:
            if ':' not in line:
                continue
            _, rest = line.split(':', 1)
            for addr in rest.strip().split():
                if addr == '--':
                    continue
                try:
                    value = int(addr, 16)
                    addresses.append(value)
                    addresses_str.append(f"0x{addr}")
                except ValueError:
                    continue
        self.logger.debug(f"Connected I2C devices: {addresses_str}")
        return addresses

    def write(self, data: Union[int, List[int], bytearray]) -> None:
        """
        Write data to the I2C device.

        :param data: Data to write (int, list, or bytearray).
        """
        if isinstance(data, bytearray):
            data_all = list(data)
        elif isinstance(data, int):
            data_all = [data] if data != 0 else [0]
        elif isinstance(data, list):
            data_all = data
        else:
            raise ValueError(f"write data must be int, list, or bytearray, not {type(data)}")

        if len(data_all) == 1:
            self._write_byte(data_all[0])
        elif len(data_all) == 2:
            self._write_byte_data(data_all[0], data_all[1])
        elif len(data_all) == 3:
            reg, low, high = data_all
            val = (high << 8) | low
            self._write_word_data(reg, val)
        else:
            reg = data_all[0]
            self._write_i2c_block_data(reg, data_all[1:])

    def read(self, length: int = 1) -> List[int]:
        """
        Read bytes from the I2C device.

        :param length: Number of bytes to read.
        :return: List of read bytes.
        """
        if not isinstance(length, int):
            raise ValueError(f"length must be int, not {type(length)}")
        return [self._read_byte() for _ in range(length)]

    def mem_write(self, data: Union[int, List[int], bytearray], memaddr: int) -> None:
        """
        Write data to a specific memory/register address.

        :param data: Data to write.
        :param memaddr: Register address.
        """
        self._write_i2c_block_data(memaddr, list(bytearray(data)) if isinstance(data, (bytearray, list)) else [data])

    def mem_read(self, length: int, memaddr: int) -> List[int]:
        """
        Read data from a specific memory/register address.

        :param length: Number of bytes to read.
        :param memaddr: Register address.
        :return: List of bytes read.
        """
        return self._read_i2c_block_data(memaddr, length)  

    def __del__(self) -> None:
        if hasattr(self, '_smbus') and self._smbus:
            self._smbus.close()
