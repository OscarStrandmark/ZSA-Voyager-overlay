import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

ALIASES = {
    "KC_BSPC": "KC_BSPACE",
    "KC_CAPS": "KC_CAPSLOCK",
    "KC_ENT": "KC_ENTER",
    "KC_SPC": "KC_SPACE",
    "KC_ESC": "KC_ESCAPE",
    "KC_DEL": "KC_DELETE",
    "KC_INS": "KC_INSERT",
    "KC_PSCR": "KC_PSCREEN",
    "KC_SCRL": "KC_SCROLLLOCK",
    "KC_LEFT_CTRL": "KC_LCTRL",
    "KC_RIGHT_CTRL": "KC_RCTRL",
    "KC_LEFT_SHIFT": "KC_LSHIFT",
    "KC_RIGHT_SHIFT": "KC_RSHIFT",
    "KC_LEFT_ALT": "KC_LALT",
    "KC_RIGHT_ALT": "KC_RALT",
    "KC_LEFT_GUI": "KC_LGUI",
    "KC_RIGHT_GUI": "KC_RGUI",
    "KC_PGUP": "KC_PAGE_UP",
    "KC_PGDN": "KC_PAGE_DOWN",
}

PRETTY = {
    "KC_LCTRL": "Ctrl",
    "KC_RCTRL": "Ctrl",
    "KC_LSHIFT": "Shift",
    "KC_RSHIFT": "Shift",
    "KC_LALT": "Alt",
    "KC_RALT": "AltGr",
    "KC_LGUI": "Super",
    "KC_RGUI": "Super",
    "KC_PAGE_UP": "PgUp",
    "KC_PAGE_DOWN": "PgDn",
    "KC_UP": "\u2191",
    "KC_DOWN": "\u2193",
    "KC_LEFT": "\u2190",
    "KC_RIGHT": "\u2192",
    "KC_BSPACE": "Bksp",
    "QK_BOOT": "Boot",
    "RGB_MODE_FORWARD": "RGB mode",
    "TOGGLE_LAYER_COLOR": "Layer colors",
    "KC_TRANSPARENT": "",
    "KC_BSLS": "\\",
    "KC_SCLN": ";",
    "KC_LBRC": "[",
    "KC_RBRC": "]",
    "KC_GRV": "`",
    "KC_COMM": ",",
    "KC_QUOT": "'",
    "MO": "MO",
}


def _prettify(code: str) -> str:
    body = re.sub(r"^(KC|QK|RGB|KC_MEDIA|KC_AUDIO)_", "", code)
    body = body.replace("_", " ").strip().lower()
    return body[:1].upper() + body[1:] if body else code


def _label_for(code: str, labels: dict[str, str]) -> str:
    if not code:
        return ""
    for candidate in (code, ALIASES.get(code, "")):
        if not candidate:
            continue
        if candidate in PRETTY:
            return PRETTY[candidate]
        found = labels.get(candidate)
        if found:
            return found
    if code in PRETTY:
        return PRETTY[code]
    return _prettify(code)


DEFAULT_DB = Path.home() / ".config" / ".keymapp" / "keymapp.sqlite3"


@dataclass(frozen=True)
class Cap:
    label: str = ""
    layer: int | None = None


@dataclass(frozen=True)
class Key:
    tap: Cap = field(default_factory=Cap)
    hold: Cap = field(default_factory=Cap)
    transparent: bool = False


@dataclass(frozen=True)
class Layer:
    index: int
    title: str
    color: str | None
    keys: list[Key]


@dataclass(frozen=True)
class Layout:
    title: str
    layout_hash: str
    revision_hash: str
    created_at: str
    layers: list[Layer]


class LayoutError(RuntimeError):
    pass


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise LayoutError(f"Keymapp database not found: {db_path}")
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def _labels(conn: sqlite3.Connection) -> dict[str, str]:
    row = conn.execute("select data from metadata").fetchone()
    if row is None:
        raise LayoutError("Keymapp database has no metadata; open Keymapp once while online")
    out: dict[str, str] = {}
    for entry in json.loads(row[0])["keys"]:
        if entry.get("deleted"):
            continue
        code = entry.get("code")
        label = entry.get("label")
        if code and label and code not in out:
            out[code] = label
    return out


def _revisions(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for revision_id, blob in conn.execute("select revisionId, data from revision"):
        layout = json.loads(blob)["layout"]
        revision = layout["revision"]
        out.append(
            {
                "revision_id": revision_id,
                "layout_hash": layout.get("hashId", ""),
                "title": layout.get("title", ""),
                "created_at": revision.get("createdAt", ""),
                "layout": layout,
            }
        )
    out.sort(key=lambda item: item["created_at"], reverse=True)
    return out


def list_layouts(db_path: Path = DEFAULT_DB) -> list[dict]:
    with _connect(db_path) as conn:
        return [
            {k: v for k, v in item.items() if k != "layout"} for item in _revisions(conn)
        ]


def _cap(slot: dict | None, labels: dict[str, str]) -> Cap:
    if not slot:
        return Cap()
    code = slot.get("code") or ""
    layer = slot.get("layer")
    label = _label_for(code, labels)
    if layer is not None:
        label = f"{label or code}{layer}"
    modifiers = slot.get("modifiers") or {}
    active = [name for name, on in modifiers.items() if on is True]
    if active and label:
        label = "+".join(short.capitalize()[:4] for short in active) + " " + label
    return Cap(label=label, layer=layer)


def load_layout(
    db_path: Path = DEFAULT_DB,
    layout_hash: str | None = None,
    revision_id: str | None = None,
) -> Layout:
    with _connect(db_path) as conn:
        labels = _labels(conn)
        revisions = _revisions(conn)
        if not revisions:
            raise LayoutError("Keymapp database holds no layouts; open Keymapp once while online")
        chosen = None
        for item in revisions:
            if revision_id and item["revision_id"] != revision_id:
                continue
            if layout_hash and item["layout_hash"] != layout_hash:
                continue
            chosen = item
            break
        if chosen is None:
            raise LayoutError(
                f"No cached layout matches layout={layout_hash} revision={revision_id}"
            )

    layers = []
    for index, raw in enumerate(chosen["layout"]["revision"]["layers"]):
        keys = []
        for raw_key in raw["keys"]:
            tap = _cap(raw_key.get("tap"), labels)
            hold = _cap(raw_key.get("hold"), labels)
            custom = raw_key.get("customLabel")
            if custom:
                tap = Cap(label=custom, layer=tap.layer)
            transparent = (raw_key.get("tap") or {}).get("code") == "KC_TRANSPARENT"
            keys.append(Key(tap=tap, hold=hold, transparent=transparent))
        layers.append(
            Layer(
                index=index,
                title=raw.get("title") or f"Layer {index}",
                color=raw.get("color"),
                keys=keys,
            )
        )

    return Layout(
        title=chosen["title"],
        layout_hash=chosen["layout_hash"],
        revision_hash=chosen["revision_id"],
        created_at=chosen["created_at"],
        layers=layers,
    )
