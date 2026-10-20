#!/usr/bin/env python3
"""
CSR HID-proxy dongle CLI for macOS / Linux.

Sends the dongle vendor's two HID SET_REPORT (Feature) requests
(github.com/chancefavorsthepreparedmind/csr_clear_pairings_cmd and its -linux port) as class
control transfers to the dongle's keyboard interface (interface 0). That is what reaches the
dongle on every OS: the Windows btusbcmd.exe goes through the Windows HID driver, which addresses
interface 0; the dongle stalls requests addressed to the device as a whole.

It first tries without taking the interface from the OS HID driver. If the OS refuses, it
detaches the driver from interface 0 for the moment of the request (needs sudo), then gives it back.

Uses the libusb C library directly (no pip packages needed).

Setup:   brew install libusb            (Linux: sudo apt install libusb-1.0-0)
Usage:   python3 csr_dongle.py -clear_pairings     (if refused: sudo python3 csr_dongle.py ...)
         python3 csr_dongle.py -hid2hci        (switch to plain Bluetooth adapter mode; replug to undo)
"""
import ctypes
import ctypes.util
import os
import sys

VID, PID = 0x0A12, 0x100B  # CSR 8510 A10 dongle in HID proxy mode
COMMANDS = {"-clear_pairings": 6, "-hid2hci": 5}

REQUEST_TYPE_INTERFACE = 0x21  # host-to-device | class | recipient: interface
REQUEST_TYPE_DEVICE = 0x20     # host-to-device | class | recipient: device (last resort)
SET_REPORT = 0x09
FEATURE_REPORT = 0x0300
INTERFACE = 0
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

    vp, i = ctypes.c_void_p, ctypes.c_int
    lib.libusb_init.argtypes = [ctypes.POINTER(vp)]
    lib.libusb_init.restype = i
    lib.libusb_open_device_with_vid_pid.argtypes = [vp, ctypes.c_uint16, ctypes.c_uint16]
    lib.libusb_open_device_with_vid_pid.restype = vp
    lib.libusb_control_transfer.argtypes = [vp, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint16,
                                            ctypes.c_uint16, ctypes.c_char_p, ctypes.c_uint16,
                                            ctypes.c_uint]
    lib.libusb_control_transfer.restype = i
    lib.libusb_set_auto_detach_kernel_driver.argtypes = [vp, i]
    lib.libusb_set_auto_detach_kernel_driver.restype = i
    lib.libusb_claim_interface.argtypes = [vp, i]
    lib.libusb_claim_interface.restype = i
    lib.libusb_release_interface.argtypes = [vp, i]
    lib.libusb_release_interface.restype = i
    lib.libusb_error_name.argtypes = [i]
    lib.libusb_error_name.restype = ctypes.c_char_p
    lib.libusb_close.argtypes = [vp]
    lib.libusb_exit.argtypes = [vp]
    return lib


def err_name(lib, code):
    return lib.libusb_error_name(code).decode()


def send_commands(lib, handle, request_type, cmd):
    """Sends both variants (as the vendor tools do); returns (ok, results)."""
    variants = [(1, [0x01, cmd, 0, 0, 0, 0, 0, 0, 0]),  # composite device: report ID 1, 9 bytes
                (0, [cmd, 0, 0, 0, 0, 0, 0, 0])]        # single interface: report ID 0, 8 bytes
    results = []
    for report_id, data in variants:
        buf = bytes(data)
        r = lib.libusb_control_transfer(handle, request_type, SET_REPORT,
                                        FEATURE_REPORT | report_id, INTERFACE, buf, len(buf),
                                        TIMEOUT_MS)
        results.append(f"report {report_id}: " + ("ok" if r >= 0 else err_name(lib, r)))
    return any(r.endswith("ok") for r in results), "; ".join(results)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: {sys.argv[0]} -clear_pairings | -hid2hci")
        return 0
    cmd = COMMANDS[sys.argv[1]]

    lib = load_libusb()
    ctx = ctypes.c_void_p()
    err = lib.libusb_init(ctypes.byref(ctx))
    if err:
        print(f"libusb_init failed: {err_name(lib, err)}")
        return 1
    try:
        handle = lib.libusb_open_device_with_vid_pid(ctx, VID, PID)
        if not handle:
            print("CSR HID proxy dongle (0a12:100b) not found or not accessible.\n"
                  "Is it plugged in (and not in HCI mode)? On Linux, try sudo.")
            return 1
        try:
            # 1) Interface 0 without taking it from the OS HID driver.
            ok, res = send_commands(lib, handle, REQUEST_TYPE_INTERFACE, cmd)
            print(f"Interface 0: {res}")
            # 2) Detach the OS HID driver from interface 0 for the request (needs root).
            if not ok:
                lib.libusb_set_auto_detach_kernel_driver(handle, 1)
                claim = lib.libusb_claim_interface(handle, INTERFACE)
                if claim == 0:
                    ok, res = send_commands(lib, handle, REQUEST_TYPE_INTERFACE, cmd)
                    print(f"Interface 0 (driver detached): {res}")
                    lib.libusb_release_interface(handle, INTERFACE)  # gives it back to the OS
                else:
                    print(f"Could not take interface 0 from the OS driver: {err_name(lib, claim)}"
                          + ("" if os.geteuid() == 0 else " (try again with sudo)"))
            # 3) Last resort: addressed to the device as a whole.
            if not ok:
                ok, res = send_commands(lib, handle, REQUEST_TYPE_DEVICE, cmd)
                print(f"Device: {res}")
        finally:
            lib.libusb_close(handle)
    finally:
        lib.libusb_exit(ctx)

    if ok:
        print("Pairings cleared. Unplug and replug the dongle." if cmd == 6
              else "Switching from HID proxy to HCI mode.")
        return 0
    print("The dongle didn't accept the command"
          + ("." if os.geteuid() == 0 else "; try again with sudo."))
    return 1


if __name__ == "__main__":
    sys.exit(main())
