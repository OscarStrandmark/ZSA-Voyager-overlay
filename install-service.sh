#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")" && pwd)"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
unit="$unit_dir/voyager-layer-overlay.service"

[ -x "$repo/.venv/bin/python" ] || {
  echo "Missing .venv. Run ./setup.sh first." >&2
  exit 1
}

mkdir -p "$unit_dir"
sed -e "s|@REPO@|$repo|" -e "s|@ARGS@|$*|" "$repo/voyager-layer-overlay.service" > "$unit"
systemctl --user daemon-reload
systemctl --user enable voyager-layer-overlay
systemctl --user restart voyager-layer-overlay

echo "Installed $unit"
