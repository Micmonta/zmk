# CSR HID-proxy dongle tool (macOS / Linux)

`csr_dongle.py` configures a CSR 8510-based Bluetooth "HID proxy" USB dongle (USB ID `0a12:100b`),
the kind used with this fork's `CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE` option.

It is a small port of the dongle vendor's
[Windows](https://github.com/chancefavorsthepreparedmind/csr_clear_pairings_cmd) /
[Linux](https://github.com/chancefavorsthepreparedmind/csr_clear_pairings_cmd-linux) command line
tools: it sends the same two HID "SET FEATURE" requests, but through the OS HID stack (`hidapi`)
instead of libusb, which on macOS cannot detach the system keyboard driver.

## Download and run

```bash
curl -LO https://raw.githubusercontent.com/Micmonta/zmk/main/extras/csr-hid-proxy/csr_dongle.py
pip3 install hidapi
python3 csr_dongle.py -clear_pairings
```

| Option | Effect |
|---|---|
| `-clear_pairings` | Forget all Bluetooth devices paired to the dongle |
| `-hid2hci` | Switch the dongle to a plain Bluetooth adapter (HCI mode); unplug/replug to go back to HID proxy mode |

On macOS, if the dongle is found but nothing happens, allow your terminal app under
**System Settings → Privacy & Security → Input Monitoring** and run it again.
