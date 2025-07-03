#!/usr/bin/env python3
from .basic import BasicClass
from .utils import run_command
from smbus2 import SMBus
import multiprocessing
from typing import Union, List, Optional

def _retry_wrapper(func):
    def wrapper(self, *args, **kwargs):
        for _ in range(self.RETRY):
            try:
                return func(self, *args, **kwargs)
            except OSError:
                self.logger.debug(f"OSError in {func.__name__}")
                continue
        else:
            return False
    return wrapper

class I2C(BasicClass):
    """
    I2C bus read/write functions.
    """
    RETRY = 5

    def __init__(self, address: Union[int, List[int], None] = None, bus: int = 1, *args, **kwargs) -> None:
        """
        Initialize the I2C bus
        
        :param address: I2C device address or a list of addresses.
        :param bus: I2C bus number.
        """
        super().__init__(*args, **kwargs)
        self._bus = bus
        self._smbus = SMBus(self._bus)
        if isinstance(address, list):
            connected_devices = self.scan()
            for _addr in address:
                if _addr in connected_devices:
                    self.address = _addr
                    break
            else:
                self.address = address[0]
        else:
            self.address = address

    @_retry_wrapper
    def _write_byte(self, data: int) -> Optional[int]:
        self.logger.debug(f"_write_byte: [0x{data:02X}]")
        result = self._smbus.write_byte(self.address, data)
        return result

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
        result = self._smbus.read_byte(self.address)
        self.logger.debug(f"_read_byte: [0x{result:02X}]")
        return result

    @_retry_wrapper
    def _read_byte_data(self, reg: int) -> int:
        result = self._smbus.read_byte_data(self.address, reg)
        self.logger.debug(f"_read_byte_data: [0x{reg:02X}] [0x{result:02X}]")
        return result

    @_retry_wrapper
    def _read_word_data(self, reg: int) -> List[int]:
        result = self._smbus.read_word_data(self.address, reg)
        result_list = [result & 0xFF, (result >> 8) & 0xFF]
        self.logger.debug(f"_read_word_data: [0x{reg:02X}] [0x{result:04X}]")
        return result_list

    @_retry_wrapper
    def _read_i2c_block_data(self, reg: int, num: int) -> List[int]:
        result = self._smbus.read_i2c_block_data(self.address, reg, num)
        self.logger.debug(f"_read_i2c_block_data: [0x{reg:02X}] {[f'0x{i:02X}' for i in result]}")
        return result

    @_retry_wrapper
    def is_ready(self) -> bool:
        """Check if the I2C device is ready."""
        addresses = self.scan()
        return self.address in addresses

    def scan(self) -> List[int]:
        """Scan the I2C bus for devices."""
        cmd = f"i2cdetect -y {self._bus}"
        _, output = run_command(cmd)

        outputs = output.split('\n')[1:]
        addresses = []
        addresses_str = []
        for tmp in outputs:
            if tmp == "":
                continue
            tmp = tmp.split(':')[1]
            parts = tmp.strip().split(' ')
            for addr in parts:
                if addr != '--':
                    addresses.append(int(addr, 16))
                    addresses_str.append(f'0x{addr}')
        self.logger.debug(f"Connected I2C devices: {addresses_str}")
        return addresses

    def write(self, data: Union[int, List[int], bytearray]) -> None:
        """
        Write data to the I2C device.

        :param data: Data to write (int, list, or bytearray).
        :raises ValueError: If the data type is not supported.
        """
        if isinstance(data, bytearray):
            data_all = list(data)
        elif isinstance(data, int):
            if data == 0:
                data_all = [0]
            else:
                data_all = []
                while data > 0:
                    data_all.append(data & 0xFF)
                    data //= 256
        elif isinstance(data, list):
            data_all = data
        else:
            raise ValueError(f"write data must be int, list, or bytearray, not {type(data)}")

        if len(data_all) == 1:
            self._write_byte(data_all[0])
        elif len(data_all) == 2:
            self._write_byte_data(data_all[0], data_all[1])
        elif len(data_all) == 3:
            reg = data_all[0]
            val = (data_all[2] << 8) + data_all[1]
            self._write_word_data(reg, val)
        else:
            reg = data_all[0]
            self._write_i2c_block_data(reg, list(data_all[1:]))

    def read(self, length: int = 1) -> List[int]:
        """
        Read data from the I2C device.

        :param length: Number of bytes to read.
        :return: List of read bytes.
        """
        if not isinstance(length, int):
            raise ValueError(f"length must be int, not {type(length)}")

        result = []
        for _ in range(length):
            result.append(self._read_byte())
        return result

    def mem_write(self, data: Union[int, List[int], bytearray], memaddr: int) -> None:
        """
        Write data to a specific memory/register address.

        :param data: Data to send (int, list, or bytearray).
        :param memaddr: Memory/register address.
        """
        if isinstance(data, bytearray):
            data_all = list(data)
        elif isinstance(data, list):
            data_all = data
        elif isinstance(data, int):
            data_all = []
            if data == 0:
                data_all = [0]
            else:
                while data > 0:
                    data_all.append(data & 0xFF)
                    data //= 256
        else:
            raise ValueError("mem_write requires data of type int, list, or bytearray.")
        self._write_i2c_block_data(memaddr, data_all)

    def mem_read(self, length: int, memaddr: int) -> Union[List[int], bool]:
        """
        Read data from a specific memory/register address.

        :param length: Number of bytes to read.
        :param memaddr: Memory/register address.
        :return: List of read bytes or False if an error occurred.
        """
        return self._read_i2c_block_data(memaddr, length)

    def is_available(self) -> bool:
        """
        Check if the I2C device is available.

        :return: True if available, False otherwise.
        """
        return self.address in self.scan()

    def __del__(self):
        if self._smbus:
            self._smbus.close()
            self._smbus = None

if __name__ == "__main__":
    i2c = I2C(address=[0x17, 0x15], debug_level='debug')