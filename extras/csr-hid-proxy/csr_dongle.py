#!/usr/bin/env python3
"""
CSR HID-proxy dongle CLI for macOS (port of chancefavorsthepreparedmind/csr_clear_pairings_cmd).

Sends the same two HID SET_REPORT (Feature) requests as the original, via macOS's HID stack
instead of libusb (macOS won't let libusb detach the keyboard driver).

Setup:   pip3 install hidapi
Usage:   python3 csr_dongle.py -clear_pairings
         python3 csr_dongle.py -hid2hci        (switch to plain Bluetooth adapter mode; power-cycle to undo)
If nothing happens, allow your terminal app under System Settings -> Privacy & Security -> Input Monitoring.
"""
import sys

import hid  # from the "hidapi" package

VID, PID = 0x0A12, 0x100B  # CSR 8510 A10 dongle in HID proxy mode
COMMANDS = {"-clear_pairings": 6, "-hid2hci": 5}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: {sys.argv[0]} -clear_pairings | -hid2hci")
        return 0
    cmd = COMMANDS[sys.argv[1]]

    devices = hid.enumerate(VID, PID)
    if not devices:
        print("CSR HID proxy dongle (0a12:100b) not found. Is it plugged in and in HID proxy mode?")
        return 1
    # The original sends to interface 0; prefer that interface if it is listed separately.
    target = next((d for d in devices if d.get("interface_number") == 0), devices[0])
    print(f"Found: {target.get('manufacturer_string')} {target.get('product_string')} "
          f"(interface {target.get('interface_number')})")

    dev = hid.device()
    dev.open_path(target["path"])
    try:
        # Composite-device variant: report ID 1, 9 bytes (wValue 0x0301).
        r1 = dev.send_feature_report([0x01, cmd, 0, 0, 0, 0, 0, 0, 0])
        # Single-interface variant: report ID 0, 8 data bytes (wValue 0x0300).
        r0 = dev.send_feature_report([0x00, cmd, 0, 0, 0, 0, 0, 0, 0])
    finally:
        dev.close()

    print(f"Sent (results: id1={r1}, id0={r0}; -1 means that variant was rejected).")
    print("Pairings cleared." if cmd == 6 else "Switching from HID proxy to HCI mode.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
