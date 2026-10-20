#!/usr/bin/env python3
"""
CSR HID-proxy dongle CLI for macOS / Linux (port of chancefavorsthepreparedmind/csr_clear_pairings_cmd).

Sends the same two HID SET_REPORT (Feature) requests as the original, via the OS HID stack using the
hidapi C library (no pip packages needed) instead of libusb (macOS won't let libusb detach the
keyboard driver).

Setup:   brew install hidapi          (Linux: sudo apt install libhidapi-hidraw0)
Usage:   python3 csr_dongle.py -clear_pairings
         python3 csr_dongle.py -hid2hci        (switch to plain Bluetooth adapter mode; replug to undo)
If nothing happens on macOS, allow your terminal app under
System Settings -> Privacy & Security -> Input Monitoring.
"""
import ctypes
import ctypes.util
import sys

VID, PID = 0x0A12, 0x100B  # CSR 8510 A10 dongle in HID proxy mode
COMMANDS = {"-clear_pairings": 6, "-hid2hci": 5}

LIB_CANDIDATES = [
    "/opt/homebrew/lib/libhidapi.dylib",  # Homebrew, Apple Silicon
    "/usr/local/lib/libhidapi.dylib",     # Homebrew, Intel
    "libhidapi.dylib",
    "libhidapi-hidraw.so.0",              # Linux
    "libhidapi-libusb.so.0",
]


class HidDeviceInfo(ctypes.Structure):
    pass


# Only the fields up to `next` are used; newer hidapi versions append fields after it.
HidDeviceInfo._fields_ = [
    ("path", ctypes.c_char_p),
    ("vendor_id", ctypes.c_ushort),
    ("product_id", ctypes.c_ushort),
    ("serial_number", ctypes.c_wchar_p),
    ("release_number", ctypes.c_ushort),
    ("manufacturer_string", ctypes.c_wchar_p),
    ("product_string", ctypes.c_wchar_p),
    ("usage_page", ctypes.c_ushort),
    ("usage", ctypes.c_ushort),
    ("interface_number", ctypes.c_int),
    ("next", ctypes.POINTER(HidDeviceInfo)),
]


def load_hidapi():
    found = ctypes.util.find_library("hidapi")
    for name in ([found] if found else []) + LIB_CANDIDATES:
        try:
            lib = ctypes.CDLL(name)
            break
        except OSError:
            continue
    else:
        sys.exit("hidapi library not found. Install it with: brew install hidapi")

    lib.hid_init.restype = ctypes.c_int
    lib.hid_enumerate.restype = ctypes.POINTER(HidDeviceInfo)
    lib.hid_enumerate.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
    lib.hid_free_enumeration.argtypes = [ctypes.POINTER(HidDeviceInfo)]
    lib.hid_open_path.restype = ctypes.c_void_p
    lib.hid_open_path.argtypes = [ctypes.c_char_p]
    lib.hid_send_feature_report.restype = ctypes.c_int
    lib.hid_send_feature_report.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
    lib.hid_close.argtypes = [ctypes.c_void_p]
    lib.hid_error.restype = ctypes.c_wchar_p
    lib.hid_error.argtypes = [ctypes.c_void_p]
    return lib


def send_feature(lib, dev, data):
    buf = bytes(data)
    return lib.hid_send_feature_report(dev, buf, len(buf))


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: {sys.argv[0]} -clear_pairings | -hid2hci")
        return 0
    cmd = COMMANDS[sys.argv[1]]

    lib = load_hidapi()
    lib.hid_init()
    # macOS: hidapi opens devices exclusively ("seize") by default, which fails for a keyboard-type
    # device macOS is already using. Open it shared instead (hidapi >= 0.12, macOS only).
    if hasattr(lib, "hid_darwin_set_open_exclusive"):
        lib.hid_darwin_set_open_exclusive.argtypes = [ctypes.c_int]
        lib.hid_darwin_set_open_exclusive(0)

    head = lib.hid_enumerate(VID, PID)
    devices = []
    node = head
    while node:
        info = node.contents
        devices.append((info.interface_number, info.path, info.manufacturer_string, info.product_string))
        node = info.next
    lib.hid_free_enumeration(head)

    if not devices:
        print("CSR HID proxy dongle (0a12:100b) not found. Is it plugged in and in HID proxy mode?")
        return 1
    # The original sends to interface 0; try that interface first, then any others.
    devices.sort(key=lambda d: (d[0] != 0, d[0]))

    dev = None
    for iface, path, manufacturer, product in devices:
        print(f"Found: {manufacturer} {product} (interface {iface})")
        dev = lib.hid_open_path(path)
        if dev:
            break
        if sys.platform == "darwin" and iface == 0:
            # macOS keeps the keyboard interface locked; the dongle also accepts the commands on
            # its other interface (verified: clear_pairings works via interface 1).
            print("  interface 0 is locked by macOS (normal), trying the next interface...")
        else:
            print(f"  could not open interface {iface}: {lib.hid_error(None)}")
    if not dev:
        print("Could not open the dongle. On macOS, allow your terminal app under "
              "System Settings -> Privacy & Security -> Input Monitoring (then quit and reopen the "
              "terminal), or try again with sudo.")
        return 1
    try:
        # Composite-device variant: report ID 1, 9 bytes (wValue 0x0301).
        r1 = send_feature(lib, dev, [0x01, cmd, 0, 0, 0, 0, 0, 0, 0])
        # Single-interface variant: report ID 0, 8 data bytes (wValue 0x0300).
        r0 = send_feature(lib, dev, [0x00, cmd, 0, 0, 0, 0, 0, 0, 0])
    finally:
        lib.hid_close(dev)

    print(f"Sent (results: id1={r1}, id0={r0}; -1 means that variant was rejected).")
    print("Pairings cleared." if cmd == 6 else "Switching from HID proxy to HCI mode.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
