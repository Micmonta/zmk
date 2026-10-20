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
If the macOS route fails, the vendor's Windows tool does the same thing.

## Using the dongle with a ZMK keyboard (`CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE`)

In the keyboard's central `.conf` (e.g. `config/toucan_left.conf`):

```
CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE=4   # BLE profile 5 (0-based index 4)
```

For that profile only, the keyboard accepts the dongle's legacy pairing and sends 8-bit mouse
reports the dongle can forward (trackpad / mouse keys). Other profiles keep LE Secure Connections
and normal 16-bit mouse reports. Don't also set `CONFIG_ZMK_BLE_EXPERIMENTAL_PAIR_JUST_WORKS`
(that allows legacy pairing on every profile). The status screen shows `HID` on that profile.

### Setup and test

1. **Flash** the keyboard's central (left) half with firmware built with the option.
   Keep a previous working `.uf2` as a rollback.
2. **Check normal use first:** profiles 1–4 reconnect to your computers, the trackpad works over
   Bluetooth, the screen shows `BLE` on profiles 1–4 and `HID` on profile 5.
3. **Reset the dongle:** `python3 csr_dongle.py -clear_pairings`. If the dongle was paired with
   another keyboard, also clear that keyboard's profile (e.g. `&bt BT_SEL 4` + `&bt BT_CLR`).
4. **Pair:** on the keyboard select profile 5 and clear it (`&bt BT_SEL 4` + `&bt BT_CLR`, or a
   `bt4clear` macro), **stay on profile 5**, and let the dongle pair. Legacy pairing is only accepted
   while that profile is selected.
5. **Test through the dongle**, in order: typing → trackpad movement → two-finger scroll →
   mouse keys / clicks → media keys → typing in a BIOS/boot screen.

### What the results mean

| Result | Meaning / next step |
|---|---|
| Typing and trackpad work | Success |
| Typing works, trackpad / mouse keys don't | The dongle may ignore mouse reports from keyboard-type devices. Next step: a USB-logging build of the central half to see whether the dongle subscribes to the mouse report |
| Pairing fails | Make sure profile 5 is selected and both sides are cleared; then check a USB log |
| Back/forward buttons or horizontal scroll don't work via the dongle | Possible if the dongle only accepts a strict boot-mouse format; harmless, everything works on the other profiles |

### Rollback

Flash the previous `.uf2`, or replace `CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE=4` with
`CONFIG_ZMK_BLE_EXPERIMENTAL_PAIR_JUST_WORKS=y` (the previous behaviour) and rebuild.
