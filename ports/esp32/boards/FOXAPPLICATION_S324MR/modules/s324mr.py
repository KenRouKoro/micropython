from machine import Pin, I2C, UART
import time
from tca6424a import TCA6424A
import ssd1306


class S324MR:
    def __init__(self):
        # LED
        self.led = Pin(9, Pin.OUT)
        self.led.value(0)  # Default off

        # Keys
        # KEY0: UP, KEY1: DOWN, KEY2: OK, KEY3: CANCEL
        self.key_up = Pin(4, Pin.IN, Pin.PULL_UP)
        self.key_down = Pin(5, Pin.IN, Pin.PULL_UP)
        self.key_ok = Pin(6, Pin.IN, Pin.PULL_UP)
        self.key_cancel = Pin(7, Pin.IN, Pin.PULL_UP)

        # I2C for OLED (I2C1 in tca_test.py)
        # SDA=47, SCL=48
        self.i2c_oled = I2C(1, sda=Pin(47), scl=Pin(48), freq=800000)

        # Scan for OLED
        devices_oled = self.i2c_oled.scan()
        if devices_oled:
            oled_addr = devices_oled[0]
            print(f"OLED detected at 0x{oled_addr:02X}")
            # OLED (128x32)
            try:
                self.oled = ssd1306.SSD1306_I2C(128, 32, self.i2c_oled, addr=oled_addr)
                self.oled.rotate(False)
                self.oled.fill(0)
                self.oled.text("Booting...", 0, 0)
                self.oled.show()
            except Exception as e:
                print("OLED init failed:", e)
                self.oled = None
        else:
            print("No OLED found on I2C1")
            self.oled = None

        # I2C for TCA6424A (I2C2/I2C0 in tca_test.py)
        # SDA=39, SCL=38
        self.i2c_tca = I2C(0, sda=Pin(39), scl=Pin(38), freq=400000)

        # Scan for TCA
        devices_tca = self.i2c_tca.scan()
        if devices_tca:
            tca_addr = devices_tca[0]
            print(f"TCA6424A detected at 0x{tca_addr:02X}")
            # TCA6424A
            try:
                self.tca = TCA6424A(self.i2c_tca, address=tca_addr)
                self.tca.set_config(0, 0, 0)  # All outputs
                self.tca.set_output(0, 0, 0)  # All Low
            except Exception as e:
                print("TCA6424A init failed:", e)
                self.tca = None
        else:
            print("No TCA6424A found on I2C0")
            self.tca = None

        # UARTs
        # UART1: TX=41, RX=42 (RS485)
        self.uart1 = UART(1, baudrate=9600, tx=41, rx=42)

        # UART2: TX=2, RX=1 (RS485)
        self.uart2 = UART(2, baudrate=9600, tx=2, rx=1)

    def beep(self, count=1, duration=0.1):
        # No buzzer mentioned in board_info, but good to have a placeholder or use LED
        for _ in range(count):
            self.led.value(1)
            time.sleep(duration)
            self.led.value(0)
            time.sleep(duration)

    def scan_i2c(self):
        print("Scanning I2C OLED (SDA=47, SCL=48):", self.i2c_oled.scan())
        print("Scanning I2C TCA (SDA=39, SCL=38):", self.i2c_tca.scan())
