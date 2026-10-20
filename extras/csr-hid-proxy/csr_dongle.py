#!/usr/bin/env python3
"""
CSR HID-proxy dongle CLI for macOS / Linux.

Sends exactly the same USB requests as the vendor's Windows tool, btusbcmd.exe
(github.com/chancefavorsthepreparedmind/csr_clear_pairings_cmd): two class SET_REPORT (Feature)
control transfers addressed to the *device* (bmRequestType 0x20, wIndex 0), not to one of its HID
interfaces. A device-level request doesn't need to detach or claim the keyboard interface, so it
works on macOS, where the OS keeps the dongle's keyboard interface locked.

Uses the libusb C library directly (no pip packages needed).

Setup:   brew install libusb            (Linux: sudo apt install libusb-1.0-0)
Usage:   python3 csr_dongle.py -clear_pairings
         python3 csr_dongle.py -hid2hci        (switch to plain Bluetooth adapter mode; replug to undo)
On Linux, run with sudo (or add a udev rule for 0a12:100b).
"""
import ctypes
import ctypes.util
import sys

VID, PID = 0x0A12, 0x100B  # CSR 8510 A10 dongle in HID proxy mode
COMMANDS = {"-clear_pairings": 6, "-hid2hci": 5}

REQUEST_TYPE = 0x20  # host-to-device | class | recipient: device (as btusbcmd.exe)
SET_REPORT = 0x09
FEATURE_REPORT = 0x0300
TIMEOUT_MS = 1000

LIB_CANDIDATES = [
    "/opt/homebrew/lib/libusb-1.0.dylib",  # Homebrew, Apple Silicon
    "/usr/local/lib/libusb-1.0.dylib",     # Homebrew, Intel
    "libusb-1.0.dylib",
    "libusb-1.0.so.0",                     # Linux
]


def load_libusb():
    found = ctypes.util.find_library("usb-1.0")
    for name in ([found] if found else []) + LIB_CANDIDATES:
        try:
            lib = ctypes.CDLL(name)
            break
        except OSError:
            continue
    else:
        sys.exit("libusb not found. Install it with: brew install libusb "
                 "(Linux: sudo apt install libusb-1.0-0)")

    lib.libusb_init.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.libusb_init.restype = ctypes.c_int
    lib.libusb_open_device_with_vid_pid.argtypes = [ctypes.c_void_p, ctypes.c_uint16,
                                                    ctypes.c_uint16]
    lib.libusb_open_device_with_vid_pid.restype = ctypes.c_void_p
    lib.libusb_control_transfer.argtypes = [ctypes.c_void_p, ctypes.c_uint8, ctypes.c_uint8,
                                            ctypes.c_uint16, ctypes.c_uint16, ctypes.c_char_p,
                                            ctypes.c_uint16, ctypes.c_uint]
    lib.libusb_control_transfer.restype = ctypes.c_int
    lib.libusb_error_name.argtypes = [ctypes.c_int]
    lib.libusb_error_name.restype = ctypes.c_char_p
    lib.libusb_close.argtypes = [ctypes.c_void_p]
    lib.libusb_exit.argtypes = [ctypes.c_void_p]
    return lib


def send_feature(lib, handle, report_id, data):
    buf = bytes(data)
    result = lib.libusb_control_transfer(handle, REQUEST_TYPE, SET_REPORT,
                                         FEATURE_REPORT | report_id, 0, buf, len(buf), TIMEOUT_MS)
    if result < 0:
        return lib.libusb_error_name(result).decode()
    return f"ok ({result} bytes)"


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: {sys.argv[0]} -clear_pairings | -hid2hci")
        return 0
    cmd = COMMANDS[sys.argv[1]]

    lib = load_libusb()
    ctx = ctypes.c_void_p()
    err = lib.libusb_init(ctypes.byref(ctx))
    if err:
        print(f"libusb_init failed: {lib.libusb_error_name(err).decode()}")
        return 1
    try:
        handle = lib.libusb_open_device_with_vid_pid(ctx, VID, PID)
        if not handle:
            print("CSR HID proxy dongle (0a12:100b) not found or not accessible.\n"
                  "Is it plugged in (and not in HCI mode)? On Linux, run with sudo.")
            return 1
        try:
            # Same two requests, in the same order, as btusbcmd.exe:
            # composite-device variant (report ID 1, 9 bytes), then single-interface variant
            # (report ID 0, 8 bytes). The dongle acts on whichever matches its configuration.
            r1 = send_feature(lib, handle, 1, [0x01, cmd, 0, 0, 0, 0, 0, 0, 0])
            r0 = send_feature(lib, handle, 0, [cmd, 0, 0, 0, 0, 0, 0, 0])
        finally:
            lib.libusb_close(handle)
    finally:
        lib.libusb_exit(ctx)

    print(f"Sent: report 1 -> {r1}; report 0 -> {r0}")
    if r1.startswith("ok") or r0.startswith("ok"):
        print("Pairings cleared. Unplug and replug the dongle." if cmd == 6
              else "Switching from HID proxy to HCI mode.")
        return 0
    print("The dongle rejected both requests (one failing is normal; both failing is not).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
