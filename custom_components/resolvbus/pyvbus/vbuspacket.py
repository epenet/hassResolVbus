#  pyvbus
#  ---------------
#  A Python library for processing RESOL VBus data.
#
#  Author:  epenet <erwann@zeflip.com> (c) 2019
#  Website: https://github.com/epenet/pyvbus
#  License: MIT (see LICENSE file)


class VBUSPacketException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class VBUSPacket(object):
    _buffer = None

    _header_syncbyte = None
    _header_destination = None
    _header_source = None
    _header_protocol = None
    _header_command = None
    _header_framecount = None
    _header_checksum = None
    _header_offset = None

    _allframes = None

    @property
    def header_destination(self):
        return self._header_destination

    @property
    def header_source(self):
        return self._header_source

    @property
    def header_protocol(self):
        return self._header_protocol

    @property
    def header_command(self):
        return self._header_command

    @property
    def header_framecount(self):
        return self._header_framecount

    @property
    def header_checksum(self):
        return self._header_checksum

    @property
    def supported_protocols(self):
        return [0x10]

    def __init__(self, buffer):
        self._buffer = buffer

        if not self._buffer[0] == 0xaa:
            raise VBUSPacketException('Buffer does not start with SYNC byte')

        if len(self._buffer) < 6:
            raise VBUSPacketException(
                'Buffer length expected greater or equal to 6 (got %s)' %
                len(self._buffer)
            )

        self._header_syncbyte = self._buffer[0]
        self._header_destination = self._buffer[1] + self._buffer[2] * 0x100
        self._header_source = self._buffer[3] + self._buffer[4] * 0x100
        self._header_protocol = self._buffer[5]

        if self._header_protocol not in self.supported_protocols:
            raise VBUSPacketException(
                'Unsupported protocol version: %s' % self._header_protocol
            )

        if self._header_protocol == 0x10:
            if len(self._buffer) < 10:
                raise VBUSPacketException(
                    'Buffer length expected greater or equal to 10 (got %s)' %
                    len(self._buffer)
                )

            self._header_command = self._buffer[6] + self._buffer[7] * 0x100
            self._header_framecount = self._buffer[8]
            self._header_checksum = self._buffer[9]
            self._header_offset = 10

            calculated_checksum = self.vbus_calccrc(1, 8)
            if self._header_checksum != calculated_checksum:
                raise VBUSPacketException(
                    'Invalid header checksum: expected %s got %s' % (
                        self._header_checksum,
                        calculated_checksum
                    )
                )

            expectedlength = self._header_offset + self._header_framecount * 6
            if len(buffer) != expectedlength:
                raise VBUSPacketException(
                    "Invalid frame count: expected %s got %s" % (
                        expectedlength,
                        len(buffer)
                    )
                )

            self.vbus_0x10_decodeframes()
        else:
            raise VBUSPacketException(
                'Unsupported protocol version: %s' % self._header_protocol
            )

    def vbus_calccrc(self, offset, length):
        crc = 0x7F
        for i in range(length):
            crc = (crc - self._buffer[offset + i]) & 0x7F
        return crc

    def vbus_extractseptett(self, offset, length):
        septett = 0
        for i in range(length):
            if self._buffer[offset + i] == 0x80:
                self._buffer[offset + i] &= 0x7F
                septett |= 1 << i
        self._buffer[offset + length] = septett
        return septett

    def vbus_injectseptett(self, offset, length):
        septett = self._buffer[offset + length]
        index = 0

        for i in range(length):
            if not septett & (1 << i) == 0:
                index = offset + i
                self._buffer[index] |= 0x80

    def vbus_0x10_decodeframes(self):
        for data_byte in self._buffer[1:]:
            if data_byte & 0x80 > 0x7F:
                raise VBUSPacketException(
                    'Byte (%s) has its MSB set: %s' % (
                        data_byte,
                        data_byte & 0x80 > 0x7
                    )
                )

        self._allframes = ['\x00'] * 4 * self._header_framecount

        for i in range(self._header_framecount):
            self.vbus_0x10_decodeframe(self._header_offset+6*i, 4*i)

    def vbus_0x10_decodeframe(self, source_offset, target_offset):
        frame_checksum = self.vbus_calccrc(source_offset, 5)
        if not frame_checksum == self._buffer[source_offset+5]:
            raise VBUSPacketException(
                'Data frame checksum invalid: expected %s got %s' % (
                    self._buffer[source_offset+5],
                    frame_checksum
                    )
                )

        self.vbus_injectseptett(source_offset, 4)

        for i in range(4):
            self._allframes[target_offset + i] = self._buffer[source_offset+i]

    def GetRawValue(self, offset, size):
        bit_size = size * 8
        value = 0

        if len(self._allframes) < (offset + size):
            raise VBUSPacketException(
                'Invalid offset (%s) and size (%s)' % (
                    offset,
                    size
                    )
                )

        for i in range(size):
            value += self._allframes[(offset+i)] << (8*i)

        return value

    def GetTemperatureValue(self, offset, size, factor=0.1):
        value = self.GetRawValue(offset, size)

        bits = size * 8
        if value >= 1 << (bits - 1):
            value -= 1 << bits

        if factor < 1:
            value = value / (1/factor)
        elif factor > 1:
            value = value * factor

        return value

    def GetTimeValue(self, offset, size):
        value = self.GetRawValue(offset, size)

        hours = value//60
        minutes = value - hours*60
        value = "%02d:%02d" % (hours, minutes)

        return value
