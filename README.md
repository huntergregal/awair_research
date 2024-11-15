# Research Code Only
Some progress on poking around the Awair internal api for fun.

The `awair_python` project works on the public developer API. This is not that. 

The script is based on REing the Android app and various domain endpoints. The EA-Games Korea Graphql server is out-of-scope. lol.

WIP. Feel free to take a build off this research. 

See the code and comments for info

## Firmware Dumps
Obtained via GET requests to 
`ota.awair.is/v2/devices/awair-element/{device_id}/upgrade?type=awair-element&version=x.x.x`

with Authorization: Bearer TOKEN header where TOKEN is taken from a UART shell running the command `get_dct` on a device to dump the device's token. UART shell was obtained by finding RX/TX pads on exposed Awair Element device.

device_id and version is also filled in.
