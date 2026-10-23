import os
import re
import select
import struct
import threading
from pathlib import Path

DEVICES = Path("/proc/bus/input/devices")
EVENT_SIZE = struct.calcsize("llHHi")
EV_KEY = 0x01
SHIFT_CODES = (42, 54)
DEFAULT_MATCH = "voyager"


class InputUnavailable(RuntimeError):
    pass


def find_devices(match: str = DEFAULT_MATCH) -> list[Path]:
    if not DEVICES.exists():
        raise InputUnavailable(f"{DEVICES} is missing")
    found: list[Path] = []
    name = ""
    for line in DEVICES.read_text(errors="replace").splitlines():
        if line.startswith("N: Name="):
            name = line.partition("=")[2].strip('"')
        elif line.startswith("H: Handlers=") and match.lower() in name.lower():
            if "kbd" not in line:
                continue
            for handler in re.findall(r"event\d+", line):
                found.append(Path("/dev/input") / handler)
    if not found:
        raise InputUnavailable(f"no input device matches {match!r}")
    return found


def open_devices(paths: list[Path]) -> list[int]:
    handles: list[int] = []
    for path in paths:
        try:
            handles.append(os.open(path, os.O_RDONLY | os.O_NONBLOCK))
        except OSError:
            continue
    if not handles:
        raise InputUnavailable(
            f"cannot read {paths[0]}; add yourself to the input group: "
            "sudo usermod -aG input $USER, then log out and back in"
        )
    return handles


class PressWatcher(threading.Thread):
    def __init__(self, on_press, on_status, match: str = DEFAULT_MATCH, retry: float = 5.0):
        super().__init__(daemon=True)
        self.on_press = on_press
        self.on_status = on_status
        self.match = match
        self.retry = retry
        self._stopped = threading.Event()
        self._shift = set()
        self._last_error: str | None = None

    def stop(self):
        self._stopped.set()

    def run(self):
        while not self._stopped.is_set():
            try:
                handles = open_devices(find_devices(self.match))
            except InputUnavailable as error:
                message = str(error)
                if message != self._last_error:
                    self._last_error = message
                    self.on_status(message)
                self._stopped.wait(self.retry)
                continue
            self._last_error = None
            try:
                self._read(handles)
            finally:
                for handle in handles:
                    os.close(handle)

    def _read(self, handles: list[int]):
        self._shift.clear()
        while not self._stopped.is_set():
            ready, _, _ = select.select(handles, [], [], 0.5)
            for handle in ready:
                try:
                    data = os.read(handle, EVENT_SIZE * 64)
                except OSError:
                    return
                for offset in range(0, len(data) - EVENT_SIZE + 1, EVENT_SIZE):
                    _, _, kind, code, value = struct.unpack(
                        "llHHi", data[offset : offset + EVENT_SIZE]
                    )
                    if kind != EV_KEY:
                        continue
                    if code in SHIFT_CODES:
                        if value == 1:
                            self._shift.add(code)
                        elif value == 0:
                            self._shift.discard(code)
                    if value == 1:
                        self.on_press(code, bool(self._shift))
