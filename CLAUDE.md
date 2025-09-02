# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for controlling Sengled smart bulbs and switches using a local MQTT architecture. Originally designed for Sengled's cloud API, it has been transformed to work with a local add-on that proxies device communication, enabling local control after Sengled's server shutdown. Supports WiFi bulbs and unique devices like the Essential Oil Diffuser with atomizer controls.

## Development Commands

### Testing and Debugging
- Enable debug logging by adding to Home Assistant `configuration.yaml`:
  ```yaml
  logger:
    default: warning
    logs:
      custom_components.sengledapi: debug
  ```

### Installation Testing
- Test manual installation: Copy `custom_components/sengledapi` to Home Assistant config directory
- Test HACS installation: Add repository as custom integration in HACS

## Code Architecture

### Core Components
- **`__init__.py`**: Main integration setup, handles authentication and device discovery
- **`light.py`**: Light entity implementation with brightness, color temperature, and color support
- **`switch.py`**: Switch entity implementation for Sengled switches
- **`const.py`**: Domain constants and configuration keys

### API Layer (`sengledapi/`)
- **`sengledapi.py`**: Main API client with MQTT connection management
- **`devices/`**: Device-specific implementations
  - **`bulbs/`**: Bulb device classes and properties
  - **`switch.py`**: Switch device implementation
  - **`request.py`**: HTTP request handling
  - **`exceptions.py`**: Custom exception classes

### Key Architectural Patterns
- Uses Home Assistant's discovery mechanism for automatic device setup
- Implements both config entry and YAML configuration support
- MQTT client maintains persistent connection for real-time device updates
- Device classes inherit from Home Assistant entity base classes
- Async/await pattern throughout for non-blocking operations

### Configuration Structure
```yaml
sengledapi:
  addon_host: "localhost"        # Local add-on IP (usually HA IP)
  addon_port: 54448             # Local add-on HTTP API port
  mqtt_host: "localhost"        # Local MQTT broker IP  
  mqtt_port: 1883              # Local MQTT broker port
  mqtt_username: "homeassistant" # Optional MQTT credentials
  mqtt_password: "password"      # Optional MQTT credentials
```

### Device Support
- Light entities support: brightness, color temperature (Kelvin), RGB color
- Switch entities for Sengled smart switches  
- Special devices like Essential Oil Diffuser with atomizer controls
- All devices use local MQTT communication (no cloud dependency)
- Real-time status updates via MQTT

### Local Add-on Integration
- Device discovery via HTTP API: `GET /api/devices`
- Add-on provides device storage and MQTT message parsing
- MQTT topics: `wifielement/{MAC}/update` (commands), `wifielement/{MAC}/status` (responses)
- Message format: `[{"dn": "MAC", "type": "command", "value": "value", "time": timestamp}]`

### Dependencies
- `paho-mqtt>=1.6.1` for MQTT communication
- `aiohttp` for add-on API communication
- Home Assistant core components: `light`, `switch`
- Local add-on container running on port 54448

### Security Considerations
- All communication stays within local network
- Optional MQTT broker authentication
- No external cloud dependencies or credentials