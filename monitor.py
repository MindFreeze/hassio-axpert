#! /usr/bin/python

# Axpert Inverter control script

# Read values from inverter, sends values to emonCMS,
# read electric low or high tarif from emonCMS and setting charger and mode to hold batteries fully charged
# controls grid charging current to meet circuit braker maximum alloweble grid current(power)
# calculation of CRC is done by XMODEM mode, but in firmware is wierd mistake in POP02 command, so exception of calculation is done in serial_command(command) function

import time, sys, string
import sqlite3
import json
import datetime
import calendar
import os
import fcntl
import re
import crcmod
from binascii import unhexlify
import paho.mqtt.client as mqtt
from random import randint

def connect():
    global client
    client = mqtt.Client(client_id=os.environ['MQTT_CLIENT_ID'])
    client.connect(os.environ['MQTT_SERVER'])
    try:
        global file
        global fd
        file = open('/dev/hidraw0', 'r+')
        fd = file.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    except Exception as e:
        print('error open file descriptor: ' + str(e))
        exit()

def disconnect():
    file.close()

def serial_command(command):
    print(command)
    try:
        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
        command_crc = command + unhexlify(hex(xmodem_crc_func(command)).replace('0x','',1)) + '\x0d'

        os.write(fd, command_crc)

        response = ''
        timeout_counter = 0
        while '\r' not in response:
            if timeout_counter > 500:
                raise Exception('Read operation timed out')
            timeout_counter += 1
            try:
                response += os.read(fd, 100)
            except Exception as e:
                # print("error reading response...: " + str(e))
                time.sleep(0.01)
            if len(response) > 0 and response[0] != '(' or 'NAKss' in response:
                raise Exception('NAKss')

        print(response)
        response = response.rstrip()
        lastI = response.find('\r')
        response = response[1:lastI-2]
        return response
    except Exception as e:
        print('error reading inverter...: ' + str(e))
        disconnect()
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

def send_data(data, topic):
    try:
        client.publish(topic, data)
    except Exception as e:
        print("error sending to emoncms...: " + str(e))
        return 0
    return 1

def main():
    time.sleep(randint(0, 2)) # so parallel streams might start at different times
    connect();
    serial_number = serial_command('QID')
    print('Reading from inverter ' + serial_number)
    while True:
        data = get_parallel_data()
        # data = '{"TotalAcOutputActivePower": 1000}'
        if not data == '':
            send = send_data(data, os.environ['MQTT_TOPIC_PARALLEL'])

        data = get_data()
        if not data == '':
            send = send_data(data, os.environ['MQTT_TOPIC'].replace('{sn}', serial_number))

        time.sleep(3)

if __name__ == '__main__':
    main()
