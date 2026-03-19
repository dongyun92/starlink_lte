#!/usr/bin/env python3
"""
Starlink gRPC-Web collector service.
Exposes the same HTTP JSON endpoints as the simulator so the ground station
can connect by port only.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import logging
import threading
import time
from pathlib import Path
import sys
import csv
import re
import subprocess
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
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("starlink_grpc_collector")


class CollectorState:
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    ERROR = "ERROR"


@dataclass
class CollectorStatus:
    state: str
    last_update: str
    last_error: str


class PingMonitor:
    """Background daemon thread that runs periodic pings; main loop reads results non-blocking."""

    def __init__(self, target: str = "8.8.8.8", interface: str = None, interval: float = 1.0):
        self.target = target
        self.interface = interface
        self.interval = interval
        self._lock = threading.Lock()
        self._rtt_ms: float = -1.0  # -1.0 = no result yet or timeout
        self._loss: int = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _ping_once(self):
        import sys
        if sys.platform == "darwin":
            cmd = ["ping", "-c", "1", "-W", "2000"]  # macOS: -W in milliseconds
        else:
            cmd = ["ping", "-c", "1", "-W", "2"]     # Linux: -W in seconds
        if self.interface:
            cmd += ["-I", self.interface]
        cmd.append(self.target)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            m = re.search(r"time[=<](\d+\.?\d*)\s*ms", result.stdout)
            if m:
                return float(m.group(1)), 0
            return -1.0, 1
        except Exception:
            return -1.0, 1

    def _run(self):
        while True:
            rtt, loss = self._ping_once()
            with self._lock:
                self._rtt_ms = rtt
                self._loss = loss
            time.sleep(self.interval)

    def get_result(self):
        """Returns (rtt_ms, loss) from last completed ping. rtt=-1.0 means timeout."""
        with self._lock:
            return self._rtt_ms, self._loss


class PopMonitor:
    """Background thread that periodically resolves public IP and Starlink POP via PTR record."""

    def __init__(self, interval: float = 10.0):
        self.interval = interval
        self._lock = threading.Lock()
        self._public_ip: str = ""
        self._ptr_record: str = ""
        self._pop_name: str = ""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _resolve_once(self):
        import urllib.request
        try:
            ip = urllib.request.urlopen("https://ifconfig.me", timeout=5).read().decode().strip()
        except Exception:
            return "", "", ""
        ptr = ""
        try:
            result = subprocess.run(
                ["dig", "-x", ip, "+short"],
                capture_output=True, text=True, timeout=5,
            )
            ptr = result.stdout.strip().rstrip(".")
        except Exception:
            pass
        pop = ""
        m = re.search(r"customer\.([^.]+)\.pop\.starlinkisp\.net", ptr)
        if m:
            pop = m.group(1)
        return ip, ptr, pop

    def _run(self):
        while True:
            ip, ptr, pop = self._resolve_once()
            with self._lock:
                self._public_ip = ip
                self._ptr_record = ptr
                self._pop_name = pop
            time.sleep(self.interval)

    def get_result(self):
        with self._lock:
            return self._public_ip, self._ptr_record, self._pop_name


class GrpcWebCollector:
    def __init__(self, grpc_host: str, grpc_port: int, interval: float, data_dir: str, ping_target: str = "8.8.8.8", ping_interface: str = None):
        self.grpc_host = grpc_host
        self.grpc_port = grpc_port
        self.context = starlink_grpc.ChannelContext(target=f"{grpc_host}:{grpc_port}")
        self.interval = interval
        self.state = CollectorState.IDLE
        self.last_error = ""
        self.last_update = ""
        self.current_data = {}
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = None
        self.current_writer = None
        self.current_fields = None
        self.file_start_time = None
        self.max_file_duration = 600
        self._thread = None
        self._stop_event = threading.Event()
        self.ping_monitor = PingMonitor(target=ping_target, interface=ping_interface)
        self.pop_monitor = PopMonitor(interval=10.0)

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
                self._maybe_rotate_file()
                self._write_csv(self.current_data)
                logger.info("Starlink data collected (fields=%s)", len(self.current_data))
            except Exception as exc:
                self.last_error = str(exc)
                self.state = CollectorState.ERROR
                logger.error("Collection error: %s", self.last_error)
            time.sleep(self.interval)

    def _fetch_status(self):
        ping_rtt_ms, ping_loss = self.ping_monitor.get_result()
        public_ip, ptr_record, pop_name = self.pop_monitor.get_result()
        status, obstruction, alerts = starlink_grpc.status_data(context=self.context)
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
            "alerts": alerts,
            "obstruction": obstruction,
            "raw_status": status,
            "raw_location": location,
            "ext_ping_rtt_ms": ping_rtt_ms,
            "ext_ping_loss": ping_loss,
            "public_ip": public_ip,
            "ptr_record": ptr_record,
            "pop_name": pop_name,
        }

    def _maybe_rotate_file(self):
        if not self.current_file:
            self._open_new_file()
            return
        if not self.file_start_time:
            self._open_new_file()
            return
        if (datetime.now(timezone.utc) - self.file_start_time).total_seconds() >= self.max_file_duration:
            self._open_new_file()

    def _flatten(self, payload):
        flat = {}
        for key, value in payload.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    flat[f"{key}.{nested_key}"] = nested_value
            else:
                flat[key] = value
        return flat

    def _open_new_file(self):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.current_file = self.data_dir / f"starlink_real_{timestamp}.csv"
        if self.current_writer:
            self.current_writer = None
        self.current_fields = None
        self.file_start_time = datetime.now(timezone.utc)

    def _write_csv(self, payload):
        if not payload:
            return
        flat = self._flatten(payload)
        fieldnames = list(flat.keys())
        if self.current_fields is None:
            # First write — create file with header
            self.current_fields = fieldnames
            with self.current_file.open("w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.current_fields)
                writer.writeheader()
                writer.writerow(flat)
            return
        if set(fieldnames) - set(self.current_fields):
            # New fields appeared — merge and rewrite file with all data
            merged = list(self.current_fields) + [f for f in fieldnames if f not in self.current_fields]
            existing_rows = []
            if self.current_file.exists():
                with self.current_file.open("r", newline="") as csvfile:
                    existing_rows = list(csv.DictReader(csvfile))
            self.current_fields = merged
            with self.current_file.open("w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.current_fields, extrasaction="ignore")
                writer.writeheader()
                for row in existing_rows:
                    writer.writerow(row)
                writer.writerow(flat)
            return
        with self.current_file.open("a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.current_fields, extrasaction="ignore")
            writer.writerow(flat)

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
    parser.add_argument("--data-dir", default="/home/hanul/starlink-collect-data", help="CSV output directory")
    parser.add_argument("--ping-target", default="8.8.8.8", help="Ping target for internet connectivity check (default: 8.8.8.8)")
    parser.add_argument("--ping-interface", default=None, help="Network interface for ping, e.g. eth0 (default: auto)")
    args = parser.parse_args()

    global collector
    collector = GrpcWebCollector(
        grpc_host=args.grpc_host,
        grpc_port=args.grpc_port,
        interval=args.interval,
        data_dir=args.data_dir,
        ping_target=args.ping_target,
        ping_interface=args.ping_interface,
    )
    collector.start()

    print("Starlink gRPC collector started")
    print(f"gRPC target: {args.grpc_host}:{args.grpc_port}")
    print(f"HTTP: 0.0.0.0:{args.control_port}")
    app.run(host="0.0.0.0", port=args.control_port)


if __name__ == "__main__":
    main()
