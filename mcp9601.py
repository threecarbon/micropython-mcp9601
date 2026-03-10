"""
MicroPython MCP9600/MCP9601 Thermocouple EMF to Temperature Converter

https://www.microchip.com/en-us/product/mcp9601

MIT License

Copyright (c) 2025-2026 Seth Hardy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from machine import I2C, Pin
from micropython import const


__version__ = "1.0.0"

# default values
_DEFAULT_ADDR    = const(0x60)
_DEFAULT_TC_TYPE = const("K")
_DEFAULT_FILTER  = const(0b000)

# registers
_REG_HOT_JUNCTION  = const(0x00)
_REG_DELTA_TEMP    = const(0x01)
_REG_COLD_JUNCTION = const(0x02)
_REG_RAW_ADC       = const(0x03)
_REG_STATUS        = const(0x04)
_REG_THERM_CFG     = const(0x05)
_REG_DEV_CFG       = const(0x06)
_REG_ALERT1_CFG    = const(0x08)
_REG_ALERT2_CFG    = const(0x09)
_REG_ALERT3_CFG    = const(0x0A)
_REG_ALERT4_CFG    = const(0x0B)
_REG_ALERT1_HYST   = const(0x0C)
_REG_ALERT2_HYST   = const(0x0D)
_REG_ALERT3_HYST   = const(0x0E)
_REG_ALERT4_HYST   = const(0x0F)
_REG_ALERT1_LIMIT  = const(0x10)
_REG_ALERT2_LIMIT  = const(0x11)
_REG_ALERT3_LIMIT  = const(0x12)
_REG_ALERT4_LIMIT  = const(0x13)
_REG_VERSION       = const(0x20)

# alert register lookup (indexed by alert 1-4, slot 0 unused)
_ALERT_CFG_REGS   = (None, _REG_ALERT1_CFG, _REG_ALERT2_CFG, _REG_ALERT3_CFG, _REG_ALERT4_CFG)
_ALERT_HYST_REGS  = (None, _REG_ALERT1_HYST, _REG_ALERT2_HYST, _REG_ALERT3_HYST, _REG_ALERT4_HYST)
_ALERT_LIMIT_REGS = (None, _REG_ALERT1_LIMIT, _REG_ALERT2_LIMIT, _REG_ALERT3_LIMIT, _REG_ALERT4_LIMIT)

# thermocouple types
TC_TYPES = ("K", "J", "T", "N", "S", "E", "B", "R")


class MCP9601:
    AMBIENT_RESOLUTION_0_0625 = const(0)
    AMBIENT_RESOLUTION_0_25   = const(1)

    ADC_RESOLUTION_18 = const(0b00)
    ADC_RESOLUTION_16 = const(0b01)
    ADC_RESOLUTION_14 = const(0b10)
    ADC_RESOLUTION_12 = const(0b11)

    BURST_SAMPLES_1   = const(0b000)
    BURST_SAMPLES_2   = const(0b001)
    BURST_SAMPLES_4   = const(0b010)
    BURST_SAMPLES_8   = const(0b011)
    BURST_SAMPLES_16  = const(0b100)
    BURST_SAMPLES_32  = const(0b101)
    BURST_SAMPLES_64  = const(0b110)
    BURST_SAMPLES_128 = const(0b111)

    SHUTDOWN_NORMAL        = const(0b00)
    SHUTDOWN_SHUTDOWN      = const(0b01)
    SHUTDOWN_BURST         = const(0b10)
    SHUTDOWN_UNIMPLEMENTED = const(0b11)

    ALERT_THERMOCOUPLE = const(0)
    ALERT_AMBIENT      = const(1)

    ALERT_FALLING = const(0)
    ALERT_RISING  = const(1)

    ALERT_ACTIVE_LOW  = const(0)
    ALERT_ACTIVE_HIGH = const(1)

    ALERT_COMPARATOR = const(0)
    ALERT_INTERRUPT  = const(1)

    i2c: I2C
    address: int
    filter_coefficient: int
    alert1: Pin | None
    alert2: Pin | None
    alert3: Pin | None
    alert4: Pin | None
    scalert: Pin | None
    ocalert: Pin | None

    def __init__(
        self,
        i2c: I2C,
        address: int | None = None,
        tc_type: str | None = None,
        filter_coefficient: int | None = None,
        alert1: Pin | None = None,
        alert2: Pin | None = None,
        alert3: Pin | None = None,
        alert4: Pin | None = None,
        scalert: Pin | None = None,
        ocalert: Pin | None = None,
    ) -> None:
        self.i2c = i2c
        self.alert1 = alert1
        self.alert2 = alert2
        self.alert3 = alert3
        self.alert4 = alert4
        self.scalert = scalert
        self.ocalert = ocalert
        self.address = address if address is not None else _DEFAULT_ADDR

        if tc_type is not None and tc_type not in TC_TYPES:
            raise ValueError(f"invalid thermocouple type, possible values: {TC_TYPES}")

        if filter_coefficient is not None and (
            (filter_coefficient < 0) or (filter_coefficient > 7)
        ):
            raise ValueError("filter out of range")

        tc = TC_TYPES.index(tc_type if tc_type is not None else _DEFAULT_TC_TYPE)
        fc = filter_coefficient if filter_coefficient is not None else _DEFAULT_FILTER
        buf = bytearray([(tc << 4) | fc])
        self.i2c.writeto_mem(self.address, _REG_THERM_CFG, buf)

        ver = self._read_register(_REG_VERSION, 2)
        self._device_id = ver[0]
        self._revision = (ver[1] >> 4, ver[1] & 0x0F)

    def _require_mcp9601(self) -> None:
        if self._device_id == 0x40:
            raise RuntimeError("not supported on MCP9600")

    def _read_register(self, reg: int, size: int = 1) -> bytearray:
        buf = bytearray([reg])
        self.i2c.writeto(self.address, buf)
        read_buf = bytearray(size)
        self.i2c.readfrom_into(self.address, read_buf)
        return read_buf

    @staticmethod
    def temperature(upper: int, lower: int) -> float:
        value = (upper * 16) + (lower * 0.0625)
        if upper & 0x80:
            value -= 4096
        return value

    # ----- register 0x00: hot-junction temperature

    @property
    def hot_junction(self) -> float:
        buf = self._read_register(_REG_HOT_JUNCTION, 2)
        return self.temperature(buf[0], buf[1])

    # ----- register 0x01: junction temperature delta

    @property
    def delta_temperature(self) -> float:
        buf = self._read_register(_REG_DELTA_TEMP, 2)
        return self.temperature(buf[0], buf[1])

    # ----- register 0x02: cold-junction temperature

    @property
    def cold_junction(self) -> float:
        buf = self._read_register(_REG_COLD_JUNCTION, 2)
        return self.temperature(buf[0], buf[1])

    # ----- register 0x03: raw data ADC

    @property
    def raw_adc(self) -> bytearray:
        return self._read_register(_REG_RAW_ADC, 3)

    @property
    def raw_adc_value(self) -> int:
        buf = self._read_register(_REG_RAW_ADC, 3)
        val = (buf[0] << 16) | (buf[1] << 8) | buf[2]
        if val & 0x800000:
            val -= 0x1000000
        return val

    # ----- register 0x04: chip status

    @property
    def status(self) -> int:
        return self._read_register(_REG_STATUS)[0]

    @property
    def burst_complete(self) -> bool:
        return bool(self.status & (1 << 7))

    @property
    def temperature_update(self) -> bool:
        return bool(self.status & (1 << 6))

    @property
    def short_circuit(self) -> bool:
        self._require_mcp9601()
        return bool(self.status & (1 << 5))

    @property
    def input_range(self) -> bool:
        return bool(self.status & (1 << 4))

    @property
    def open_circuit(self) -> bool:
        self._require_mcp9601()
        return bool(self.status & (1 << 4))

    @property
    def data_ready(self) -> bool:
        return bool(self.status & (1 << 6))

    def clear_status_flags(self) -> None:
        s = self.status & 0x3F  # clear bits 7 (burst_complete) and 6 (temperature_update)
        self.i2c.writeto_mem(self.address, _REG_STATUS, bytearray([s]))

    def alert_status(self, alert: int) -> bool:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        return bool(self.status & (1 << (alert - 1)))

    # ----- register 0x05: thermocouple sensor configuration

    @property
    def sensor_config(self) -> int:
        return self._read_register(_REG_THERM_CFG)[0]

    @sensor_config.setter
    def sensor_config(self, config: int) -> None:
        if (config < 0) or (config > 255):
            raise ValueError("config out of range")
        self.i2c.writeto_mem(self.address, _REG_THERM_CFG, bytearray([config]))

    @property
    def tc_type(self) -> str:
        return TC_TYPES[self.sensor_config >> 4]

    @tc_type.setter
    def tc_type(self, val: str) -> None:
        if val not in TC_TYPES:
            raise ValueError(f"invalid thermocouple type, possible values: {TC_TYPES}")
        tc_type = TC_TYPES.index(val)
        config = bytearray([(self.sensor_config & 0x0F) | (tc_type << 4)])
        self.i2c.writeto_mem(self.address, _REG_THERM_CFG, config)

    @property
    def filter(self) -> int:
        return self._read_register(_REG_THERM_CFG)[0] & 0b0111

    @filter.setter
    def filter(self, val: int) -> None:
        if (val < 0) or (val > 7):
            raise ValueError("filter out of range")
        config = bytearray([(self.sensor_config & 0xF0) | val])
        self.i2c.writeto_mem(self.address, _REG_THERM_CFG, config)

    # ----- register 0x06: device configuration

    @property
    def device_config(self) -> int:
        return self._read_register(_REG_DEV_CFG)[0]

    @device_config.setter
    def device_config(self, config: int) -> None:
        if (config < 0) or (config > 255):
            raise ValueError("config out of range")
        self.i2c.writeto_mem(self.address, _REG_DEV_CFG, bytearray([config]))

    @property
    def ambient_resolution(self) -> int:
        return (self.device_config & (1 << 7)) >> 7

    @ambient_resolution.setter
    def ambient_resolution(self, val: int) -> None:
        if (val < 0) or (val > 1):
            raise ValueError("ambient resolution out of range")
        config = bytearray([(self.device_config & ~(1 << 7)) | (val << 7)])
        self.i2c.writeto_mem(self.address, _REG_DEV_CFG, config)

    @property
    def adc_resolution(self) -> int:
        return (self.device_config & (0b11 << 5)) >> 5

    @adc_resolution.setter
    def adc_resolution(self, val: int) -> None:
        if (val < 0) or (val > 3):
            raise ValueError("adc resolution out of range")
        config = bytearray([(self.device_config & ~(0b11 << 5)) | (val << 5)])
        self.i2c.writeto_mem(self.address, _REG_DEV_CFG, config)

    @property
    def burst_samples(self) -> int:
        return (self.device_config & (0b111 << 2)) >> 2

    @burst_samples.setter
    def burst_samples(self, val: int) -> None:
        if (val < 0) or (val > 7):
            raise ValueError("burst samples out of range")
        config = bytearray([(self.device_config & ~(0b111 << 2)) | (val << 2)])
        self.i2c.writeto_mem(self.address, _REG_DEV_CFG, config)

    @property
    def shutdown_mode(self) -> int:
        return self.device_config & 0b0011

    @shutdown_mode.setter
    def shutdown_mode(self, val: int) -> None:
        if (val < 0) or (val > 2):
            raise ValueError("shutdown mode out of range")
        config = bytearray([(self.device_config & ~0b11) | val])
        self.i2c.writeto_mem(self.address, _REG_DEV_CFG, config)

    def configure_device(
        self,
        ambient_resolution: int | None = None,
        adc_resolution: int | None = None,
        burst_samples: int | None = None,
        shutdown_mode: int | None = None,
    ) -> None:
        config = self.device_config
        if ambient_resolution is not None:
            config = (config & ~(1 << 7)) | (ambient_resolution << 7)
        if adc_resolution is not None:
            config = (config & ~(0b11 << 5)) | (adc_resolution << 5)
        if burst_samples is not None:
            config = (config & ~(0b111 << 2)) | (burst_samples << 2)
        if shutdown_mode is not None:
            config = (config & ~0b11) | shutdown_mode
        self.i2c.writeto_mem(self.address, _REG_DEV_CFG, bytearray([config]))

    # ----- register 0x08: alert 1 configuration
    # ----- register 0x09: alert 2 configuration
    # ----- register 0x0A: alert 3 configuration
    # ----- register 0x0B: alert 4 configuration

    def alert_config(self, alert: int) -> int:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        return self._read_register(_ALERT_CFG_REGS[alert])[0]

    def set_alert_config(self, alert: int, config: int) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        if (config < 0) or (config > 255):
            raise ValueError("config out of range")
        self.i2c.writeto_mem(self.address, _ALERT_CFG_REGS[alert], bytearray([config]))

    def is_interrupt_pending(self, alert: int) -> int:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        return (self.alert_config(alert) & 0b1000_0000) >> 7

    def alert_monitor(self, alert: int) -> int:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        return (self.alert_config(alert) & 0b0001_0000) >> 4

    def set_alert_monitor(self, alert: int, val: int) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        config = (self.alert_config(alert) & ~0b0001_0000) | bool(val) << 4
        self.i2c.writeto_mem(self.address, _ALERT_CFG_REGS[alert], bytearray([config]))

    def alert_rise_fall(self, alert: int) -> int:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        return (self.alert_config(alert) & 0b1000) >> 3

    def set_alert_rise_fall(self, alert: int, val: int) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        config = (self.alert_config(alert) & ~0b1000) | bool(val) << 3
        self.i2c.writeto_mem(self.address, _ALERT_CFG_REGS[alert], bytearray([config]))

    def alert_active_high_low(self, alert: int) -> int:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        return (self.alert_config(alert) & 0b0100) >> 2

    def set_alert_active_high_low(self, alert: int, val: int) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        config = (self.alert_config(alert) & ~0b0100) | bool(val) << 2
        self.i2c.writeto_mem(self.address, _ALERT_CFG_REGS[alert], bytearray([config]))

    def alert_comparator_interrupt(self, alert: int) -> int:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        return (self.alert_config(alert) & 0b0010) >> 1

    def set_alert_comparator_interrupt(self, alert: int, val: int) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        config = (self.alert_config(alert) & ~0b0010) | bool(val) << 1
        self.i2c.writeto_mem(self.address, _ALERT_CFG_REGS[alert], bytearray([config]))

    def alert_enabled(self, alert: int) -> int:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        return self.alert_config(alert) & 1

    def set_alert_enabled(self, alert: int, val: int) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        config = (self.alert_config(alert) & ~1) | bool(val)
        self.i2c.writeto_mem(self.address, _ALERT_CFG_REGS[alert], bytearray([config]))

    def configure_alert(
        self,
        alert: int,
        monitor_junction: int | None = None,
        rise_fall: int | None = None,
        high_low: int | None = None,
        mode: int | None = None,
        enable: int | None = None,
    ) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        config = self.alert_config(alert)
        if monitor_junction is not None:
            config = (config & ~(1 << 4)) | bool(monitor_junction) << 4
        if rise_fall is not None:
            config = (config & ~(1 << 3)) | bool(rise_fall) << 3
        if high_low is not None:
            config = (config & ~(1 << 2)) | bool(high_low) << 2
        if mode is not None:
            config = (config & ~(1 << 1)) | bool(mode) << 1
        if enable is not None:
            config = (config & ~1) | bool(enable)
        self.i2c.writeto_mem(self.address, _ALERT_CFG_REGS[alert], bytearray([config]))

    # ----- register 0x0C: alert 1 hysteresis
    # ----- register 0x0D: alert 2 hysteresis
    # ----- register 0x0E: alert 3 hysteresis
    # ----- register 0x0F: alert 4 hysteresis

    def alert_hysteresis(self, alert: int) -> int:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        return self._read_register(_ALERT_HYST_REGS[alert])[0]

    def set_alert_hysteresis(self, alert: int, val: int) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        if (val < 0) or (val > 255):
            raise ValueError("alert hysteresis out of range")
        self.i2c.writeto_mem(self.address, _ALERT_HYST_REGS[alert], bytearray([val]))

    # ----- register 0x10: alert 1 limit
    # ----- register 0x11: alert 2 limit
    # ----- register 0x12: alert 3 limit
    # ----- register 0x13: alert 4 limit

    def alert_limit(self, alert: int) -> float:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        limit = self._read_register(_ALERT_LIMIT_REGS[alert], 2)
        return self.temperature(limit[0], limit[1])

    def set_alert_limit(self, alert: int, val: float) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        if (val < -2048) or (val > 2047.75):
            raise ValueError("value out of range")
        if val < 0:
            val += 4096
        limit = int(val / 0.0625)
        buf = bytearray([(limit >> 8) & 0xFF, limit & 0xFF])
        self.i2c.writeto_mem(self.address, _ALERT_LIMIT_REGS[alert], buf)

    def check_alerts(self) -> tuple:
        s = self.status
        return (bool(s & 1), bool(s & 2), bool(s & 4), bool(s & 8))

    def setup_alert(
        self,
        alert: int,
        limit: float,
        hysteresis: int = 0,
        rising: bool = True,
        monitor_cold_junction: bool = False,
        active_high: bool = False,
        interrupt: bool = False,
    ) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        config = (
            (bool(monitor_cold_junction) << 4)
            | (bool(rising) << 3)
            | (bool(active_high) << 2)
            | (bool(interrupt) << 1)
            | 1  # enabled
        )
        self.i2c.writeto_mem(self.address, _ALERT_CFG_REGS[alert], bytearray([config]))
        self.set_alert_limit(alert, limit)
        self.set_alert_hysteresis(alert, hysteresis)

    def setup_overtemp_alert(self, alert: int, limit: float, hysteresis: int = 0) -> None:
        self.setup_alert(alert, limit, hysteresis, rising=True, active_high=False)

    def setup_undertemp_alert(self, alert: int, limit: float, hysteresis: int = 0) -> None:
        self.setup_alert(alert, limit, hysteresis, rising=False, active_high=False)

    def setup_window(
        self,
        alert_high: int,
        alert_low: int,
        high_temp: float,
        low_temp: float,
        hysteresis: int = 0,
    ) -> None:
        self.setup_overtemp_alert(alert_high, high_temp, hysteresis)
        self.setup_undertemp_alert(alert_low, low_temp, hysteresis)

    def clear_interrupt(self, alert: int) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        config = self.alert_config(alert) | 0x80
        self.i2c.writeto_mem(self.address, _ALERT_CFG_REGS[alert], bytearray([config]))

    def disable_alert(self, alert: int) -> None:
        if (alert < 1) or (alert > 4):
            raise ValueError("alert out of range")
        config = self.alert_config(alert) & ~1
        self.i2c.writeto_mem(self.address, _ALERT_CFG_REGS[alert], bytearray([config]))

    # ----- register 0x20: version

    @property
    def version(self) -> bytearray:
        return self._read_register(_REG_VERSION, 2)

    @property
    def device_id(self) -> int:
        return self._device_id

    @property
    def revision(self) -> tuple:
        return self._revision

    # ----- end registers

    def test(self) -> None:
        if self._device_id == 0x41:
            name = "MCP9601"
        elif self._device_id == 0x40:
            name = "MCP9600"
        else:
            raise RuntimeError("unknown chip")
        print(name)
        major, minor = self.revision
        print(f"  device_id: 0x{self._device_id:02X}  revision: {major}.{minor}")
        print(f"  type: {self.tc_type}  filter: {self.filter}")
        print(
            f"  status: {bin(self.status)} ",
            f"config sensor: {bin(self._read_register(_REG_THERM_CFG)[0])} ",
            f"config device: {bin(self._read_register(_REG_DEV_CFG)[0])}",
        )
        if self._device_id == 0x41:
            if self.short_circuit:
                print("  *** thermocouple short circuit ***")
                return
            if self.open_circuit:
                print("  *** thermocouple not connected ***")
                return
        print(
            f"  cold: {self.cold_junction}°C ",
            f"hot: {self.hot_junction}°C ",
            f"Δ: {self.delta_temperature}°C",
        )
