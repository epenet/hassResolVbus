"""Support for Resol Vbus."""

import asyncio
import logging
import time
import binascii
from datetime import datetime, timedelta
from .pyvbus.vbuspacket import (
    VBUSPacket,
    VBUSPacketException
    )

import voluptuous as vol

from homeassistant.helpers.entity import Entity

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_NAME

REQUIREMENTS = ['pyserial==3.4', 'pyserial-asyncio==0.4']

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_NAME): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_NAME): cv.string,
})


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Setup the sensor platform."""
    _LOGGER.debug("Initialising resolvbus platform")
    device = ResolVbusSensor(config.get(CONF_NAME),
                             config.get('attributes')
                             )
    if config.get('message', None) is not None:
        device._debugmessage = config.get('message')
    elif config.get('ttyPort', None) is not None:
        device._ttyPort = config.get('ttyPort')
        device._filterSource = config.get('filterSource', None)
        device._filterDestination = config.get('filterDestination', None)
        device._filterCommand = config.get('filterCommand', None)
    devices = [device]
    async_add_entities(devices)


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
