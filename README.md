
# Home Assistant - Local Sengled Integration

**🔥 RESURRECTED PROJECT 🔥**

This integration brings your Sengled smart bulbs back to life after Sengled shut down their cloud servers! Originally designed for Sengled's cloud API, this integration has been completely transformed to work with a **local MQTT add-on architecture**, enabling full local control of your devices.

**No more cloud dependency. Full local control. Your devices, your network.**

## ✨ What This Integration Supports

* **All WiFi Sengled Bulbs** - Standard brightness, color temperature, full RGB
* **Special Devices** - Essential oil diffuser with atomizer controls - who knows what else?
* **Real-time Control** - MQTT-based local communication
* **Rich Device Info** - Firmware versions, signal strength, device diagnostics
* **No Hub Required** - In fact, it ONLY works with "No Hub Required" WiFi bulbs!

## 🏗️ Architecture

This integration works with a companion [**Local Sengled Add-on**](https://github.com/FalconFour/HA-Sengled-Local-Server-AddOn) that:
- Proxies MQTT communication between Home Assistant and your Sengled devices  
- Provides local device discovery and state management
- Stores device information and capabilities
- Runs entirely on your local network

In turn, it also relies on setup workflow from [SengledTools](https://github.com/HamzaETTH/SengledTools) - which needs to be tweaked to point bulbs to the HA add-on's `/bimqtt` and `accessCloud.json` URLs. Yes, it's a bit complicated. But burn-out is a real drag.

**No cloud servers. No external dependencies. Just local control.**

## 🚀 Installation

### Prerequisites
1. **Local Sengled Add-on** - Install the [companion add-on](https://github.com/FalconFour/HA-Sengled-Local-Server-AddOn) first
2. **MQTT Broker** - Home Assistant's Mosquitto broker add-on works perfectly (many things in HA ecosystem already use it - you probably already have this if you've used HA for a while)
3. **Your bulbs to be pointed to the Local Add-On already** - [SengledTools](https://github.com/HamzaETTH/SengledTools) has the WiFi pairing process, just need to adjust it to send the HA add-on URLs that the bulbs will memorize.

### HACS Installation (Recommended)
1. Have HACS installed in Home Assistant  
2. Add `https://github.com/FalconFour/ha-sengled-local` as a custom repository (Type: Integration)
3. Install "Local Sengled Integration" 
4. Configure it in `configuration.yaml` (as below)
5. Restart Home Assistant

### Manual Installation
1. Download this repository as ZIP
2. Extract the `custom_components/sengledapi` folder to `/config/custom_components/sengledapi/` inside HA
3. Restart Home Assistant

## ⚙️ Configuration

Add to your `configuration.yaml`:

```yaml
sengledapi:
  addon_host: "YOUR_HA_IP"     # Add-on IP (usually same as HA)
  addon_port: 54448            # Add-on HTTP API port  
  mqtt_host: "YOUR_HA_IP"      # MQTT broker IP (usually same as HA)
  mqtt_port: 1883              # MQTT broker port
  mqtt_username: "mqttuser"    # Username for connecting to your MQTT broker
  mqtt_password: "mqttpass"    # Password for your MQTT broker
```

## 💡 Usage

After restart, your Sengled devices will appear as:
* **Entities**: `light.sengled_w1f_n84_3a_a2`, `light.sengled_w21_n11_43_52`, etc.
* **Devices**: Each bulb *should* becomes a proper device with model info, firmware version, etc. - but this may not yet be the case (debug/contribution welcome)

## 🐛 Troubleshooting

### Enable Debug Logging

Add `custom_components.sengledapi: debug` to configuration.yaml under `logger`, as below:
```yaml
logger:
  default: warning
  logs:
    custom_components.sengledapi: debug
```

### Common Issues
- **No entities appear**: Check add-on is running and devices are discovered
- **Entities unavailable**: Verify MQTT broker connection and credentials
- **Commands not working**: Check MQTT topics in add-on logs

## 🤝 Contributing

This project was resurrected from the ashes of Sengled's cloud shutdown. Contributions welcome!

**Original Integration**: [@jfarmer08](https://github.com/jfarmer08/ha-sengledapi)  
**Local Architecture**: [@FalconFour](https://github.com/FalconFour/ha-sengled-local)

Found issues? [Report them here](https://github.com/FalconFour/ha-sengled-local/issues)
