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

## Installation

### 1. Install the system packages

1. Run `sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0`.
2. Install [Keymapp](https://www.zsa.io/flash) 1.3.2 or later.

### 2. Clone and set up the project

You can clone the repository to any directory.

1. Run `git clone git@github.com:OscarStrandmark/ZSA-Voyager-overlay.git`.
2. Run `cd ZSA-Voyager-overlay`.
3. Run `./setup.sh`. It creates `.venv` and generates the gRPC stubs from `proto/keymapp.proto`.

### 3. Enable the Keymapp API

1. Open Keymapp.
2. Go to the config page.
3. Enable the API.
4. Restart Keymapp.
5. Confirm that `~/.config/.keymapp/keymapp.sock` exists.

### 4. Enable the press flash (optional)

The overlay runs without this step. It prints one line to stderr and skips the
flash.

1. Run `sudo usermod -aG input $USER`.
2. Log out and log back in.
3. Run `id -nG` and confirm that `input` is listed.

### 5. Check the overlay

1. Run `./run.sh --list-layouts`.
2. Find the hash of your layout in the `layout=` column.
3. Run `./run.sh --test-layer 1 --layout <hash>`.
4. Confirm that the overlay shows layer 1.
5. Press Ctrl+C to close it.

### 6. Install the service

The service starts the overlay at login. See [Autostart](#autostart).

1. Run `./install-service.sh --layout <hash>`.
2. Hold a layer key and confirm that the overlay appears.

## Run

Run the overlay in the foreground, without the service:

1. Run `./run.sh --layout <hash>`, for example `./run.sh --layout 6qlKr`.
2. Hold a layer key. The overlay shows that layer.
3. Press a key. That key flashes in the layer color.
4. Release the layer key. The overlay hides.

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

`install-service.sh` writes `~/.config/systemd/user/voyager-layer-overlay.service`
from the template in this repository. It fills in the path of your checkout and
the options that you give it. Then it enables and restarts the service.

To change the options, run `./install-service.sh` again with the new options,
for example `./install-service.sh --layout 6qlKr --position top`.

Caution: the service runs `run.sh` from your checkout. Run
`./install-service.sh` again after you move or rename the checkout.

Manage the service:

| Task | Command |
| --- | --- |
| Stop now | `systemctl --user stop voyager-layer-overlay` |
| Start now | `systemctl --user start voyager-layer-overlay` |
| Disable autostart | `systemctl --user disable --now voyager-layer-overlay` |
| Read the logs | `journalctl --user -u voyager-layer-overlay -f` |

Uninstall the service:

1. Run `systemctl --user disable --now voyager-layer-overlay`.
2. Run `rm ~/.config/systemd/user/voyager-layer-overlay.service`.
3. Run `systemctl --user daemon-reload`.

## Update the layout

The service pins one layout with `--layout` and follows its newest cached
revision. Without `--layout`, it shows the newest cached layout of any kind.

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
