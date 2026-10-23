import argparse
import signal
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk

from .client import DEFAULT_SOCKET, KeymappClient, LayerPoller
from .geometry import slots
from .layout import DEFAULT_DB, LayoutError, list_layouts, load_layout
from .presses import DEFAULT_MATCH, PressWatcher
from .render import render_png
from .window import OverlayWindow


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="voyager-layer-overlay")
    parser.add_argument("--layout", help="Oryx layout hash, e.g. 6qlKr")
    parser.add_argument("--revision", help="Oryx revision hash; defaults to the newest cached one")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Keymapp database path")
    parser.add_argument("--socket", type=Path, default=DEFAULT_SOCKET, help="Keymapp API socket")
    parser.add_argument("--base-layer", type=int, default=0, help="layer that hides the overlay")
    parser.add_argument("--poll-ms", type=int, default=40, help="API poll interval")
    parser.add_argument("--retry-s", type=float, default=2.0, help="retry delay when the API is down")
    parser.add_argument("--show-delay-ms", type=int, default=90, help="hold time before the overlay appears")
    parser.add_argument("--unit", type=int, default=40, help="key size in pixels")
    parser.add_argument("--margin", type=int, default=48, help="distance from the screen edge")
    parser.add_argument("--position", choices=("bottom", "top", "center"), default="bottom")
    parser.add_argument("--swap-thumbs", action="store_true", help="mirror the thumb key order")
    parser.add_argument("--flash-ms", type=int, default=180, help="press flash fade time; 0 disables it")
    parser.add_argument("--input-match", default=DEFAULT_MATCH, help="input device name substring")
    parser.add_argument("--test-layer", type=int, help="show this layer until Ctrl+C")
    parser.add_argument("--render-png", help="write --test-layer to this PNG and exit")
    parser.add_argument("--list-layouts", action="store_true", help="print cached layouts and exit")
    return parser.parse_args(argv)


class Application:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        layout = load_layout(args.db, args.layout, args.revision)
        self.window = OverlayWindow(
            layout, args.unit, args.position, args.swap_thumbs, args.margin, args.flash_ms
        )
        self.pending: int | None = None

    def run(self) -> int:
        args = self.args
        if args.test_layer is not None:
            self.window.show_layer(args.test_layer)
        else:
            client = KeymappClient(args.socket)
            self.poller = LayerPoller(
                client,
                lambda layer: GLib.idle_add(self._on_layer, layer),
                lambda message: GLib.idle_add(self._on_status, f"keymapp: {message}"),
                args.poll_ms / 1000,
                args.retry_s,
            )
            self.poller.start()
        if args.flash_ms > 0:
            self.watcher = PressWatcher(
                lambda code, shift: GLib.idle_add(self._on_press, code, shift),
                lambda message: GLib.idle_add(self._on_status, f"input: {message}"),
                args.input_match,
            )
            self.watcher.start()
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._quit)
        Gtk.main()
        return 0

    def _quit(self) -> bool:
        Gtk.main_quit()
        return False

    def _on_layer(self, layer: int | None) -> bool:
        if layer is None or layer == self.args.base_layer:
            self.pending = None
            self.window.hide_overlay()
            return False
        self.pending = layer
        if self.args.show_delay_ms <= 0:
            self.window.show_layer(layer)
        else:
            GLib.timeout_add(self.args.show_delay_ms, self._on_delay_elapsed, layer)
        return False

    def _on_delay_elapsed(self, layer: int) -> bool:
        if self.pending == layer:
            self.window.show_layer(layer)
        return False

    def _on_press(self, code: int, shift: bool) -> bool:
        self.window.flash(code, shift)
        return False

    def _on_status(self, message: str) -> bool:
        print(message, file=sys.stderr)
        return False


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        if args.list_layouts:
            for item in list_layouts(args.db):
                print(f"{item['created_at']}  layout={item['layout_hash']}  revision={item['revision_id']}  {item['title']}")
            return 0
        if args.render_png:
            layout = load_layout(args.db, args.layout, args.revision)
            layer = args.test_layer if args.test_layer is not None else 1
            if not 0 <= layer < len(layout.layers):
                raise LayoutError(f"layer {layer} does not exist; the layout has {len(layout.layers)} layers")
            render_png(args.render_png, layout, layer, args.unit, slots(args.swap_thumbs))
            return 0
        return Application(args).run()
    except LayoutError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
