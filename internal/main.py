#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import certifi
import ssl
import requests
import sys
import os
import uuid

from typing import *
from enum import Enum

from IPython import embed

#########
# Enums #
#########

class CMD(str, Enum):
    TUTORIAL = "tutorial"
    DISPLAY = "display"
    SWITCH = "switch"
    PREFERENCE = "preference"
    LIGHT_BEACON = "light-beacon-mode"
    SAFETY_FEATURE = "safety-feature-mode"
    SET_TIMEZONE = "setTimezone"
    KNOCKING = "knocking"
    LED = "led"
    SOUND = "sound"
    OTA_UPGRADE = "ota-upgrade"
    WIFI_SCAN = "wifi-scan"
    SENSOR_SERVER = "sensor-server"

class DISPLAY_MODE(str, Enum):
        TEMP = "temp"
        HUMID = "humid"
        VOC = "voc"
        DUST = "dust"
        CO2 = "co2"
        WHITE_SOLID = "white_solid"
        WHITE_BLINK = "white_blink"

###########
# Classes #
###########

class AwairApi:
    def __init__(self, url: str, access_token: str = None):
        self.url = url
        self.user_id = None
        self.mqtt_token = None
        self.access_token = access_token

    def get(self, route: str, data: dict):
        if self.access_token:
            hdrs = {'Authorization': f'Bearer {self.access_token}'}
            r = requests.get(f'{self.url}{route}', json=data, headers=hdrs)
        else:
            r = requests.get(f'{self.url}{route}', json=data)
        if not r.ok:
            raise Exception(f'req failed: {self.url}{route}')
        return r.json()

    def post(self, route: str, data: dict):
        if self.access_token:
            hdrs = {'Authorization': f'Bearer {self.access_token}'}
            r = requests.post(f'{self.url}{route}', json=data, headers=hdrs)
        else:
            r = requests.post(f'{self.url}{route}', json=data)
        if not r.ok:
            raise Exception(f'req failed: {self.url}{route}, resp: {r.text}')
        return r.json()

class AwairInternalApi(AwairApi):
    def __init__(self, access_token: str):
            super().__init__('https://internal.awair.is', access_token=access_token)

    def command(self, device: dict, cmd: CMD, payload):
        #@POST("v1/devices/{deviceType}/{deviceId}/commands/{commandType}")
        #Observable<Object> postCommand(@Path("deviceType") String str, @Path("deviceId") Integer num, @Path("commandType") String str2, @Body Object obj);

        device_type = device['device_type']
        device_id = device['device_id']
        payload = {'payload':payload}
        r = self.post(f'/v1/devices/{device_type}/{device_id}/commands/{cmd}', payload)
        print(f'Command "{cmd}" completed')
        return r

    def ota_upgrade(self, device, version: str = "latest"):
        return self.command(device, CMD.OTA_UPGRADE, {"desired_version": version})

    def set_display_mode(self, device, mode: DISPLAY_MODE):
        return self.command(device, CMD.DISPLAY, {"mode": mode})

    def get_devices(self) -> dict:
        return self.get('/v1.1/users/self/devices', {})['data']

class AwairMobileApi(AwairApi):
    def __init__(self):
            super().__init__('https://mobile-app.awair.is')

    def login(self, email: str, passwd: str) -> Tuple:
        r = self.post('/v1/users/login', {'email':email,'password':passwd})
        self.user_id = r['userId']
        self.access_token = r['accessToken']
        print('[MobileApi]: logged in')

    def get_mqtt_token(self) -> str:
        if self.mqtt_token is None:
            self.mqtt_token = self.post('/v1/users/self/mqtt-token', {})['mqttAccessToken']
        return self.mqtt_token

class AwairMqttClient:
    # XXX These may be useful.. WIP
    # OTHER_TOPICS = ['change_degree_of_unit', 'change_device_name', 'change_device_notification_setting',
    #     'change_device_sleep_report_setting', 'change_location', 'change_preference',
    #     'change_space', 'change_trigger', 'dismiss_add_balloon', 'finish_registration',
    #     'get_space'
    # ]
    # SUBSCRIBE_TOPICS = ['mqtt_subscribe_battery', 'mqtt_subscribe_display',
    #     'mqtt_subscribe_ota_upgrade', 'mqtt_subscribe_score']

    def __init__(self, mqttToken):
        mqttc = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            clean_session=True,
            client_id=str(uuid.uuid4())[:22],
            userdata=[],
        )

        mqttc.username_pw_set(mqttToken)
        mqttc.on_connect = self.on_connect
        mqttc.on_message = self.on_message
        mqttc.on_subscribe = self.on_subscribe
        mqttc.on_unsubscribe = self.on_unsubscribe
        mqttc.tls_set(certifi.where())
        mqttc.tls_insecure_set(True)
        self.mqttc = mqttc

    def connect(self) -> None:
        self.mqttc.connect("messaging.awair.is", 8883, 60)

    def loop(self) -> None:
        self.mqttc.loop_forever()

    @staticmethod
    def on_subscribe(client, userdata, mid, reason_code_list, properties):
        # Since we subscribed only for a single channel, reason_code_list contains
        # a single entry
        if reason_code_list[0].is_failure:
            print(f"Broker rejected you subscription: {reason_code_list[0]}")
        else:
            print(f"Broker granted the following QoS: {reason_code_list[0].value}")

    @staticmethod
    def on_unsubscribe(client, userdata, mid, reason_code_list, properties):
        # Be careful, the reason_code_list is only present in MQTTv5.
        # In MQTTv3 it will always be empty
        if len(reason_code_list) == 0 or not reason_code_list[0].is_failure:
            print("unsubscribe succeeded (if SUBACK is received in MQTTv3 it success)")
        else:
            print(f"Broker replied with failure: {reason_code_list[0]}")
        client.disconnect()

    @staticmethod
    def on_message(client, userdata, message):
        print(f'message: {message}')
        userdata.append(message.payload)

    @staticmethod
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"Failed to connect: {reason_code}. loop_forever() will retry connection")
        else:
            print('mqtt connected')
            # XXX No luck with these
            # client.subscribe("mqtt_subscribe_ota_upgrade", 1)
            # client.subscribe("/mqtt_subscribe_ota_upgrade")
            # client.subscribe("mqtt_subscribe_ota_upgrade")
            # client.subscribe("$SYS/#", 0)
            # client.subscribe("score/format/json")

if __name__ == '__main__':
    # You must create a passwork by using the password reset feature
    # at https://account.getawair.com/forgot-password
    email = os.environ.get("AWAIR_EMAIL")
    passwd = os.environ.get("AWAIR_PASSWORD")

    # Login using the mobile api
    mobile_api = AwairMobileApi()
    mobile_api.login(email, passwd)

    # Re-use the mobile api access token to login into the
    # internal api >.>
    internal_api = AwairInternalApi(mobile_api.access_token)
    devices = internal_api.get_devices()

    print('[+] Found devices via internal API:')
    print(devices)

    # Example of modifying display mode via the internal API

    # internal_api.set_display_mode(devices[0], DISPLAY_MODE.TEMP)
    # internal_api.set_display_mode(devices[0], DISPLAY_MODE.HUMID)

    # Drop to a REPL
    # embed(colors='linux')

    # MQTT not flushed out at this time #
    if False:
        mqtt_token = mobile_api.get_mqtt_token()
        print(f'MQTT token: {mqtt_token}')
        mqtt_client = AwairMqttClient(mqtt_token)
        mqtt_client.connect()
        mqtt_client.loop()
