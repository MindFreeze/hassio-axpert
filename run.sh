#!/bin/bash
CONFIG_PATH=/data/options.json

MQTT_SERVER="$(jq --raw-output '.mqtt_server' $CONFIG_PATH)" \
MQTT_CLIENT_ID="$(jq --raw-output '.mqtt_client_id' $CONFIG_PATH)" \
MQTT_TOPIC_PARALLEL="$(jq --raw-output '.mqtt_topic_parallel' $CONFIG_PATH)" \
MQTT_TOPIC="$(jq --raw-output '.mqtt_topic' $CONFIG_PATH)" \
python /monitor.py
