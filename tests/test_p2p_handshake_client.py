#!/usr/bin/env python3
"""Outbound P2P handshake client integration test."""

import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from api.p2p_handler import HandshakeHandler  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402
from network.p2p_handshake_client import perform_outbound_handshake  # noqa: E402


class _RemoteHandler(BaseHTTPRequestHandler):
    remote: HandshakeHandler = None  # type: ignore

    def log_message(self, format, *args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        data = json.loads(raw.decode("utf-8") if raw else "{}")
        result = self.remote.handle_request(data)
        if result.get("status") == "trusted_peer":
            result = dict(result)
            result["ok"] = True
        body = json.dumps(result).encode("utf-8")
        code = 200 if result.get("ok", True) else 400
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        im_local = IdentityManager(os.path.join(tmp, "local.key"))
        im_remote = IdentityManager(os.path.join(tmp, "remote.key"))
        local = HandshakeHandler(im_local)
        remote = HandshakeHandler(im_remote)
        _RemoteHandler.remote = remote

        server = HTTPServer(("127.0.0.1", 0), _RemoteHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            result = perform_outbound_handshake(
                f"http://127.0.0.1:{port}",
                im_remote.public_key_hex(),
                local,
                local_host="http://127.0.0.1:7864",
            )
            assert result.get("ok"), result
            assert result.get("remote_trusts_us") is True
            print("handshake_client:", result.get("phase"), result.get("status"))
            print("\nP2P HANDSHAKE CLIENT TEST PASSED")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
