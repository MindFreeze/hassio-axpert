This is a Hassio addon to monitor [voltronic axpert inverters](http://www.voltronicpower.com/oCart2/index.php?route=product/product&product_id=123) through USB and publish the data as JSON to an MQTT broker. It publishes the data to 2 topics:
- 'power/axpert' for the parallel data (some of these values seem to be only for the connected inverter even though they are returned by the parallel data command)
- 'power/axpert' for the data from the connected inverter
You can then configure the sensors in Home Assistant like this:
```
sensors:
  - platform: mqtt
    name: "Power"
    state_topic: "power/axpert"
    unit_of_measurement: 'W'
    value_template: "{{ value_json.TotalAcOutputActivePower }}"
    expire_after: 60
```

The values published on 'power/axpert' are:
- TotalAcOutputActivePower
- TotalAcOutputApparentPower
- TotalAcOutputPercentage
- BatteryChargingCurrent
- BatteryDischargeCurrent
- TotalChargingCurrent
- GridVoltage
- GridFrequency
- OutputVoltage
- OutputFrequency
- OutputAparentPower
- OutputActivePower
- LoadPercentage
- BatteryVoltage
- BatteryCapacity
- PvInputVoltage
- OutputMode
- ChargerSourcePriority
- MaxChargeCurrent
- MaxChargerRange
- MaxAcChargerCurrent
- PvInputCurrentForBattery
- Gridmode
- Solarmode
- Gridmode
- Gridmode
- Gridmode

The values published on 'power/axpert1' are:
- BusVoltage
- InverterHeatsinkTemperature
- BatteryVoltageFromScc

I have 3 inverters in parallel and a raspberry connected to 1 of them with a USB cable . Linux doesn't seem to recognize it as a USB to Serial device and it only shows up as `/dev/hidraw0`.
