import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gtk

from .geometry import slots
from .layout import Layout
from .render import draw_panel, panel_size


class OverlayWindow(Gtk.Window):
    def __init__(self, layout: Layout, unit: int, position: str, swap_thumbs: bool, margin: int):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.layout = layout
        self.unit = unit
        self.position = position
        self.margin = margin
        self.slots = slots(swap_thumbs)
        self.layer_index: int | None = None

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

    def show_layer(self, index: int):
        if index == self.layer_index and self.get_visible():
            return
        self.layer_index = index
        self.area.queue_draw()
        self.show_all()
        self._place()

    def hide_overlay(self):
        self.layer_index = None
        self.hide()

    def _on_draw(self, _widget, cr):
        if self.layer_index is not None:
            draw_panel(cr, self.layout, self.layer_index, self.unit, self.slots)
        return False
