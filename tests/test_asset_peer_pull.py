#!/usr/bin/env python3
"""On-demand asset pull from trusted peers."""

import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.asset_processor import AssetProcessor  # noqa: E402
from core.peer_registry import PeerRegistry  # noqa: E402
from network.asset_peer_pull import fetch_asset_from_peer, pull_asset_into_local  # noqa: E402

SAMPLE_CODE = b"print('peer asset')\n"
ASSET_ID = AssetProcessor.content_hash(SAMPLE_CODE)
PEER_PUBKEY = "aa" * 32


class _PeerAssetHandler(BaseHTTPRequestHandler):
    asset_id: str = ASSET_ID
    payload: dict = {}

    def log_message(self, format, *args):
        return

    def do_GET(self):
        if "/api/asset/" not in self.path:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(self.payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _start_peer_server(payload: dict):
    _PeerAssetHandler.payload = payload
    server = HTTPServer(("127.0.0.1", 0), _PeerAssetHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def test_fetch_asset_from_peer_code():
    server, host = _start_peer_server(
        {
            "ok": True,
            "type": "code",
            "filename": "peer.py",
            "content": SAMPLE_CODE.decode("utf-8"),
        }
    )
    try:
        result = fetch_asset_from_peer(host, ASSET_ID)
        assert result.get("ok"), result
        assert result.get("raw") == SAMPLE_CODE
        print("fetch_code:", result.get("phase"))
    finally:
        server.shutdown()


def test_pull_asset_into_local():
    server, host = _start_peer_server(
        {
            "ok": True,
            "type": "code",
            "filename": "peer.py",
            "content": SAMPLE_CODE.decode("utf-8"),
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        proc = AssetProcessor(os.path.join(tmp, "assets"))
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        reg.save_peer(PEER_PUBKEY, host, status="trusted")
        try:
            report = pull_asset_into_local(
                ASSET_ID,
                proc,
                reg,
                source_peer=PEER_PUBKEY,
            )
            assert report.get("ok"), report
            assert report.get("pulled") is True
            blob, meta, status = proc.read_raw(ASSET_ID)
            assert status == 200
            assert blob is not None
            assert blob.decode("utf-8").replace("\r\n", "\n") == SAMPLE_CODE.decode("utf-8")
            assert meta.get("source_peer") == PEER_PUBKEY
            print("pull_local:", report.get("status"))
        finally:
            server.shutdown()


def test_pull_rejects_hash_mismatch():
    bad_id = "b" * 64
    server, host = _start_peer_server(
        {
            "ok": True,
            "type": "code",
            "filename": "peer.py",
            "content": SAMPLE_CODE.decode("utf-8"),
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        proc = AssetProcessor(os.path.join(tmp, "assets"))
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        reg.save_peer(PEER_PUBKEY, host, status="trusted")
        try:
            report = pull_asset_into_local(
                bad_id,
                proc,
                reg,
                source_peer=PEER_PUBKEY,
            )
            assert not report.get("ok"), report
            assert report.get("error") == "hash_mismatch"
            print("hash_mismatch:", report.get("error"))
        finally:
            server.shutdown()


def main():
    test_fetch_asset_from_peer_code()
    test_pull_asset_into_local()
    test_pull_rejects_hash_mismatch()
    print("\nASSET PEER PULL TEST PASSED")


if __name__ == "__main__":
    main()
