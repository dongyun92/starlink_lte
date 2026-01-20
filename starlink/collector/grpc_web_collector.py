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
from flask import Flask, jsonify

from starlink.real_starlink_api import RealStarlinkAPI


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
    def __init__(self, dish_ip: str, interval: float):
        self.api = RealStarlinkAPI(dish_ip=dish_ip)
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
                data = self.api.get_status_with_fallback()
                self.current_data = data
                self.last_error = ""
                self.last_update = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                if self.state != CollectorState.RUNNING:
                    self.state = CollectorState.RUNNING
            except Exception as exc:
                self.last_error = str(exc)
                self.state = CollectorState.ERROR
            time.sleep(self.interval)

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
    parser.add_argument("--dish-ip", default="192.168.100.1", help="Starlink dish IP")
    parser.add_argument("--control-port", type=int, default=9201, help="Collector HTTP port")
    parser.add_argument("--interval", type=float, default=3.0, help="Collection interval in seconds")
    args = parser.parse_args()

    global collector
    collector = GrpcWebCollector(dish_ip=args.dish_ip, interval=args.interval)
    collector.start()

    print("Starlink gRPC-Web collector started")
    print(f"Dish: {args.dish_ip}:9201")
    print(f"HTTP: 0.0.0.0:{args.control_port}")
    app.run(host="0.0.0.0", port=args.control_port)


if __name__ == "__main__":
    main()
