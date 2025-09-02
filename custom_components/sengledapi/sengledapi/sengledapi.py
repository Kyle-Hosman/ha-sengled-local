#!/usr/bin/python3
"""Local Sengled Bulb Integration."""
import json
import logging
import time

import paho.mqtt.client as mqtt

from .devices.bulbs.bulb import Bulb
from .devices.bulbs.bulbproperty import BulbProperty
from .devices.switch import Switch

_LOGGER = logging.getLogger(__name__)


class SengledSession:

    addon_host = "localhost"
    addon_port = 8080
    mqtt_host = "localhost"
    mqtt_port = 1883
    mqtt_username = None
    mqtt_password = None
    mqtt_client = None
    subscribe = {}
    devices = []


SESSION = SengledSession()


class SengledApi:
    def __init__(self, addon_host, addon_port, mqtt_host, mqtt_port, mqtt_username, mqtt_password):
        _LOGGER.info("Local Sengled Api initializing.")
        SESSION.addon_host = addon_host
        SESSION.addon_port = addon_port
        SESSION.mqtt_host = mqtt_host
        SESSION.mqtt_port = mqtt_port
        SESSION.mqtt_username = mqtt_username
        SESSION.mqtt_password = mqtt_password

    async def async_init(self):
        _LOGGER.info("Local Sengled Api initializing async.")
        # No authentication needed - just initialize MQTT connection
        return await self.async_initialize_mqtt()

# Old cloud authentication methods removed - no longer needed for local setup

    def is_valid_connection(self):
        # For local setup, we just check if MQTT client exists - connection is async
        return SESSION.mqtt_client is not None

# Old cloud server discovery methods removed - no longer needed

    async def async_get_devices_from_addon(self):
        """
        Get list of devices from local add-on API.
        """
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{SESSION.addon_host}:{SESSION.addon_port}/api/devices"
                async with session.get(url) as response:
                    if response.status == 200:
                        api_response = await response.json()
                        _LOGGER.debug("SengledApi: Got devices from add-on: %s", api_response)
                        
                        if api_response.get("success") and "devices" in api_response:
                            # Clear existing devices and repopulate
                            SESSION.devices = []
                            devices_data = api_response["devices"]
                            
                            for mac, device_info in devices_data.items():
                                # Convert add-on format to BulbProperty format
                                bulb_data = {
                                    "deviceUuid": mac,
                                    "attributeList": []
                                }
                                
                                # Add capabilities as supportAttributes
                                capabilities = device_info.get("capabilities", [])
                                bulb_data["attributeList"].append({
                                    "name": "supportAttributes", 
                                    "value": ",".join(capabilities)
                                })
                                
                                # Convert attributes dict to attributeList format
                                for attr_name, attr_value in device_info.get("attributes", {}).items():
                                    bulb_data["attributeList"].append({
                                        "name": attr_name,
                                        "value": str(attr_value)
                                    })
                                
                                SESSION.devices.append(BulbProperty(self, bulb_data, True))
                        else:
                            _LOGGER.error("Add-on API returned unsuccessful response: %s", api_response)
                    else:
                        _LOGGER.error("Failed to get devices from add-on API: %s", response.status)
        except Exception as e:
            _LOGGER.error("Error connecting to add-on API: %s", e)
        
        return SESSION.devices

    async def async_get_devices(self):
        """Get devices from local add-on instead of cloud API."""
        _LOGGER.debug("SengledApi: Get Devices from local add-on.")
        return await self.async_get_devices_from_addon()

    async def discover_devices(self):
        _LOGGER.info("SengledApi: List All Bulbs from local add-on.")
        bulbs = []
        for device in await self.async_get_devices():
            bulbs.append(
                Bulb(
                    self,
                    device.uuid,
                    device.name,
                    device.switch,
                    device.typeCode,
                    device.isOnline,
                    device.support_color,
                    device.support_color_temp,
                    device.support_brightness,
                    None,  # No session ID needed for local MQTT
                    None,  # No country code needed
                    True,  # All devices use MQTT now
                )
            )
        return bulbs

    async def async_list_switch(self):
        _LOGGER.info("Sengled Api listing switches.")
        switch = []
        for device in await self.async_get_devices():
            _LOGGER.debug(device)
            if "lampInfos" in device:
                for switch in device["lampInfos"]:
                    if switch["attributes"]["productCode"] == "E1E-G7F":
                        switch.append(
                            Switch(
                                self,
                                device["deviceUuid"],
                                device["attributes"]["name"],
                                ("on" if device["attributes"]["onoff"] == 1 else "off"),
                                device["attributes"]["productCode"],
                                self._access_token,
                                SESSION.countryCode,
                            )
                        )
        return switch

