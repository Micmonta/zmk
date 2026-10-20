# CSR HID-proxy dongle tools

Tools to configure a CSR 8510-based Bluetooth "HID proxy" USB dongle (USB ID `0a12:100b`), the kind
used with this fork's `CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE` option. Both send the dongle vendor's
two HID "SET FEATURE" commands (see the vendor's
[Windows](https://github.com/chancefavorsthepreparedmind/csr_clear_pairings_cmd) and
[Linux](https://github.com/chancefavorsthepreparedmind/csr_clear_pairings_cmd-linux) sources).

| Option | Effect |
|---|---|
| `-clear_pairings` | Forget all Bluetooth devices paired to the dongle |
| `-hid2hci` | Switch the dongle to a plain Bluetooth adapter (HCI mode); unplug/replug to go back to HID proxy mode |
| `-version` | Show the tool version (Windows tool) |

## Windows (recommended): `btusbcmd.exe`

The vendor's own tool. In **Windows Terminal** (PowerShell or Command Prompt), with the dongle
plugged in:

```powershell
curl.exe -LO https://raw.githubusercontent.com/Micmonta/zmk/main/extras/csr-hid-proxy/btusbcmd.exe
.\btusbcmd.exe -clear_pairings
```

## macOS / Linux: `csr_dongle.py`

Sends exactly the same USB requests as `btusbcmd.exe`: two control transfers addressed to the
dongle as a whole (not to its keyboard interface), so nothing has to be detached or claimed and
macOS locking the keyboard interface doesn't matter. It uses the `libusb` C library directly (no
pip packages needed):

```bash
brew install libusb        # Linux: sudo apt install libusb-1.0-0
curl -LO https://raw.githubusercontent.com/Micmonta/zmk/main/extras/csr-hid-proxy/csr_dongle.py
python3 csr_dongle.py -clear_pairings      # Linux: sudo python3 csr_dongle.py -clear_pairings
```

Then unplug and replug the dongle. One of the two requests being rejected is normal (the dongle
only accepts the variant that matches its configuration).

> [!NOTE]
> The macOS version is new and not yet confirmed on real hardware. An earlier hidapi-based version
> sent the commands to the dongle's mouse interface instead, which left the dongle in a bad state;
> if this one misbehaves, fall back to `btusbcmd.exe` on Windows.

## Using the dongle with a ZMK keyboard (`CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE`)

In the keyboard's central `.conf` (e.g. `config/toucan_left.conf`):

```
CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE=4   # BLE profile 5 (0-based index 4)
```

For that profile only, the keyboard accepts the dongle's legacy pairing and sends the mouse as
report ID 2 in the dongle's own USB mouse layout (3 buttons, 16-bit X/Y, 8-bit wheel), with media
keys moved to report ID 3. The dongle forwards report ID 1 (keyboard) and, by the usual
combo-keyboard convention, report ID 2 (mouse). Other profiles are unchanged. Don't also set
`CONFIG_ZMK_BLE_EXPERIMENTAL_PAIR_JUST_WORKS` (that allows legacy pairing on every profile).
The status screen shows `HID` on that profile.

The dongle has no media-key (consumer) interface, so volume / media keys can't work through it.
Buttons 4/5 and horizontal scroll aren't supported by its mouse either.

> [!NOTE]
> Current status: typing works through the dongle; mouse movement (trackpad / mouse keys) does not
> yet. Still being investigated.

### Pairing

**Always clear both sides.** ZMK refuses a new pairing on a profile that still remembers the
dongle, so after clearing the dongle the keyboard's profile must be cleared too (otherwise the
dongle connects, the screen shows `HID`, but no keys are sent).

1. Clear the dongle: `.\btusbcmd.exe -clear_pairings` (Windows).
2. Unplug and replug the dongle.
3. On the keyboard: select profile 5 and clear it (`&bt BT_SEL 4` + `&bt BT_CLR`, or a `bt4clear`
   macro), and **stay on profile 5**. Legacy pairing is only accepted while that profile is selected.
4. Let the dongle pair, then test typing, trackpad / mouse keys, and a BIOS/boot screen.

To move the dongle to another keyboard, do the same steps with that keyboard (and clear profile 5 on
the old one if you later want it back on the dongle).

### Troubleshooting

| Result | Meaning / next step |
|---|---|
| Screen shows `HID` but nothing types | The pairing didn't complete: clear both sides again (steps 1–3), using the Windows tool |
| Typing works, trackpad / mouse keys don't | Known current limitation, under investigation (a USB-logging build of the central half shows whether the dongle subscribes to the mouse report) |
| Right-half battery icon disappears on profile 5 | Under investigation (likely the left/right link briefly dropping when the dongle connects) |

### Rollback

Flash the previous `.uf2`, or replace `CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE=4` with
`CONFIG_ZMK_BLE_EXPERIMENTAL_PAIR_JUST_WORKS=y` (the previous behaviour) and rebuild.
