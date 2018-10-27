#!/bin/bash
CONFIG_PATH=/data/options.json

MQTT_SERVER="$(jq --raw-output '.mqtt_server' $CONFIG_PATH)" \
python /monitor.py