# Old cloud HTTP request methods removed - no longer needed

    async def async_initialize_mqtt(self):
        _LOGGER.info("SengledApi: Initialize local MQTT connection")
        import asyncio

        connection_result = {"connected": False}

        def on_message(client, userdata, msg):
            _LOGGER.debug("MQTT message received: %s %s", msg.topic, msg.payload)
            if msg.topic in SESSION.subscribe:
                SESSION.subscribe[msg.topic](msg.payload)

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                _LOGGER.info("Connected to local MQTT broker")
                connection_result["connected"] = True
            else:
                _LOGGER.error("Failed to connect to MQTT broker: %s", rc)
                connection_result["connected"] = False

        def on_disconnect(client, userdata, rc):
            _LOGGER.warning("Disconnected from MQTT broker: %s", rc)

        SESSION.mqtt_client = mqtt.Client(client_id="sengled_local_integration")
        SESSION.mqtt_client.on_message = on_message
        SESSION.mqtt_client.on_connect = on_connect
        SESSION.mqtt_client.on_disconnect = on_disconnect

        # Set credentials if provided
        if SESSION.mqtt_username and SESSION.mqtt_password:
            SESSION.mqtt_client.username_pw_set(SESSION.mqtt_username, SESSION.mqtt_password)

        # Connect to local broker (no SSL, no websockets)
        try:
            SESSION.mqtt_client.connect_async(
                SESSION.mqtt_host,
                port=SESSION.mqtt_port,
                keepalive=60,
            )
            SESSION.mqtt_client.loop_start()
            
            # Wait a bit for connection to establish
            for _ in range(10):  # Wait up to 1 second
                await asyncio.sleep(0.1)
                if connection_result["connected"]:
                    return True
                    
            _LOGGER.warning("MQTT connection taking longer than expected, continuing anyway")
            return True  # Continue even if connection is slow
            
        except Exception as e:
            _LOGGER.error("Failed to connect to local MQTT broker: %s", e)
            return False

    def reinitialize_mqtt(self):
        _LOGGER.info("SengledApi: Re-initialize local MQTT connection")
        if SESSION.mqtt_client is None:
            return False

        SESSION.mqtt_client.loop_stop()
        SESSION.mqtt_client.disconnect()
        
        # Simple reconnection for local broker
        try:
            SESSION.mqtt_client.reconnect()
            SESSION.mqtt_client.loop_start()
            
            # Re-subscribe to all topics
            for topic in SESSION.subscribe:
                self.subscribe_mqtt(topic, SESSION.subscribe[topic])
                
            return True
        except Exception as e:
            _LOGGER.error("Failed to reinitialize MQTT: %s", e)
            return False

    def publish_mqtt(self, device_mac, command_type, value):
        """Publish command in the format expected by local add-on"""
        _LOGGER.info("SengledApi: Publishing MQTT command to %s: %s=%s", device_mac, command_type, value)
        
        if SESSION.mqtt_client is None:
            _LOGGER.error("MQTT client not initialized")
            return False

        topic = f"wifielement/{device_mac}/update"
        
        # Create payload in format: [{"dn": "MAC", "type": "command", "value": "value", "time": timestamp}]
        import time
        payload = [{
            "dn": device_mac,
            "type": command_type,
            "value": str(value),
            "time": int(time.time() * 1000)  # Unix timestamp in milliseconds
        }]
        
        import json
        payload_json = json.dumps(payload)
        
        _LOGGER.debug("Publishing to topic %s: %s", topic, payload_json)
        
        r = SESSION.mqtt_client.publish(topic, payload=payload_json)
        _LOGGER.debug("SengledApi: Publish Mqtt %s", str(r))
        
        try:
            r.wait_for_publish()
            return r.is_published
        except ValueError:
            pass

        return False

    def subscribe_mqtt(self, topic, callback):
        _LOGGER.info("SengledApi: Subscribe to an MQTT Topic")
        if SESSION.mqtt_client is None:
            return False

        r = SESSION.mqtt_client.subscribe(topic)
        _LOGGER.info("SengledApi: Subscribe Mqtt %s", str(r))
        if r[0] != mqtt.MQTT_ERR_SUCCESS:
            return False

        SESSION.subscribe[topic] = callback
        return True

    def unsubscribe_mqtt(self, topic, callback):
        _LOGGER.info("SengledApi: Unsubscribe from an MQTT topic")
        if topic in SESSION.subscribe:
            del SESSION.subscribe[topic]
