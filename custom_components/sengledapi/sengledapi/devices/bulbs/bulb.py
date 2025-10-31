"""Sengled Bulb Integration."""

import asyncio
import json
import logging
import time

from .const import (
    HTTPS,
    SET_BRIGHTNESS,
    SET_COLOR_TEMPERATURE,
    SET_GROUP,
)

from .bulbproperty import BulbProperty

_LOGGER = logging.getLogger(__name__)
_LOGGER.info("SengledApi: Initializing Bulbs")


class Bulb:
    def __init__(
        self,
        api,
        device_mac,
        friendly_name,
        state,
        device_model,
        isonline,
        support_color,
        support_color_temp,
        support_brightness,
        jsession_id,
        country,
        wifi,
    ):
        _LOGGER.info("SengledApi: Bulb %s initializing.", friendly_name)

        self._api = api
        self._device_mac = device_mac
        self._friendly_name = friendly_name
        self._state = state
        self._available = isonline
        self._device_model = device_model
        self._device_rssi = -30
        self._brightness = 255
        self._color = "255:255:255"
        self._color_temperature = None
        self._rgb_color_r = 255
        self._rgb_color_g = 255
        self._rgb_color_b = 255
        self._alarm_status = 0
        self._wifi_device = wifi
        self._support_color = support_color
        self._support_color_temp = support_color_temp
        self._support_brightness = support_brightness
        self._jsession_id = jsession_id
        self._country = country
        self._firmware_version = None  # Will be populated from device data
        
        # Atomizer/diffuser specific attributes (if applicable)
        self._atomizer_switch = None
        self._atomizer_mode = None 
        self._atomizer_sleep = None
        self._water_state = None
        # self._api._subscribe_mqtt(
        #    "wifielement/{}/status".format(self._device_mac),
        #    self.update_status,
        # )

    async def async_toggle(self, onoff):
        """Toggle Bulb on or off"""
        if onoff == "1":
            self._state = True
        else:
            self._state = False
        # All devices now use local MQTT
        _LOGGER.info(
            "SengledApi: Bulb %s %s turning %s via MQTT.",
            self._friendly_name,
            self._device_mac,
            "on" if onoff == "1" else "off"
        )
        self._api.publish_mqtt(self._device_mac, "switch", onoff)

    async def async_set_brightness(self, brightness):
        """Set Bulb Brightness"""
        # All devices now use local MQTT
        brightness_precentage = round((brightness / 255) * 100)

        _LOGGER.info(
            "SengledApi: Bulb %s %s setting brightness %s via MQTT",
            self._friendly_name,
            self._device_mac,
            str(brightness_precentage),
        )

        self._api.publish_mqtt(self._device_mac, "brightness", str(brightness_precentage))

    async def async_color_temperature(self, color_temperature):
        """Set Color Temperature"""
        _LOGGER.info(
            "SengledApi: Bulb %s %s setting color temperature %s via MQTT",
            self._friendly_name,
            self._device_mac,
            str(color_temperature),
        )
        
        color_temperature_precentage = round(
            self.translate(int(color_temperature), 200, 6500, 1, 100)
        )

        self._api.publish_mqtt(self._device_mac, "colorTemperature", str(color_temperature_precentage))

    async def async_set_color(self, color):
        """
        Set the color of a light device.
        device_id: A single device ID or a list to update multiple at once
        color: [red(0-255), green(0-255), blue(0-255)]
        """
        # All devices now use local MQTT
        _LOGGER.info(
            "SengledApi: Bulb %s %s setting color via MQTT",
            self._friendly_name,
            self._device_mac,
        )

        self._api.publish_mqtt(self._device_mac, "color", self.convert_color_HA(color))
        self._state = True

    def is_on(self):
        """Get State"""
        return self._state

    async def async_update(self):
        """Update device status from local add-on API."""
        _LOGGER.debug("SengledApi: Bulb %s %s updating from local API", 
                     self._friendly_name, self._device_mac)
        try:
            import aiohttp
            # Access add-on connection info through the API object  
            async with aiohttp.ClientSession() as session:
                url = f"http://{self._api.addon_host}:{self._api.addon_port}/api/device/{self._device_mac}"
                async with session.get(url) as response:
                    if response.status == 200:
                        api_response = await response.json()
                        if api_response.get("success") and "device" in api_response:
                            attrs = api_response["device"]["attributes"]

                            # Update device availability and signal strength
                            self._available = True
                            self._device_rssi = int(attrs.get("deviceRssi", -50))

                            # Only update state from API if it's actually different and makes sense
                            # This prevents the add-on's potentially stale state from overriding our commands
                            api_state = attrs.get("switch") == "1"
                            if api_state != self._state:
                                _LOGGER.warning(
                                    "SengledApi: State mismatch for %s - local:%s, API:%s - keeping local state",
                                    self._friendly_name, self._state, api_state
                                )
                            # Don't update self._state from API - trust the local state we set
                            
                            # Update brightness (convert 0-100 to 0-255)
                            if self._support_brightness and "brightness" in attrs:
                                self._brightness = round((int(attrs["brightness"]) / 100) * 255)
                            
                            # Update color temperature (convert 0-100 to 2000-6500K)
                            if self._support_color_temp and "colorTemperature" in attrs:
                                temp_percent = int(attrs["colorTemperature"])
                                self._color_temperature = round(self.translate(temp_percent, 0, 100, 2000, 6500))
                            
                            # Update color (format: "r:g:b")
                            if self._support_color and "color" in attrs:
                                self._color = attrs["color"]
                            
                            # Update firmware version if available
                            if "version" in attrs:
                                self._firmware_version = attrs["version"]
                            
                            # Update atomizer/diffuser attributes if present
                            if "atomizerSwitch" in attrs:
                                self._atomizer_switch = attrs["atomizerSwitch"] 
                            if "atomizerMode" in attrs:
                                self._atomizer_mode = attrs["atomizerMode"]
                            if "atomizerSleep" in attrs:
                                self._atomizer_sleep = attrs["atomizerSleep"]
                            if "waterState" in attrs:
                                self._water_state = attrs["waterState"]
                                
                            _LOGGER.debug("SengledApi: Updated %s - state:%s, brightness:%s", 
                                        self._friendly_name, self._state, self._brightness)
                        else:
                            _LOGGER.warning("Add-on API returned unsuccessful response for %s", self._device_mac)
                            self._available = False
                    else:
                        _LOGGER.warning("Failed to update device %s: HTTP %s", self._device_mac, response.status)
                        self._available = False
                        
        except Exception as e:
            _LOGGER.error("Error updating device %s: %s", self._device_mac, e)
            self._available = False

    def update_status(self, message):
        """
        Update the status from an incoming MQTT message.
        message -- the incoming message. This is not used.
        """
        try:
            data = json.loads(message)
            _LOGGER.debug("SengledApi: Update Status from MQTT %s", str(data))
        except ValueError:
            return

        for status in data:
            if "type" not in status or "dn" not in status:
                continue

            if status["dn"] == self._device_mac:
                if status["type"] == "color":
                    self._color = status["value"]
                if status["type"] == "colorMode":
                    self._color_mode = status["value"]
                if status["type"] == "brightness":
                    self._brightness = status["value"]
                if status["type"] == "colorTemperature":
                    self._color_temperature = status["value"]

    def set_attribute_update_callback(self, callback):
        """
        Set the callback to be called when an attribute is updated.
        callback -- callback
        """
        self.attribute_update_callback = callback

    @staticmethod
    def attribute_to_property(attr):
        attr_map = {
            "consumptionTime": "consumption_time",
            "deviceRssi": "rssi",
            "identifyNO": "identify_no",
            "productCode": "product_code",
            "saveFlag": "save_flag",
            "startTime": "start_time",
            "supportAttributes": "support_attributes",
            "timeZone": "time_zone",
            "typeCode": "type_code",
        }

        return attr_map.get(attr, attr)

    def convert_color_HA(self, HACOLOR):
        sengled_color = str(HACOLOR)
        for r in ((" ", ""), (",", ":"), ("(", ""), (")", "")):
            sengled_color = sengled_color.replace(*r)
        return sengled_color

    def translate(self, value, left_min, left_max, right_min, right_max):
        """Figure out how 'wide' each range is"""
        left_span = left_max - left_min
        right_span = right_max - right_min

        # Convert the left range into a 0-1 range (float)
        value_scaled = float(value - left_min) / float(left_span)

        # Convert the 0-1 range into a value in the right range.
        return right_min + (value_scaled * right_span)
