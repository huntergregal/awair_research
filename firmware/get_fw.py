#!/usr/bin/env python3
import requests
import os, sys

# GLOBAL CONFIG - Fill this with your info
DEVICE_TYPE = 'awair-element'
DEVICE_ID = os.environ.get('AWAIR_DEVICE_ID')
DEVICE_TOKEN = os.environ.get('AWAIR_DEVICE_TOKEN')

def dl_fw(version: str):
    url = 'https://ota.awair.is'
    api = f'v2/devices/{DEVICE_TYPE}/{DEVICE_ID}/upgrade?type={DEVICE_TYPE}&version={version}'
    hdrs = {'Authorization': f'Bearer {DEVICE_TOKEN}'}
    r = requests.get(f'{url}/{api}', headers=hdrs)

    if r.status_code == 204:
        print('[!] No content - Bad fw version?')
        return

    if r.status_code != 200:
        print('[!] Request failed, wrong token?')
        return

    with open(f'{version}.bin', 'wb') as f:
        for chunk in r.iter_content(chunk_size=4096):
            if chunk:
                f.write(chunk)
    print(f'[+] saved to {version}.bin')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'usage: {sys.argv[0]} fw_version')
        exit(0)
    if not DEVICE_TOKEN or not DEVICE_ID:
        print('must set environ var AWAIR_DEVICE_TOKEN and AWAIR_DEVICE_ID')
        exit(0)
    dl_fw(sys.argv[1])
