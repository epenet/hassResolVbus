# hassResolVbus
A custom component for [Home Assistant](http://home-assistant.io/) to add Resol Vbus status from a Resol-compatible device.

## What's Available?
The custom component will create a sensor with the specified information as attributes.
However, since each device has separate attributes, these need to be specified in the configuration file.

## Getting started
Please check the [Resol Specification](https://github.com/epenet/pyvbus/blob/master/documentation/VBus%20Protocol%20Specification%20-%20English%202011-01-27.pdf) to find your device and corresponding attributes.

To install the component, you will need to copy resolvbus.py and vbuspacket.py to you local configuration folder:
```
 - .homeassistant
 | - custom_components
 | | - sensor
 | | | - resolvbus.py
 | | | - pyvbus
 | | | | - vbuspacket.py
```

In your configuration.yaml, you will need to add a sensor, and set the corresponding attributes:
```
sensor:
  - platform: resolvbus
    name: MyResol
    ttyPort: /dev/ttyUSB0
    filterSource: 0x7321
    filterDestination: 0x0010
    filterCommand: 0x0100
    attributes:
      - name: temperature_sensor_1
        offset: 0
        size: 2
        factor: 0.1
        type: temperature
      - name: system_time
        offset: 18
        size: 2
        type: time
      - name: pump_speed_relay_1
        offset: 10
        size: 1
```

## Converting attributes to sensors
Template sensors can be added to your configuration.yaml to display the attributes as sensors.
```
sensor:
  - platform: template
    sensors:
      myresol_temperature1:
        value_template: '{{ state_attr("sensor.myresol" , "temperature_sensor_1") }}'
        friendly_name: "Temperature 1"
        unit_of_measurement: '°C'
  - platform: template
    sensors:
      myresol1_pump1:
        value_template: '{{ state_attr("sensor.myresol" , "pump_speed_relay_1") }}'
        friendly_name: "Pump 1"
        unit_of_measurement: '%'
```

## Logging
If you are having issues with the component, please enable debug logging in your configuration.yaml, for example:
```
logger:
  default: warn
  logs:
    custom_components.sensor.resolvbus: debug
```
