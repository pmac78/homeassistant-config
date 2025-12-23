# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Home Assistant configuration for an off-grid solar/battery-powered setup (likely a van or similar mobile installation). The system focuses on energy management, water monitoring, and smart load control.

**Home Assistant Version:** 2025.11.3

## Configuration Structure

The main configuration uses YAML includes to split functionality:

- `configuration.yaml` - Main entry point with include directives
- `automations.yaml` - Automation rules
- `templates.yaml` - Template sensors and binary sensors (Jinja2)
- `sensors.yaml` - Integration, derivative, filter, and statistics sensors
- `input_number.yaml` - User-configurable values (e.g., battery capacity)
- `input_boolean.yaml` - Toggle switches
- `utility_meter.yaml` - Daily/weekly counters
- `compensation.yaml` - Calibration curves for sensors
- `mqtt_dvcc.yaml` - MQTT configuration for Victron DVCC
- `scripts.yaml`, `scenes.yaml`, `timer.yaml` - Supporting automation files

## Key Integrations

### Custom Components
- **HACS** - Home Assistant Community Store
- **victron_mqtt** - Victron energy system via MQTT
- **solcast_solar** - Solar production forecasting
- **smartvanio** - Smart van I/O integration
- **mcp_server_http_transport** - MCP server transport

### Hardware
- **Victron Energy System** - Battery, solar, inverter via GX device (MQTT)
- **Shelly Pro 4PM** (x2) - AC circuit power monitoring (8 circuits total)
- **Shelly Plus Uni** - Water tank voltage sensor
- **ZHA** - Zigbee switches and buttons
- **WLED** - Addressable LED lighting
- **ESPHome** - Custom ESP32 with 16x INA226 current/voltage monitors

## Core Sensor Architecture

### Energy Flow Tracking
The system distinguishes between:
- **DC Consumption** (`sensor.victron_dc_consumption_power`) - DC loads only
- **Total System Consumption** (`sensor.total_system_consumption_power`) - DC loads + inverter
- **Battery Power** - Split into charge/discharge components for accurate energy accounting

### Battery Prediction System
Multiple prediction methods are implemented:
1. **Forecast method** - Uses Solcast hourly solar forecasts
2. **Profiled method** - Uses 24-hour load profile (hourly buckets averaged over 3 days)

Key prediction sensors:
- `sensor.battery_predicted_end_of_day_soc_profiled`
- `sensor.battery_soc_at_sunrise_profiled`
- `sensor.battery_full_by_sunset_forecast`
- `sensor.battery_autonomy_avg_load` / `sensor.battery_autonomy_current_load`

### 24-Hour Load Profile
Template sensors capture hourly consumption buckets (`sensor.total_usage_hour_XX_raw`), which feed into statistics sensors (`sensor.total_usage_hour_XX_mean`) for 3-day averages per hour.

### Water Tank Monitoring
Two-tank system with:
- Smoothed level sensors with outlier filtering
- Fill/usage rate detection (2 L/min threshold)
- Volume integration for cumulative tracking
- Days remaining prediction

## HWS (Hot Water System) Control

The `automations.yaml` contains a sophisticated solar-powered water heating control system:
- **Predictive start** - Calculates if solar forecast can afford a heating cycle
- **Surplus-based start** - Traditional method using current surplus power
- **Score-based decisions** - `sensor.hws_heating_score` weights multiple factors (0-100+ points)
- **Safety stops** - Battery SoC limits, sunset cutoff

HWS operates in ECO (900W) or BOOST (1800W) modes based on available solar surplus.

## Important Entity Naming Patterns

- Victron sensors: `sensor.victron_mqtt_*`
- Battery: `sensor.victron_mqtt_system_0_system_dc_battery_*`
- Solar: `sensor.victron_mqtt_system_0_system_dc_pv_power`
- Solcast: `sensor.solcast_pv_forecast_*`
- Shelly power: `sensor.shellypro4pm_*_switch_N_power`
- Water tanks: `sensor.tank_1_level_smoothed`, `sensor.tank_2_level_smoothed`

## Validation

```bash
# Check configuration syntax (run from HA container/install)
hass --script check_config

# Validate YAML syntax only
python -c "import yaml; yaml.safe_load(open('configuration.yaml'))"
```

## Notes

- Secrets are stored in `secrets.yaml` (gitignored)
- The `.storage/` directory contains tokens and auth (gitignored)
- ESPHome configs are in `esphome/` directory
- Battery capacity is configured via `input_number.battery_capacity_kwh` (default: 15.2 kWh)
