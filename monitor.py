#! /usr/bin/python

# Axpert Inverter control script

# Read values from inverter, sends values to mqtt,
# calculation of CRC is done by XMODEM

import time, sys, string
import sqlite3
import json
import datetime
import calendar
import os
import fcntl
import re
import unicodedata
import crcmod.predefined
from binascii import unhexlify
import paho.mqtt.client as mqtt
from random import randint

battery_types = {'0': 'AGM', '1': 'Flooded', '2': 'User'}
voltage_ranges = {'0': 'Appliance', '1': 'UPS'}
output_sources = {'0': 'utility', '1': 'solar', '2': 'battery'}
charger_sources = {'0': 'utility first', '1': 'solar first', '2': 'solar + utility', '3': 'solar only'}
machine_types = {'00': 'Grid tie', '01': 'Off Grid', '10': 'Hybrid'}
topologies = {'0': 'transformerless', '1': 'transformer'}
output_modes = {'0': 'single machine output', '1': 'parallel output', '2': 'Phase 1 of 3 Phase output', '3': 'Phase 2 of 3 Phase output', '4': 'Phase 3 of 3 Phase output'}
pv_ok_conditions = {'0': 'As long as one unit of inverters has connect PV, parallel system will consider PV OK', '1': 'Only All of inverters have connect PV, parallel system will consider PV OK'}
pv_power_balance = {'0': 'PV input max current will be the max charged current', '1': 'PV input max power will be the sum of the max charged power and loads power'}

def connect():
    global client
    client = mqtt.Client(client_id=os.environ['MQTT_CLIENT_ID'])
    client.username_pw_set(os.environ['MQTT_USER'], os.environ['MQTT_PASS'])
    client.connect(os.environ['MQTT_SERVER'])
    print(os.environ['DEVICE'])

def serial_command(command):
    print(command)

    try:
        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
        command_bytes = command.encode('utf-8')
        command_crc_hex = hex(xmodem_crc_func(command_bytes)).replace('0x', '')
        command_crc = command_bytes + unhexlify(command_crc_hex.encode('utf-8')) + b'\x0d'

        try:
            file = open(os.environ['DEVICE'], 'r+')
            fd = file.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        except Exception as e:
            print('error open file descriptor: ' + str(e))
            exit()

        os.write(fd, command_crc)

        response = b''
        timeout_counter = 0
        while b'\r' not in response:
            if timeout_counter > 500:
                raise Exception('Read operation timed out')
            timeout_counter += 1
            try:
                response += os.read(fd, 100)
            except Exception as e:
                time.sleep(0.01)
            if len(response) > 0 and (response[0] != ord('(') or b'NAKss' in response):
                raise Exception('NAKss')

        try:
            response = response.decode('utf-8')
        except UnicodeDecodeError:
            response = response.decode('iso-8859-1')

        print(response)
        response = response.rstrip()
        lastI = response.find('\r')
        response = response[1:lastI-2]

        file.close()
        return response
    except Exception as e:
        print('error reading inverter...: ' + str(e))
        file.close()
        time.sleep(0.1)
        connect()
        return serial_command(command)

def get_parallel_data():
    #collect data from axpert inverter
    try:
        data = '{'
        response = serial_command('QPGS0')
        nums = response.split(' ')
        if len(nums) < 27:
            return ''

        if nums[2] == 'L':
            data += '"Gridmode":1'
        else:
            data += '"Gridmode":0'
        data += ',"SerialNumber": ' + str(int(nums[1]))
        data += ',"BatteryChargingCurrent": ' + str(int(nums[12]))
        data += ',"BatteryDischargeCurrent": ' + str(int(nums[26]))
        data += ',"TotalChargingCurrent": ' + str(int(nums[15]))
        data += ',"GridVoltage": ' + str(float(nums[4]))
        data += ',"GridFrequency": ' + str(float(nums[5]))
        data += ',"OutputVoltage": ' + str(float(nums[6]))
        data += ',"OutputFrequency": ' + str(float(nums[7]))
        data += ',"OutputAparentPower": ' + str(int(nums[8]))
        data += ',"OutputActivePower": ' + str(int(nums[9]))
        data += ',"LoadPercentage": ' + str(int(nums[10]))
        data += ',"BatteryVoltage": ' + str(float(nums[11]))
        data += ',"BatteryCapacity": ' + str(float(nums[13]))
        data += ',"PvInputVoltage": ' + str(float(nums[14]))
        data += ',"TotalAcOutputApparentPower": ' + str(int(nums[16]))
        data += ',"TotalAcOutputActivePower": ' + str(int(nums[17]))
        data += ',"TotalAcOutputPercentage": ' + str(int(nums[18]))
        # data += ',"InverterStatus": ' + nums[19]
        data += ',"OutputMode": ' + str(int(nums[20]))
        data += ',"ChargerSourcePriority": ' + str(int(nums[21]))
        data += ',"MaxChargeCurrent": ' + str(int(nums[22]))
        data += ',"MaxChargerRange": ' + str(int(nums[23]))
        data += ',"MaxAcChargerCurrent": ' + str(int(nums[24]))
        data += ',"PvInputCurrentForBattery": ' + str(int(nums[25]))
        if nums[2] == 'B':
            data += ',"Solarmode":1'
        else:
            data += ',"Solarmode":0'

        data += '}'
    except Exception as e:
        print('error parsing inverter data...: ' + str(e))
        return ''
    return data

