import time

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, GLib, Gtk

from .geometry import slots
from .keycodes import linux_code, needs_shift
from .layout import Layout
from .render import draw_panel, panel_size

FRAME_MS = 16


class OverlayWindow(Gtk.Window):
    def __init__(
        self,
        layout: Layout,
        unit: int,
        position: str,
        swap_thumbs: bool,
        margin: int,
        flash_ms: int = 180,
    ):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.layout = layout
        self.unit = unit
        self.position = position
        self.margin = margin
        self.slots = slots(swap_thumbs)
        self.layer_index: int | None = None
        self.flash_ms = flash_ms
        self._flashes: dict[int, float] = {}
        self._tick_id: int | None = None
        self._key_codes: dict[int, dict[tuple[int, bool], list[int]]] = {}

        self.set_title("Voyager layer overlay")
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
        self.stick()

        visual = self.get_screen().get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)

        self.width, self.height = panel_size(unit)
        self.set_default_size(self.width, self.height)

        self.area = Gtk.DrawingArea()
        self.area.connect("draw", self._on_draw)
        self.add(self.area)
        self.connect("realize", lambda *_: self._place())

    def _place(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        rect = monitor.get_workarea()
        x = rect.x + (rect.width - self.width) // 2
        if self.position == "top":
            y = rect.y + self.margin
        elif self.position == "center":
            y = rect.y + (rect.height - self.height) // 2
        else:
            y = rect.y + rect.height - self.height - self.margin
        self.move(x, y)

    def _codes_for(self, layer_index: int) -> dict[tuple[int, bool], list[int]]:
        cached = self._key_codes.get(layer_index)
        if cached is not None:
            return cached
        table: dict[tuple[int, bool], list[int]] = {}
        layer = self.layout.layers[layer_index]
        base = self.layout.layers[0]
        for index, key in enumerate(layer.keys):
            code = key.tap.code
            if key.transparent and index < len(base.keys):
                code = base.keys[index].tap.code
            number = linux_code(code)
            if number is not None:
                table.setdefault((number, needs_shift(code)), []).append(index)
        self._key_codes[layer_index] = table
        return table

    def flash(self, code: int, shift: bool = False) -> None:
        if self.flash_ms <= 0 or self.layer_index is None:
            return
        table = self._codes_for(self.layer_index)
        matches = table.get((code, shift)) or table.get((code, not shift))
        if not matches:
            return
        now = time.monotonic()
        for index in matches:
            self._flashes[index] = now
        if self._tick_id is None:
            self._tick_id = GLib.timeout_add(FRAME_MS, self._on_tick)
        self.area.queue_draw()

    def _on_tick(self) -> bool:
        if not self._flashes:
            self._tick_id = None
            return False
        self.area.queue_draw()
        return True

    def _intensities(self) -> dict[int, float]:
        now = time.monotonic()
        span = self.flash_ms / 1000
        out: dict[int, float] = {}
        for index, started in list(self._flashes.items()):
            remaining = 1.0 - (now - started) / span
            if remaining <= 0:
                del self._flashes[index]
                continue
            out[index] = remaining
        return out

    def show_layer(self, index: int):
        if index >= len(self.layout.layers):
            self.hide_overlay()
            return
        if index == self.layer_index and self.get_visible():
            return
        self.layer_index = index
        self._flashes.clear()
        self.area.queue_draw()
        self.show_all()
        self._place()

    def hide_overlay(self):
        self.layer_index = None
        self._flashes.clear()
        self.hide()

    def _on_draw(self, _widget, cr):
        if self.layer_index is not None:
            draw_panel(
                cr, self.layout, self.layer_index, self.unit, self.slots, flashes=self._intensities()
            )
        return False
