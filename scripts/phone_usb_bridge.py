"""Forward the iPhone probe's direction readings to the receiver over the USB cable.

Run: .venv/bin/python scripts/phone_usb_bridge.py --receiver http://127.0.0.1:8766
Keep the phone plugged in and the probe listening. No Wi-Fi, hotspot or pairing code: the cable
and the phone's existing trust of this Mac are the connection. Talks to macOS's usbmuxd (the
service Xcode uses) to open TCP port 5178 on the phone, reads one JSON reading per line and posts
each to the receiver's /spatial. Reconnects on its own when the cable or app restarts.
"""
import argparse
import json
import plistlib
import socket
import struct
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

USBMUXD = '/var/run/usbmuxd'
PHONE_PORT = 5178


def usbmux_request(sock, message):
    payload = plistlib.dumps(dict(message, ClientVersionString='aware-bridge', ProgName='aware-bridge'))
    sock.sendall(struct.pack('<IIII', 16 + len(payload), 1, 8, 1) + payload)
    header = recv_exact(sock, 16)
    length = struct.unpack('<IIII', header)[0]
    return plistlib.loads(recv_exact(sock, length - 16))


def recv_exact(sock, size):
    data = b''
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError('usbmuxd closed the connection')
        data += chunk
    return data


def usb_device(udid=None):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(USBMUXD)
        devices = usbmux_request(sock, dict(MessageType='ListDevices')).get('DeviceList', [])
    for device in devices:
        props = device.get('Properties', {})
        if props.get('ConnectionType') == 'USB' and (udid is None or props.get('SerialNumber') == udid):
            return device['DeviceID'], props.get('SerialNumber')
    return None, None


def connect_phone(device_id):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(USBMUXD)
    result = usbmux_request(sock, dict(MessageType='Connect', DeviceID=device_id,
                                       PortNumber=socket.htons(PHONE_PORT)))
    if result.get('Number') != 0:
        sock.close()
        raise ConnectionError('probe not listening on the phone (open it and tap Start listening)')
    return sock


def post(receiver, line):
    request = Request(receiver + '/spatial', data=line, headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=1) as response:
        return response.status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receiver', default='http://127.0.0.1:8766')
    parser.add_argument('--udid', help='Pick one phone when several are plugged in')
    args = parser.parse_args()
    receiver = args.receiver.rstrip('/')
    sent, last_note = 0, ''

    def note(text):
        nonlocal last_note
        if text != last_note:
            print(text, flush=True)
            last_note = text

    while True:
        try:
            device_id, serial = usb_device(args.udid)
            if device_id is None:
                note('Waiting for a USB-connected iPhone…')
                time.sleep(1)
                continue
            sock = connect_phone(device_id)
            note(f'Connected to the probe over USB ({serial}). Forwarding readings to {receiver}.')
            buffer = b''
            with sock:
                sock.settimeout(5)
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        raise ConnectionError('probe closed the stream')
                    buffer += chunk
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if not line.strip() or len(line) > 512:
                            continue
                        try:
                            post(receiver, line)
                            sent += 1
                            if sent % 50 == 1:
                                reading = json.loads(line)
                                note(f'{sent} readings forwarded · latest bearing {reading.get("bearing_degrees")} '
                                     f'coherence {reading.get("coherence", 0):.2f}')
                        except (URLError, OSError):
                            note('Receiver unavailable; readings dropped until it is back.')
        except socket.timeout:
            note('No readings for 5 s (is the probe listening?). Reconnecting…')
        except (ConnectionError, OSError) as error:
            note(f'USB link: {error}. Retrying…')
            time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)


if __name__ == '__main__':
    main()