def get_data():
    #collect data from axpert inverter
    try:
        response = serial_command('QPIGS')
        nums = response.split(' ')
        if len(nums) < 21:
            return ''

        data = '{'

        data += '"BusVoltage":' + str(float(nums[7]))
        data += ',"InverterHeatsinkTemperature":' + str(float(nums[11]))
        data += ',"BatteryVoltageFromScc":' + str(float(nums[14]))
        data += ',"PvInputCurrent":' + str(int(nums[12]))
        data += ',"PvInputVoltage":' + str(float(nums[13]))
        data += ',"PvInputPower":' + str(int(nums[19]))
        data += ',"BatteryChargingCurrent": ' + str(int(nums[9]))
        data += ',"BatteryDischargeCurrent":' + str(int(nums[15]))
        data += ',"DeviceStatus":"' + nums[16] + '"'

        data += '}'
        return data
    except Exception as e:
        print('error parsing inverter data...: ' + str(e))
        return ''

def get_settings():
    #collect data from axpert inverter
    try:
        response = serial_command('QPIRI')
        nums = response.split(' ')
        if len(nums) < 21:
            return ''

        data = '{'

        data += '"AcInputVoltage":' + str(float(nums[0]))
        data += ',"AcInputCurrent":' + str(float(nums[1]))
        data += ',"AcOutputVoltage":' + str(float(nums[2]))
        data += ',"AcOutputFrequency":' + str(float(nums[3]))
        data += ',"AcOutputCurrent":' + str(float(nums[4]))
        data += ',"AcOutputApparentPower":' + str(int(nums[5]))
        data += ',"AcOutputActivePower":' + str(int(nums[6]))
        data += ',"BatteryVoltage":' + str(float(nums[7]))
        data += ',"BatteryRechargeVoltage":' + str(float(nums[8]))
        data += ',"BatteryUnderVoltage":' + str(float(nums[9]))
        data += ',"BatteryBulkVoltage":' + str(float(nums[10]))
        data += ',"BatteryFloatVoltage":' + str(float(nums[11]))
        data += ',"BatteryType":"' + battery_types[nums[12]] + '"'
        data += ',"MaxAcChargingCurrent":' + str(int(nums[13]))
        data += ',"MaxChargingCurrent":' + str(int(nums[14]))
        data += ',"InputVoltageRange":"' + voltage_ranges[nums[15]] + '"'
        data += ',"OutputSourcePriority":"' + output_sources[nums[16]] + '"'
        data += ',"ChargerSourcePriority":"' + charger_sources[nums[17]] + '"'
        data += ',"MaxParallelUnits":' + str(int(nums[18]))
        data += ',"MachineType":"' + machine_types[nums[19]] + '"'
        data += ',"Topology":"' + topologies[nums[20]] + '"'
        data += ',"OutputMode":"' + output_modes[nums[21]] + '"'
        data += ',"BatteryRedischargeVoltage":' + str(float(nums[22]))
        data += ',"PvOkCondition":"' + pv_ok_conditions[nums[23]] + '"'
        data += ',"PvPowerBalance":"' + pv_power_balance[nums[24]] + '"'
        data += ',"MaxBatteryCvChargingTime":' + str(int(nums[25]))
        
        data += '}'
        return data
    except Exception as e:
        print('error parsing inverter data...: ' + str(e))
        return ''

def send_data(data, topic):
    try:
        client.publish(topic, data, 0, True)
    except Exception as e:
        print("error sending to emoncms...: " + str(e))
        return 0
    return 1

def main():
    time.sleep(randint(0, 5))  # so parallel streams might start at different times
    connect()
    
    serial_number = serial_command('QID')
    print('Reading from inverter ' + serial_number)

    while True:
        try:
            data = get_parallel_data()
            if data != '':
                send_data(data, os.environ['MQTT_TOPIC_PARALLEL'])
            time.sleep(1)
            
            data = get_data()
            if data != '':
                send_data(data, os.environ['MQTT_TOPIC'].replace('{sn}', serial_number))
            time.sleep(1)
            
            data = get_settings()
            if data != '':
                send_data(data, os.environ['MQTT_TOPIC_SETTINGS'])
            time.sleep(4)
        except Exception as e:
            print("Error occurred:", e)
            # Consider handling specific errors or performing a reconnect here
            time.sleep(10)  # Delay before retrying to avoid continuous strain

if __name__ == '__main__':
    main()