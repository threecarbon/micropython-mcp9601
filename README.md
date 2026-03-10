# MicroPython MCP9600/MCP9601 Driver

A MicroPython driver for the Microchip [MCP9600](https://www.microchip.com/en-us/product/mcp9600) and [MCP9601](https://www.microchip.com/en-us/product/mcp9601) thermocouple EMF-to-temperature converters.

Single file. No dependencies. MicroPython, not CircuitPython.

Supports all thermocouple types (K, J, T, N, S, E, B, R), 4 configurable temperature alerts, burst mode sampling, and fault detection (open/short circuit on MCP9601).

## Installation

Copy `mcp9601.py` to your board's `lib/` directory.

## Quick Start

```python
from machine import I2C, Pin
from mcp9601 import MCP9601

i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=100_000)
tc = MCP9601(i2c)

print(f"Temperature: {tc.hot_junction}°C")
print(f"Cold junction: {tc.cold_junction}°C")
print(f"Delta: {tc.delta_temperature}°C")
```

## Constructor

```python
MCP9601(
    i2c,                          # machine.I2C instance
    address=0x60,                 # I2C address (0x60-0x67)
    tc_type="K",                  # Thermocouple type: K, J, T, N, S, E, B, R
    filter_coefficient=0,         # Digital filter: 0 (off) to 7 (max smoothing)
    alert1=None,                  # Optional Pin for alert 1 output
    alert2=None,                  # Optional Pin for alert 2 output
    alert3=None,                  # Optional Pin for alert 3 output
    alert4=None,                  # Optional Pin for alert 4 output
    scalert=None,                 # Optional Pin for short-circuit alert (MCP9601)
    ocalert=None,                 # Optional Pin for open-circuit alert (MCP9601)
)
```

Alert pins are stored as attributes for convenience and are not used by the driver internally.

## Temperature Reading

```python
tc.hot_junction         # Thermocouple temperature (°C)
tc.cold_junction        # Ambient/cold-junction temperature (°C)
tc.delta_temperature    # Difference between hot and cold junction (°C)
tc.raw_adc_value        # Raw ADC reading (signed 24-bit)
```

## Configuration

### Thermocouple Type and Filter

```python
tc.tc_type = "J"        # Change thermocouple type at runtime
tc.filter = 4           # Set digital filter (0=off, 7=max)
```

### Device Configuration

```python
tc.configure_device(
    ambient_resolution=MCP9601.AMBIENT_RESOLUTION_0_0625,  # 0.0625°C (default) or 0.25°C
    adc_resolution=MCP9601.ADC_RESOLUTION_18,              # 18, 16, 14, or 12-bit
    burst_samples=MCP9601.BURST_SAMPLES_1,                 # 1 to 128 samples
    shutdown_mode=MCP9601.SHUTDOWN_NORMAL,                 # Normal, Shutdown, or Burst
)
```

Individual settings can also be set as properties:

```python
tc.ambient_resolution = MCP9601.AMBIENT_RESOLUTION_0_25
tc.adc_resolution = MCP9601.ADC_RESOLUTION_16
tc.burst_samples = MCP9601.BURST_SAMPLES_32
tc.shutdown_mode = MCP9601.SHUTDOWN_BURST
```

## Alerts

The MCP9601 has 4 configurable temperature alert outputs.

### Quick Setup

```python
# Alert when temperature exceeds 100°C
tc.setup_overtemp_alert(alert=1, limit=100.0, hysteresis=5)

# Alert when temperature drops below 10°C
tc.setup_undertemp_alert(alert=2, limit=10.0, hysteresis=2)

# Temperature window using two alerts
tc.setup_window(alert_high=1, alert_low=2, high_temp=100.0, low_temp=10.0, hysteresis=5)

# Check which alerts are active
alerts = tc.check_alerts()  # (alert1, alert2, alert3, alert4) booleans
```

### Full Alert Configuration

```python
tc.setup_alert(
    alert=1,                       # Alert 1-4
    limit=150.0,                   # Temperature threshold (°C)
    hysteresis=10,                 # Hysteresis (°C, 0-255)
    rising=True,                   # True=rising edge, False=falling edge
    monitor_cold_junction=False,   # True=monitor ambient instead of thermocouple
    active_high=False,             # Alert pin polarity
    interrupt=False,               # True=interrupt mode, False=comparator mode
)
```

### Alert Management

```python
tc.alert_status(1)       # Check if alert 1 is active
tc.clear_interrupt(1)    # Clear interrupt flag for alert 1
tc.disable_alert(1)      # Disable alert 1
```

## Status and Diagnostics

```python
tc.status                # Raw status register
tc.burst_complete        # True if burst measurement complete
tc.temperature_update    # True if new temperature data available
tc.data_ready            # True if data ready to read
tc.short_circuit         # True if thermocouple shorted (MCP9601 only)
tc.open_circuit          # True if thermocouple disconnected (MCP9601 only)
tc.clear_status_flags()  # Clear burst_complete and temperature_update flags
```

## Device Info

```python
tc.device_id             # 0x40 = MCP9600, 0x41 = MCP9601
tc.revision              # (major, minor) firmware revision tuple
tc.test()                # Print diagnostic summary
```

## MCP9600 vs MCP9601

The driver supports both chips. The MCP9601 adds short-circuit and open-circuit detection; these properties raise `RuntimeError` if called on an MCP9600.

## Credits

Inspired by the [Adafruit CircuitPython MCP9600 driver](https://github.com/adafruit/Adafruit_CircuitPython_MCP9600).

## License

MIT License. Copyright (c) 2025-2026 Seth Hardy.