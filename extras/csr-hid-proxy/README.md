# CSR HID-proxy dongle (USB `0a12:100b`)

BLE-to-USB dongle used with `CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE`. Typing works through it;
mouse and media keys don't.

## Clear the dongle's pairing

Then unplug and replug the dongle.

### Windows

```powershell
curl.exe -LO https://raw.githubusercontent.com/Micmonta/zmk/main/extras/csr-hid-proxy/btusbcmd.exe
.\btusbcmd.exe -clear_pairings
```

### macOS

```bash
brew install libusb
curl -LO https://raw.githubusercontent.com/Micmonta/zmk/main/extras/csr-hid-proxy/csr_dongle.py
python3 csr_dongle.py -clear_pairings
```

Works without sudo. Success = a line with `ok` (the other variant failing is normal).

### Linux (untested)

```bash
sudo apt install libusb-1.0-0
curl -LO https://raw.githubusercontent.com/Micmonta/zmk/main/extras/csr-hid-proxy/csr_dongle.py
sudo python3 csr_dongle.py -clear_pairings
```

`-hid2hci` instead of `-clear_pairings` switches the dongle to a plain Bluetooth adapter until
replugged.

## Keyboard config

`config/toucan_left.conf`:

```
CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE=4   # profile 5
```

Allows the dongle's legacy pairing on profile 5 only. Screen shows `HID` on that profile.

## Pairing

1. Clear the dongle (above) and replug it.
2. On the Toucan: profile 5, clear it, stay on it.
3. Wait for it to pair; test typing.

If the screen shows `HID` but nothing types: repeat 1–2 (both sides must be cleared).

## Why no mouse

- The dongle remembers one device and treats it as either a keyboard or a mouse, decided at
  pairing by the Boot Keyboard / Boot Mouse characteristics. It never reads the report map.
- No mouse format got through (report IDs 2/3, boot mouse 3/4 bytes, keyboard or mouse mode).
- No media-key interface on its USB side.
- Same firmware family: [Laird BT800 HID proxy app note](http://cdn.lairdtech.com/home/brandworld/files/Application%20Note%20-%20BT800%20Series%20HID%20Proxy.pdf).

## Clear command details

Both tools send HID SET_REPORT (Feature) to interface 0: report 1 `01 06 00…` (9 bytes) and
report 0 `06 00…` (8 bytes); `05` instead of `06` = hid2hci. The dongle rejects it on interface 1
or addressed to the whole device. Vendor sources:
[Windows](https://github.com/chancefavorsthepreparedmind/csr_clear_pairings_cmd),
[Linux](https://github.com/chancefavorsthepreparedmind/csr_clear_pairings_cmd-linux).
