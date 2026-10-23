import math

import cairo

from .geometry import TOTAL_HEIGHT, TOTAL_WIDTH, Slot
from .layout import Key, Layout

PADDING = 0.34
HEADER = 0.62
ACCENTS = ("#6ea8fe", "#f7a072", "#8bd450", "#e879f9", "#facc15", "#5eead4")
FONT = "DejaVu Sans"


def panel_size(unit: int) -> tuple[int, int]:
    width = int((TOTAL_WIDTH + PADDING * 2) * unit)
    height = int((TOTAL_HEIGHT + HEADER + PADDING * 2) * unit)
    return width, height


def hex_to_rgb(value: str | None, fallback: tuple[float, float, float]) -> tuple[float, float, float]:
    if not value:
        return fallback
    text = value.strip().lstrip("#")
    if len(text) != 6:
        return fallback
    try:
        return tuple(int(text[i : i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return fallback


def _rounded(cr, x, y, width, height, radius):
    cr.new_sub_path()
    cr.arc(x + width - radius, y + radius, radius, -math.pi / 2, 0)
    cr.arc(x + width - radius, y + height - radius, radius, 0, math.pi / 2)
    cr.arc(x + radius, y + height - radius, radius, math.pi / 2, math.pi)
    cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
    cr.close_path()


def _fit(cr, text: str, max_width: float, size: float, minimum: float = 6.0) -> float:
    while size > minimum:
        cr.set_font_size(size)
        if cr.text_extents(text)[2] <= max_width:
            break
        size -= 0.5
    cr.set_font_size(size)
    return size


def _wrap(text: str) -> list[str]:
    words = text.split()
    if len(words) < 2:
        return [text]
    best = min(
        range(1, len(words)),
        key=lambda cut: abs(len(" ".join(words[:cut])) - len(" ".join(words[cut:]))),
    )
    return [" ".join(words[:best]), " ".join(words[best:])]


def _draw_label(cr, text: str, x: float, width: float, baseline: float, size: float, unit: int) -> None:
    fitted = _fit(cr, text, width * 0.86, size, minimum=size * 0.62)
    if cr.text_extents(text)[2] <= width * 0.86:
        _centered(cr, text, x, width, baseline)
        return
    lines = _wrap(text)
    if len(lines) == 1:
        _fit(cr, text, width * 0.86, size)
        _centered(cr, text, x, width, baseline)
        return
    line_size = min(fitted, unit * 0.19)
    for index, line in enumerate(lines):
        _fit(cr, line, width * 0.9, line_size)
        _centered(cr, line, x, width, baseline + (index - 0.5) * line_size * 1.15)


def _centered(cr, text: str, x: float, width: float, y: float) -> None:
    extents = cr.text_extents(text)
    cr.move_to(x + (width - extents[2]) / 2 - extents[0], y)
    cr.show_text(text)


def _draw_key(
    cr, key: Key, base_key: Key, x: float, y: float, size: float, unit: int, accent, flash: float = 0.0
) -> None:
    transparent = key.transparent or not key.tap.label
    _rounded(cr, x, y, size, size, unit * 0.13)
    if transparent:
        cr.set_source_rgba(1, 1, 1, 0.03)
    elif key.tap.layer is not None or key.hold.layer is not None:
        cr.set_source_rgba(*accent, 0.22)
    else:
        cr.set_source_rgba(1, 1, 1, 0.08)
    cr.fill_preserve()
    if flash > 0:
        cr.set_source_rgba(*accent, 0.70 * flash)
        cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, 0.10 + 0.75 * flash)
    cr.set_line_width(1.0 + flash)
    cr.stroke()

    label = key.tap.label
    if transparent:
        label = base_key.tap.label
        cr.set_source_rgba(1, 1, 1, 0.22)
    else:
        cr.set_source_rgba(0.94, 0.95, 0.97, 1.0)
    if label:
        baseline = y + size * (0.52 if key.hold.label and not transparent else 0.62)
        _draw_label(cr, label, x, size, baseline, unit * 0.26, unit)

    if key.hold.label and not transparent:
        cr.set_source_rgba(*accent, 0.85)
        _fit(cr, key.hold.label, size * 0.84, unit * 0.18)
        _centered(cr, key.hold.label, x, size, y + size * 0.84)


def draw_panel(
    cr,
    layout: Layout,
    layer_index: int,
    unit: int,
    slots: list[Slot],
    clear: bool = True,
    flashes: dict[int, float] | None = None,
) -> None:
    if layer_index >= len(layout.layers):
        return
    width, height = panel_size(unit)
    layer = layout.layers[layer_index]
    base = layout.layers[0]
    accent = hex_to_rgb(layer.color, hex_to_rgb(ACCENTS[layer_index % len(ACCENTS)], (0.43, 0.66, 1.0)))

    if clear:
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

    _rounded(cr, 0, 0, width, height, unit * 0.28)
    cr.set_source_rgba(0.07, 0.08, 0.10, 0.67)
    cr.fill_preserve()
    cr.set_source_rgba(*accent, 0.45)
    cr.set_line_width(1.5)
    cr.stroke()

    cr.select_font_face(FONT)
    cr.set_font_size(unit * 0.27)
    cr.set_source_rgba(*accent, 1.0)
    cr.move_to(PADDING * unit, PADDING * unit + unit * 0.3)
    cr.show_text(f"Layer {layer.index} · {layer.title}")

    cr.set_font_size(unit * 0.2)
    cr.set_source_rgba(1, 1, 1, 0.35)
    title = f"{layout.title} ({layout.revision_hash})"
    cr.move_to(width - PADDING * unit - cr.text_extents(title)[2], PADDING * unit + unit * 0.28)
    cr.show_text(title)

    origin_y = (PADDING + HEADER) * unit
    for slot in slots:
        if slot.index >= len(layer.keys):
            continue
        _draw_key(
            cr,
            layer.keys[slot.index],
            base.keys[slot.index],
            PADDING * unit + slot.x * unit,
            origin_y + slot.y * unit,
            unit * 0.92,
            unit,
            accent,
            (flashes or {}).get(slot.index, 0.0),
        )


def render_png(path: str, layout: Layout, layer_index: int, unit: int, slots: list[Slot]) -> None:
    width, height = panel_size(unit)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)
    draw_panel(cr, layout, layer_index, unit, slots)
    surface.write_to_png(path)
