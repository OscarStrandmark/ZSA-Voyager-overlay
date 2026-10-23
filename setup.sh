#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -c "import gi" 2>/dev/null || {
  echo "Missing PyGObject. Run: sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0" >&2
  exit 1
}

python3 -m venv --system-site-packages .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet grpcio grpcio-tools
.venv/bin/python -m grpc_tools.protoc \
  --proto_path=proto \
  --python_out=overlay/proto \
  --grpc_python_out=overlay/proto \
  proto/keymapp.proto
sed -i 's/^import keymapp_pb2 as/from . import keymapp_pb2 as/' overlay/proto/keymapp_pb2_grpc.py

echo "Setup complete. Start the overlay with ./run.sh"
