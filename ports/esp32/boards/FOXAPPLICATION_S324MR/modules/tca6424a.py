from machine import I2C
import micropython


class TCA6424A:
    # Register definitions
    REG_INPUT0 = micropython.const(0x00)
    REG_INPUT1 = micropython.const(0x01)
    REG_INPUT2 = micropython.const(0x02)
    REG_OUTPUT0 = micropython.const(0x04)
    REG_OUTPUT1 = micropython.const(0x05)
    REG_OUTPUT2 = micropython.const(0x06)
    REG_POLARITY0 = micropython.const(0x08)
    REG_POLARITY1 = micropython.const(0x09)
    REG_POLARITY2 = micropython.const(0x0A)
    REG_CONFIG0 = micropython.const(0x0C)
    REG_CONFIG1 = micropython.const(0x0D)
    REG_CONFIG2 = micropython.const(0x0E)

    # Auto-increment flag for bulk read/write
    AUTO_INCREMENT = micropython.const(0x80)

    def __init__(self, i2c, address=34):
        """
        Initialize the TCA6424A driver.

        Args:
            i2c: Configured machine.I2C object
            address: I2C address of the device (default 34)
        """
        self.i2c = i2c
        self.address = address

        # Shadow registers to minimize read operations for output/config
        # Initializing to default values (Power-up defaults)
        # Config: All 1 (Inputs)
        # Output: All 1 (High) - Note: C driver initialized to 0xFFFFFF
        # Polarity: All 0 (No inversion)
        self._config = bytearray([0xFF, 0xFF, 0xFF])
        self._output = bytearray([0xFF, 0xFF, 0xFF])
        self._polarity = bytearray([0x00, 0x00, 0x00])

        # Read current state from device to sync shadow registers
        try:
            self._read_registers()
        except OSError:
            print("TCA6424A not found or error reading initial state")

    def _read_registers(self):
        """Read current configuration from device to sync shadow registers."""
        # Read Config
        self._config = bytearray(
            self.i2c.readfrom_mem(self.address, self.REG_CONFIG0 | self.AUTO_INCREMENT, 3)
        )
        # Read Output
        self._output = bytearray(
            self.i2c.readfrom_mem(self.address, self.REG_OUTPUT0 | self.AUTO_INCREMENT, 3)
        )
        # Read Polarity
        self._polarity = bytearray(
            self.i2c.readfrom_mem(self.address, self.REG_POLARITY0 | self.AUTO_INCREMENT, 3)
        )

    def _write_block(self, reg_base, data):
        """Write 3 bytes to a register block using auto-increment."""
        self.i2c.writeto_mem(self.address, reg_base | self.AUTO_INCREMENT, data)

    def set_config(self, port0, port1, port2):
        """
        Set configuration (direction) for all ports.
        1 = Input, 0 = Output
        """
        self._config[0] = port0 & 0xFF
        self._config[1] = port1 & 0xFF
        self._config[2] = port2 & 0xFF
        self._write_block(self.REG_CONFIG0, self._config)

    def set_output(self, port0, port1, port2):
        """
        Set output levels for all ports.
        1 = High, 0 = Low
        """
        self._output[0] = port0 & 0xFF
        self._output[1] = port1 & 0xFF
        self._output[2] = port2 & 0xFF
        self._write_block(self.REG_OUTPUT0, self._output)

    def set_polarity(self, port0, port1, port2):
        """
        Set polarity inversion for all ports.
        1 = Inverted, 0 = Normal
        """
        self._polarity[0] = port0 & 0xFF
        self._polarity[1] = port1 & 0xFF
        self._polarity[2] = port2 & 0xFF
        self._write_block(self.REG_POLARITY0, self._polarity)

    def get_input(self):
        """
        Read input states of all ports.
        Returns a tuple of 3 bytes (port0, port1, port2).
        """
        data = self.i2c.readfrom_mem(self.address, self.REG_INPUT0 | self.AUTO_INCREMENT, 3)
        return (data[0], data[1], data[2])

    @micropython.native
    def pin_mode(self, pin: int, mode: int):
        """
        Set mode for a specific pin (0-23).
        mode: 1 = Input, 0 = Output
        """
        if not 0 <= pin <= 23:
            raise ValueError("Pin must be 0-23")

        port_idx = pin // 8
        bit_idx = pin % 8

        if mode:
            self._config[port_idx] |= 1 << bit_idx
        else:
            self._config[port_idx] &= ~(1 << bit_idx)

        self.i2c.writeto_mem(
            self.address, (self.REG_CONFIG0 + port_idx), bytes([self._config[port_idx]])
        )

    @micropython.native
    def pin_write(self, pin: int, value: int):
        """
        Set output value for a specific pin (0-23).
        value: 1 = High, 0 = Low
        """
        if not 0 <= pin <= 23:
            raise ValueError("Pin must be 0-23")

        port_idx = pin // 8
        bit_idx = pin % 8

        if value:
            self._output[port_idx] |= 1 << bit_idx
        else:
            self._output[port_idx] &= ~(1 << bit_idx)

        self.i2c.writeto_mem(
            self.address, (self.REG_OUTPUT0 + port_idx), bytes([self._output[port_idx]])
        )

    @micropython.native
    def pin_read(self, pin: int) -> int:
        """
        Read value of a specific pin (0-23).
        Returns 0 or 1.
        """
        if not 0 <= pin <= 23:
            raise ValueError("Pin must be 0-23")

        port_idx = pin // 8
        bit_idx = pin % 8

        # Read the single port byte
        val = int(self.i2c.readfrom_mem(self.address, self.REG_INPUT0 + port_idx, 1)[0])
        return (val >> bit_idx) & 1

    @micropython.native
    def toggle(self, pin: int):
        """Toggle the output state of a pin."""
        if not 0 <= pin <= 23:
            raise ValueError("Pin must be 0-23")

        port_idx = pin // 8
        bit_idx = pin % 8

        self._output[port_idx] ^= 1 << bit_idx
        self.i2c.writeto_mem(
            self.address, (self.REG_OUTPUT0 + port_idx), bytes([self._output[port_idx]])
        )

    def get_all_inputs(self):
        """Return all inputs as a single 24-bit integer."""
        p0, p1, p2 = self.get_input()
        return p0 | (p1 << 8) | (p2 << 16)

    def set_all_outputs(self, value):
        """Set all outputs from a single 24-bit integer."""
        self.set_output(value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF)
