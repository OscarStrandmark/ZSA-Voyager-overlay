import threading
from pathlib import Path

import grpc

from .proto import keymapp_pb2, keymapp_pb2_grpc

DEFAULT_SOCKET = Path.home() / ".config" / ".keymapp" / "keymapp.sock"


class KeymappUnavailable(RuntimeError):
    pass


class KeymappClient:
    def __init__(self, socket_path: Path = DEFAULT_SOCKET, timeout: float = 1.0):
        self.socket_path = socket_path
        self.timeout = timeout
        self._channel: grpc.Channel | None = None
        self._stub: keymapp_pb2_grpc.KeyboardServiceStub | None = None

    def close(self):
        if self._channel is not None:
            self._channel.close()
        self._channel = None
        self._stub = None

    def _ensure_stub(self) -> keymapp_pb2_grpc.KeyboardServiceStub:
        if self._stub is not None:
            return self._stub
        if not self.socket_path.exists():
            raise KeymappUnavailable(
                f"{self.socket_path} is missing; enable the API in Keymapp's config page"
            )
        self._channel = grpc.insecure_channel(f"unix://{self.socket_path}")
        self._stub = keymapp_pb2_grpc.KeyboardServiceStub(self._channel)
        return self._stub

    def current_layer(self) -> int:
        stub = self._ensure_stub()
        try:
            reply = stub.GetStatus(keymapp_pb2.GetStatusRequest(), timeout=self.timeout)
        except grpc.RpcError as error:
            self.close()
            raise KeymappUnavailable(str(error.code())) from error
        keyboard = reply.connected_keyboard
        if not keyboard.friendly_name:
            self._connect_any()
            raise KeymappUnavailable("no keyboard connected in Keymapp")
        return keyboard.current_layer

    def _connect_any(self):
        try:
            self._ensure_stub().ConnectAnyKeyboard(
                keymapp_pb2.ConnectAnyKeyboardRequest(), timeout=self.timeout
            )
        except grpc.RpcError:
            self.close()


class LayerPoller(threading.Thread):
    def __init__(self, client: KeymappClient, on_layer, on_status, interval: float, retry: float):
        super().__init__(daemon=True)
        self.client = client
        self.on_layer = on_layer
        self.on_status = on_status
        self.interval = interval
        self.retry = retry
        self._stopped = threading.Event()
        self._last_layer: int | None = None
        self._last_error: str | None = None

    def stop(self):
        self._stopped.set()

    def run(self):
        while not self._stopped.is_set():
            try:
                layer = self.client.current_layer()
            except KeymappUnavailable as error:
                message = str(error)
                if message != self._last_error:
                    self._last_error = message
                    self.on_status(message)
                if self._last_layer is not None:
                    self._last_layer = None
                    self.on_layer(None)
                self._stopped.wait(self.retry)
                continue
            if self._last_error is not None:
                self._last_error = None
                self.on_status("connected")
            if layer != self._last_layer:
                self._last_layer = layer
                self.on_layer(layer)
            self._stopped.wait(self.interval)
