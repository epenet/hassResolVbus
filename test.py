#!/usr/bin/env python3

import asyncio
import time
import yaml
import binascii
import serial_asyncio
from datetime import datetime, timedelta

# All the shared functions are in this package.
from custom_components.sensor.pyvbus.vbuspacket import (
    VBUSPacket,
    VBUSPacketException
    )

# Load configuration.
config = []
with open("0x7321.yaml", 'r', encoding='utf8') as stream:
    try:
        config = yaml.load(stream)
    except yaml.YAMLError as exc:
        print(exc)

# Get the config.
message = config.get('message')


class logger():
    def error(self, value):
        print("Error: %s" % value)

    def warning(self, value):
        print("Warning: %s" % value)

    def warn(self, value):
        print("Warn: %s" % value)

    def info(self, value):
        print("Info: %s" % value)

    def debug(self, value):
        print("Debug: %s" % value)


class Entity():
    """Fake HASS Entity"""


class ResolVbusSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, name, attributes):
        """Initialize the sensor."""
        _LOGGER.debug("Initialising ResolVbusSensor %s" % name)
        self._state = None
        self._attrsdef = attributes
        self._name = name
        self._attrs = {}
        self._debugmessage = None
        self._ttyPort = None
        self._filterSource = None
        self._filterDestination = None
        self._filterCommand = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        return self._attrs

    def process_packet(self, vbusPacket):
        """Update new state data for the sensor."""
        for item in self._attrsdef:
            attrName = item.get('name', '').lower().replace(' ', '_')
            attrValue = None
            try:
                attrFormat = item.get('format', None)
                if attrFormat == 'time':
                    attrValue = vbusPacket.GetTimeValue(item.get('offset',0),item.get('size',2))
                elif attrFormat == 'temperature':
                    attrValue = vbusPacket.GetTemperatureValue(item.get('offset',0),item.get('size',2), item.get('factor', 1))
                else:
                    attrValue = vbusPacket.GetRawValue(item.get('offset',0),item.get('size',2))
                self._attrs[attrName] = attrValue
            except Exception as e:
                _LOGGER.warning("Attribute %s failed: %s" % (attrName, e))

    def process_buffer(self, buffer):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        # Run standard update
        try:
            _LOGGER.debug("Processing buffer: %s" % binascii.hexlify(buffer))
            vbusPacket = VBUSPacket(buffer)
            self.process_packet(vbusPacket)
        except VBUSPacketException as e:
            _LOGGER.warning("Update failed: %s" % e)

    async def async_update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        # Run standard update
        try:
            if self._debugmessage is not None:
                buffer = bytearray.fromhex(self._debugmessage)
                self.process_buffer(buffer)
            elif self._ttyPort is not None:
                buffer = await self.async_readFromSerial(self._ttyPort, self._filterSource, self._filterDestination, self._filterCommand)
                self.process_buffer(buffer)
        except VBUSPacketException as e:
            _LOGGER.error("Update failed: %s" % e)

    async def async_readFromSerial(self, port, source=None, destination=None, command=None):
        import serial_asyncio
        import serial
        reader, writer = await serial_asyncio.open_serial_connection(
            url=port,
            baudrate=9600
        )

        await reader.readuntil(b'\xaa')  # wait for message start
        try:
            while True:
                buffer = bytearray(b'\xaa')  # initialise new buffer
                buffer.extend(await reader.readuntil(b'\xaa'))
                if len(buffer) >= 5:
                    header_destination = buffer[1] + buffer[2] * 0x100
                    header_source = buffer[3] + buffer[4] * 0x100
                    if source is None or source == header_source:
                        if destination is None or destination == header_destination:
                            return buffer[0:len(buffer)-1]
        finally:
            writer.close()


_LOGGER = logger()

async def async_setup_platform():
    """Setup the sensor platform."""
    device = ResolVbusSensor(config.get('name'),
                             config.get('attributes'))
    device._debugmessage = config.get('message')
    await device.async_update()
    print("%s: %s" % (device.name, device.device_state_attributes))

loop = asyncio.get_event_loop()
buffer = loop.run_until_complete(async_setup_platform())
loop.close()
