#!/usr/bin/env python3
"""
Starlink gRPC-Web collector service.
Exposes the same HTTP JSON endpoints as the simulator so the ground station
can connect by port only.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import threading
import time
from pathlib import Path
import sys
from flask import Flask, jsonify

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "starlink-grpc-tools"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if TOOLS_DIR.exists() and str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

try:
    import starlink_grpc
except ImportError as exc:
    raise SystemExit(
        f"starlink_grpc import failed: {exc}. "
        "Ensure starlink-grpc-tools is present and grpcio is installed."
    ) from exc


app = Flask(__name__)


class CollectorState:
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


@dataclass
class CollectorStatus:
    state: str
    last_update: str
    last_error: str


class GrpcWebCollector:
    def __init__(self, grpc_host: str, grpc_port: int, interval: float):
        self.grpc_host = grpc_host
        self.grpc_port = grpc_port
        self.context = starlink_grpc.ChannelContext(target=f"{grpc_host}:{grpc_port}")
        self.interval = interval
        self.state = CollectorState.IDLE
        self.last_error = ""
        self.last_update = ""
        self.current_data = {}
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self.state == CollectorState.RUNNING:
            return
        self._stop_event.clear()
        self.state = CollectorState.RUNNING
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self.state = CollectorState.IDLE

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                data = self._fetch_status()
                self.current_data = data or {}
                self.last_error = ""
                self.last_update = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                if self.state != CollectorState.RUNNING:
                    self.state = CollectorState.RUNNING
            except Exception as exc:
                self.last_error = str(exc)
                self.state = CollectorState.ERROR
            time.sleep(self.interval)

    def _fetch_status(self):
        status, _, _ = starlink_grpc.status_data(context=self.context)
        location = starlink_grpc.location_data(context=self.context)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return {
            "timestamp": now,
            "terminal_id": status.get("id"),
            "state": status.get("state"),
            "uptime": status.get("uptime"),
            "downlink_throughput_bps": status.get("downlink_throughput_bps"),
            "uplink_throughput_bps": status.get("uplink_throughput_bps"),
            "ping_drop_rate": status.get("pop_ping_drop_rate"),
            "ping_latency_ms": status.get("pop_ping_latency_ms"),
            "snr": status.get("snr"),
            "seconds_to_first_nonempty_slot": status.get("seconds_to_first_nonempty_slot"),
            "azimuth": status.get("direction_azimuth"),
            "elevation": status.get("direction_elevation"),
            "pop_ping_drop_rate": status.get("pop_ping_drop_rate"),
            "pop_ping_latency_ms": status.get("pop_ping_latency_ms"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "altitude": location.get("altitude"),
            "gps_sats": status.get("gps_sats"),
            "hardware_version": status.get("hardware_version"),
            "software_version": status.get("software_version"),
        }

    def status(self) -> CollectorStatus:
        return CollectorStatus(
            state=self.state,
            last_update=self.last_update,
            last_error=self.last_error,
        )


collector = None


@app.route("/api/status")
def api_status():
    if not collector:
        return jsonify({"state": "UNKNOWN", "error": "collector not initialized"}), 503
    return jsonify(asdict(collector.status()))


@app.route("/api/start", methods=["POST"])
def api_start():
    if not collector:
        return jsonify({"success": False, "error": "collector not initialized"}), 503
    collector.start()
    return jsonify({"success": True, "state": collector.state})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    if not collector:
        return jsonify({"success": False, "error": "collector not initialized"}), 503
    collector.stop()
    return jsonify({"success": True, "state": collector.state})


@app.route("/api/current_data")
def api_current_data():
    if not collector:
        return jsonify({})
    return jsonify(collector.current_data or {})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Starlink gRPC-Web collector")
    parser.add_argument("--grpc-host", default="192.168.100.1", help="Starlink gRPC host")
    parser.add_argument("--grpc-port", type=int, default=9200, help="Starlink gRPC port")
    parser.add_argument("--control-port", type=int, default=9201, help="Collector HTTP port")
    parser.add_argument("--interval", type=float, default=3.0, help="Collection interval in seconds")
    args = parser.parse_args()

    global collector
    collector = GrpcWebCollector(
        grpc_host=args.grpc_host,
        grpc_port=args.grpc_port,
        interval=args.interval,
    )
    collector.start()

    print("Starlink gRPC collector started")
    print(f"gRPC target: {args.grpc_host}:{args.grpc_port}")
    print(f"HTTP: 0.0.0.0:{args.control_port}")
    app.run(host="0.0.0.0", port=args.control_port)


if __name__ == "__main__":
    main()
