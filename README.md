# voyager-layer-overlay

An on-screen cheat sheet for the ZSA Voyager. The overlay appears while a
non-base layer is active and disappears when you release the layer key.

The layer state comes from Keymapp's gRPC API, so the firmware needs no changes:
the keyboard already reports its active layer to Keymapp over HID.

Layouts are read from Keymapp's local cache
(`~/.config/.keymapp/keymapp.sqlite3`), so the overlay always shows the layout
you last opened in Keymapp. Nothing is fetched from the network at runtime.

## Requirements

- Keymapp 1.3.2 or later, running and connected to the keyboard
- PyGObject and GTK 3 (`sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0`)
- Python 3.12 or later

## Install

1. Run `./setup.sh`. It creates `.venv` and generates the gRPC stubs.
2. Open Keymapp.
3. Go to the config page.
4. Enable the API.
5. Restart Keymapp.
6. Confirm that `~/.config/.keymapp/keymapp.sock` exists.

## Run

```
./run.sh --layout 6qlKr
```

Hold a layer key. The overlay shows that layer. Release the key. The overlay hides.

List the cached layouts:

```
./run.sh --list-layouts
```

Preview one layer without Keymapp:

```
./run.sh --test-layer 1
./run.sh --test-layer 1 --render-png /tmp/layer1.png
```

## Options

| Option | Default | Purpose |
| --- | --- | --- |
| `--layout` | newest cached | Oryx layout hash, for example `6qlKr` |
| `--revision` | newest cached | Oryx revision hash |
| `--base-layer` | `0` | Layer that keeps the overlay hidden |
| `--show-delay-ms` | `90` | Hold time before the overlay appears |
| `--poll-ms` | `40` | API poll interval |
| `--unit` | `54` | Key size in pixels |
| `--position` | `bottom` | `bottom`, `top`, or `center` |
| `--margin` | `48` | Distance from the screen edge |
| `--swap-thumbs` | off | Mirror the thumb key order |

## Autostart

The overlay runs as a systemd user service. It starts at login and stops at
logout, and it restarts itself after a crash. Keymapp autostarts separately, and
the poller retries every 2 seconds, so the start order does not matter.

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

## Updating the layout

The service pins one layout with `--layout`. It follows the newest cached
revision of that layout.

1. Flash the new revision from Oryx.
2. Open Keymapp once, so it refreshes its cache.
3. Run `systemctl --user restart voyager-layer-overlay`.

## Notes on Wayland

GNOME's Mutter does not implement `wlr-layer-shell`, and a Wayland client cannot
raise itself above other windows. `run.sh` therefore sets `GDK_BACKEND=x11` and
the overlay runs as an override-redirect X11 window under XWayland, which Mutter
keeps on top and never focuses.

The thumb key order in Oryx exports is not documented. This project assumes each
half lists its thumb keys left to right. If your thumb keys look mirrored, add
`--swap-thumbs`.
