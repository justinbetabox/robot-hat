#!/usr/bin/env python3
from typing import Union
from .i2c import I2C

class ADC(I2C):
    """
    Analog to digital converter
    """
    ADDR = [0x14, 0x15]

    def __init__(self, chn: Union[int, str], address: Union[int, list, None] = None, *args, **kwargs) -> None:
        """
        Initialize the ADC device

        :param chn: Channel number (0-7 or "A0"-"A7")
        :type chn: int or str
        :param address: ADC device address or list of addresses, defaults to None.
        """
        if address is not None:
            super().__init__(address, *args, **kwargs)
        else:
            super().__init__(self.ADDR, *args, **kwargs)
        self.logger.debug(f'ADC device address: 0x{self.address:02X}')

        if isinstance(chn, str):
            # If chn is a string, assume it's a pin name like "A0", remove "A" and convert to int
            if chn.startswith("A"):
                chn = int(chn[1:])
            else:
                raise ValueError(f'ADC channel should be between [A0, A7], not "{chn}"')
        # Ensure channel is between 0 and 7
        if not (0 <= chn <= 7):
            raise ValueError(f'ADC channel should be between [0, 7], not "{chn}"')
        # Invert channel order (if needed)
        chn = 7 - chn
        # Convert to register value (OR with 0x10)
        self.chn = chn | 0x10

    def read(self) -> int:
        """
        Read the ADC value

        :return: ADC value (0-4095)
        :rtype: int
        """
        # Write register address, then read values
        self.write([self.chn, 0, 0])
        msb, lsb = super().read(2)
        # Combine MSB and LSB
        value = (msb << 8) + lsb
        self.logger.debug(f"Read value: {value}")
        return value

    def read_voltage(self) -> float:
        """
        Read the ADC value and convert it to voltage

        :return: Voltage value (0-3.3V)
        :rtype: float
        """
        value = self.read()
        voltage = value * 3.3 / 4095
        self.logger.debug(f"Read voltage: {voltage}")
        return voltage