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

## macOS / Linux: `csr_dongle.py` (experimental, may not work)

> [!WARNING]
> On macOS this may not work properly. macOS locks the dongle's keyboard interface (0), so the
> script can only send the commands to interface 1. In testing that made the dongle forget its
> pairings, but keyboards re-paired afterwards connected without sending any keys until the dongle
> was cleared again with `btusbcmd.exe` on Windows. Prefer the Windows tool.

It uses the `hidapi` C library directly (no pip packages needed):

```bash
brew install hidapi        # Linux: sudo apt install libhidapi-hidraw0
curl -LO https://raw.githubusercontent.com/Micmonta/zmk/main/extras/csr-hid-proxy/csr_dongle.py
python3 csr_dongle.py -clear_pairings
```

On macOS, also allow your terminal app under
**System Settings → Privacy & Security → Input Monitoring**.

## Using the dongle with a ZMK keyboard (`CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE`)

In the keyboard's central `.conf` (e.g. `config/toucan_left.conf`):

```
CONFIG_ZMK_BLE_DONGLE_COMPAT_PROFILE=4   # BLE profile 5 (0-based index 4)
```

For that profile only, the keyboard accepts the dongle's legacy pairing and sends 8-bit mouse
reports. Other profiles keep LE Secure Connections and normal 16-bit mouse reports. Don't also set
`CONFIG_ZMK_BLE_EXPERIMENTAL_PAIR_JUST_WORKS` (that allows legacy pairing on every profile).
The status screen shows `HID` on that profile.

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
