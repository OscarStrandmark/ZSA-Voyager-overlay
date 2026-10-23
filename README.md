# voyager-layer-overlay

An on-screen cheat sheet for the ZSA Voyager on GNOME. The overlay appears
while a non-base layer is active and hides when you release the layer key.
Keys flash on the overlay as you press them.

The firmware needs no changes. The keyboard already reports its active layer to
Keymapp, and the overlay reads it from there.

## How it works

The overlay has three inputs:

| Input | Source | Module |
| --- | --- | --- |
| Key contents (labels, layer names, colors) | Keymapp's local cache, `~/.config/.keymapp/keymapp.sqlite3` | `layout.py` |
| Active layer | Keymapp's gRPC API, `~/.config/.keymapp/keymapp.sock` | `client.py` |
| Key presses, for the flash | The keyboard's `/dev/input` event devices | `presses.py` |

The physical key positions are hardcoded for the Voyager in `geometry.py`.
Nothing is fetched from the network at runtime. The overlay shows the layout
that Keymapp last cached.

| Module | Purpose |
| --- | --- |
| `__main__.py` | Command line, startup, and the show/hide logic |
| `client.py` | Keymapp gRPC client and the layer poller thread |
| `layout.py` | Reads a layout revision from the Keymapp database and builds key labels |
| `geometry.py` | Voyager key positions, in key units |
| `keycodes.py` | Maps QMK codes to Linux keycodes, for the press flash |
| `presses.py` | Reads key presses from the input devices |
| `render.py` | Draws the panel with Cairo |
| `window.py` | The GTK overlay window and the flash animation |

## Requirements

- Keymapp 1.3.2 or later, running and connected to the keyboard
- GNOME (X11 or Wayland with XWayland)
- Python 3.12 or later
- PyGObject and GTK 3 (`sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0`)
- Membership of the `input` group, for the press flash only

## Install

1. Run `./setup.sh`. It creates `.venv` and generates the gRPC stubs from `proto/keymapp.proto`.
2. Open Keymapp.
3. Go to the config page.
4. Enable the API.
5. Restart Keymapp.
6. Confirm that `~/.config/.keymapp/keymapp.sock` exists.

Enable the press flash:

1. Run `sudo usermod -aG input $USER`.
2. Log out and log back in.
3. Run `id -nG` and confirm that `input` is listed.

The overlay runs without the `input` group. It prints one line to stderr and
skips the flash.

## Run

1. List the cached layouts with `./run.sh --list-layouts`.
2. Start the overlay with `./run.sh --layout <hash>`, for example `./run.sh --layout 6qlKr`.
3. Hold a layer key. The overlay shows that layer.
4. Press a key. That key flashes in the layer color.
5. Release the layer key. The overlay hides.

Preview one layer without Keymapp:

```
./run.sh --test-layer 1
./run.sh --test-layer 1 --render-png /tmp/layer1.png
```

`--render-png` needs no display, so you can run it over SSH or in a script.

## Options

| Option | Default | Purpose |
| --- | --- | --- |
| `--layout` | newest cached | Oryx layout hash, for example `6qlKr` |
| `--revision` | newest cached | Oryx revision hash |
| `--db` | `~/.config/.keymapp/keymapp.sqlite3` | Keymapp database |
| `--socket` | `~/.config/.keymapp/keymapp.sock` | Keymapp API socket |
| `--base-layer` | `0` | Layer that keeps the overlay hidden |
| `--show-delay-ms` | `90` | Hold time before the overlay appears |
| `--poll-ms` | `40` | API poll interval |
| `--retry-s` | `2.0` | Retry delay when the API is down |
| `--unit` | `40` | Key size in pixels |
| `--position` | `bottom` | `bottom`, `top`, or `center` |
| `--margin` | `48` | Distance from the screen edge, in pixels |
| `--swap-thumbs` | off | Mirror the thumb key order |
| `--flash-ms` | `180` | Press flash fade time; `0` disables the flash |
| `--input-match` | `voyager` | Input device name substring to read presses from |
| `--test-layer` | none | Show this layer until Ctrl+C, without Keymapp |
| `--render-png` | none | Write the test layer (default `1`) to a PNG and exit |
| `--list-layouts` | off | Print the cached layouts and exit |

## Autostart

The overlay runs as a systemd user service. It starts at login, stops at
logout, and restarts after a crash. Keymapp autostarts separately. The poller
retries until Keymapp is up, so the start order does not matter.

The service file expects the repository at `~/workspace/voyager-layer-overlay`.
If your clone is somewhere else, edit `ExecStart` before you install it.

Install the service:

1. Copy `voyager-layer-overlay.service` to `~/.config/systemd/user/`.
2. Run `systemctl --user daemon-reload`.
3. Run `systemctl --user enable --now voyager-layer-overlay`.

Manage the service:

| Task | Command |
| --- | --- |
| Stop now | `systemctl --user stop voyager-layer-overlay` |
| Start now | `systemctl --user start voyager-layer-overlay` |
| Disable autostart | `systemctl --user disable --now voyager-layer-overlay` |
| Read the logs | `journalctl --user -u voyager-layer-overlay -f` |

Change the options:

1. Edit `ExecStart` in `~/.config/systemd/user/voyager-layer-overlay.service`.
2. Run `systemctl --user daemon-reload`.
3. Run `systemctl --user restart voyager-layer-overlay`.

## Update the layout

The service pins one layout with `--layout` and follows its newest cached
revision.

1. Flash the new revision from Oryx.
2. Open Keymapp once, so it refreshes its cache.
3. Run `systemctl --user restart voyager-layer-overlay`.

## Behavior notes

### Wayland

GNOME's Mutter does not implement `wlr-layer-shell`, and a Wayland client cannot
raise itself above other windows. `run.sh` therefore sets `GDK_BACKEND=x11`. The
overlay runs as a popup X11 window under XWayland, which Mutter keeps on top and
never focuses.

### Keymapp disconnects

If Keymapp stops or the keyboard disconnects, the overlay hides. It reappears on
the next layer change after the connection comes back.

### Press flash

The keyboard reports a Linux keycode, not a physical position. The overlay maps
the active layer's QMK codes back to keycodes and flashes every key that
matches. This gives three special cases:

- A layer key that you hold emits nothing, so it never flashes.
- A layer that puts the same output on two keys flashes both of them.
- A key that emits no keycode never flashes, for example `RGB_TOG`,
  `TOGGLE_LAYER_COLOR`, and `QK_BOOT`.

Shifted symbols such as `KC_LCBR` emit Shift plus the base key. The overlay
tracks the Shift state, so `{` and `[` on one layer stay apart.

### Thumb keys

The thumb key order in Oryx exports is not documented. This project assumes that
each half lists its thumb keys left to right. If your thumb keys look mirrored,
add `--swap-thumbs`.

### Other keyboards

Only the Voyager is supported. A different keyboard needs its own key positions
in `geometry.py`, and its key count must match the Oryx export.
