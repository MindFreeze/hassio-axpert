#! /usr/bin/python

import time, sys, string
import os
import fcntl
import re
import crcmod
from binascii import unhexlify

try:
    file = open('/dev/hidraw0', 'r+')
    fd = file.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
except Exception as e:
    print("error open file descriptor: " + str(e))
    exit()

try:
    command = sys.argv[1]
    print(command)
    byte_cmd = command.encode()
    xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
    print(hex(xmodem_crc_func(byte_cmd)))
    # print(hex(xmodem_crc_func(command)).replace("0x","",1))
    command_crc = byte_cmd + unhexlify(hex(xmodem_crc_func(byte_cmd)).replace('0x','',1)) + '\x0d'.encode()
    print(command_crc)

#    command_crc = '\x50\x4f\x50\x30\x32\xe2\x0b\x0d'
    # file.write(command_crc)
    os.write(fd, command_crc)

    response = ''
    timeout_counter = 0
    while '\r' not in response:
        if timeout_counter > 1000:
            if len(response) > 0:
                break
            else:
                raise Exception('Read operation timed out')
        timeout_counter += 1
        try:
            response += os.read(fd, 2)
        except Exception as e:
            print("error reading response...: " + str(e))
            time.sleep(0.02)
        if 'NAK' in response:
            raise Exception('NAK')
    file.close()

except Exception as e:
    print("error reading inverter...: " + str(e))
    exit()

print(response)
print(len(response))
