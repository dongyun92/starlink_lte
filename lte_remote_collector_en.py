#!/usr/bin/env python3
"""
LTE Remote Data Collector for Aircraft (EC25 FIXED VERSION)
- Full LTE quality metrics
- Stable AT handling (URC safe)
- Ground station compatible
"""

from flask import Flask, jsonify, request, send_file
import threading
import time
import os
import csv
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import serial
import re

# ================= Configuration =================
CONTROL_PORT = 8897
DATA_DIR = "./lte-data"
CSV_PREFIX = "lte_data"
CSV_ROTATION_MINUTES = 10
CSV_MAX_SIZE_MB = 30
SERIAL_PORT = "/dev/ttyUSB0"
SERIAL_BAUDRATE = 115200
COLLECTION_INTERVAL = 5
# =================================================

app = Flask(__name__)
collector = None

class CollectorState(Enum):
    IDLE = "idle"
    COLLECTING = "collecting"
    ERROR = "error"

@dataclass
class LTEStatus:
    timestamp: str
    rssi: int
    ber: int
    network_type: str
    network_operator: str
    network_operator_numeric: str
    network_band: str
    network_channel: int
    cell_id: str
    lac: str
    registration_status: str
    eps_reg_status: str
    eps_tac: str
    eps_cell_id: str
    eps_act: str
    cs_reg_status: str
    cs_lac: str
    cs_cell_id: str
    cs_act: str
    ip_address: str
    connection_state: str
    rx_bytes: int
    tx_bytes: int
    rsrp: int
    rsrq: int
    sinr: int


# ================= LTE MODULE =================
class LTEModule:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False

    def connect(self):
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0,
                rtscts=False,
                dsrdtr=False,
                xonxoff=False
            )
            time.sleep(0.5)
            self.send_at("ATE0")
            self.connected = True
            print(f"[INFO] LTE module connected on {self.port}")
            return True
        except Exception as e:
            print(f"[ERROR] LTE connect failed: {e}")
            return False

    def read_response(self, timeout=3.0):
        end = time.time() + timeout
        buf = ""
        while time.time() < end:
            if self.ser.in_waiting:
                buf += self.ser.read(self.ser.in_waiting).decode("utf-8", errors="ignore")
                if "OK" in buf or "ERROR" in buf:
                    break
            time.sleep(0.05)
        return buf.strip()

    def send_at(self, cmd, timeout=3.0):
        if not self.connected:
            return None
        self.ser.reset_input_buffer()
        self.ser.write(f"{cmd}\r\n".encode())
        return self.read_response(timeout)

    def get_signal_quality(self):
        r = self.send_at("AT+CSQ")
        m = re.search(r"\+CSQ:\s*(\d+),(\d+)", r or "")
        if not m:
            return -999, 0
        rssi_raw = int(m.group(1))
        ber = int(m.group(2))
        rssi = -113 + rssi_raw * 2 if rssi_raw != 99 else -999
        return rssi, ber

    def get_network_info(self):
        r = self.send_at("AT+QNWINFO")
        m = re.search(r'\+QNWINFO:\s*"([^"]+)","([^"]+)","([^"]+)",(\d+)', r or "")
        if not m:
            return {}
        return {
            "type": m.group(1),
            "operator": m.group(2),
            "band": m.group(3),
            "channel": int(m.group(4)),
        }

    def get_operator_name(self):
        r = self.send_at("AT+COPS?")
        m = re.search(r'\+COPS:\s*\d+,\d+,"([^"]+)"', r or "")
        return m.group(1) if m else "Unknown"

    def get_eps_registration_detail(self):
        r = self.send_at("AT+CEREG?")
        m = re.search(r"\+CEREG:\s*(\d+),(\d+)(?:,([^,]+),([^,]+)(?:,(\d+))?)?", r or "")
        if not m:
            return {}
        return {
            "stat": m.group(2),
            "tac": (m.group(3) or "").strip('"'),
            "ci": (m.group(4) or "").strip('"'),
            "act": m.group(5) or "",
        }

    def get_cs_registration_detail(self):
        r = self.send_at("AT+CREG?")
        m = re.search(r"\+CREG:\s*(\d+),(\d+)(?:,([^,]+),([^,]+)(?:,(\d+))?)?", r or "")
        if not m:
            return {}
        return {
            "stat": m.group(2),
            "lac": (m.group(3) or "").strip('"'),
            "ci": (m.group(4) or "").strip('"'),
            "act": m.group(5) or "",
        }

    def get_registration(self):
        if re.search(r"\+CEREG:\s*\d+,(1|5)", self.send_at("AT+CEREG?") or ""):
            return "Registered (LTE)"
        if re.search(r"\+CREG:\s*\d+,(1|5)", self.send_at("AT+CREG?") or ""):
            return "Registered (2G/3G)"
        return "Not Registered"

    def get_cell_info(self):
        r = self.send_at('AT+QENG="servingcell"', timeout=3)
        for line in (r or "").splitlines():
            if "LTE" in line and "servingcell" in line:
                p = [x.strip() for x in line.split(",")]
                try:
                    return p[-5], p[-6]
                except:
                    pass
        return "0", "0"

    def get_extended_signal(self, is_lte):
        if not is_lte:
            return -999, -999, -999
        def parse(cmd, key):
            r = self.send_at(cmd)
            m = re.search(rf"\+{key}:\s*(-?\d+)", r or "")
            return int(m.group(1)) if m else -999
        return (
            parse("AT+QRSRP", "QRSRP"),
            parse("AT+QRSRQ", "QRSRQ"),
            parse("AT+QSINR", "QSINR"),
        )

    def get_data_usage(self):
        r = self.send_at("AT+QGDCNT?")
        m = re.search(r"\+QGDCNT:\s*(\d+),(\d+)", r or "")
        return (int(m.group(2)), int(m.group(1))) if m else (0, 0)

    def get_pdp_address(self, cid=1):
        r = self.send_at(f"AT+CGPADDR={cid}")
        m = re.search(rf"\+CGPADDR:\s*{cid},\"([^\"]+)\"", r or "")
        return m.group(1) if m else ""


# ================= COLLECTOR =================
class LTEDataCollector:
    def __init__(self):
        self.state = CollectorState.IDLE
        self.data = []
        self.stop_event = threading.Event()
        self.thread = None
        self.csv_file = None
        self.csv_writer = None
        self.csv_path = None
        self.last_rotate = time.time()

        os.makedirs(DATA_DIR, exist_ok=True)

        self.modem = LTEModule(SERIAL_PORT, SERIAL_BAUDRATE)
        if not self.modem.connect():
            raise RuntimeError("LTE module not available")

    def rotate_csv(self):
        if self.csv_file:
            self.csv_file.close()
        name = datetime.now().strftime(f"{CSV_PREFIX}_%Y%m%d_%H%M.csv")
        self.csv_path = os.path.join(DATA_DIR, name)
        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.DictWriter(
            self.csv_file, fieldnames=LTEStatus.__dataclass_fields__.keys()
        )
        self.csv_writer.writeheader()
        self.last_rotate = time.time()

    def collect_once(self):
        now = datetime.utcnow().isoformat() + "Z"
        rssi, ber = self.modem.get_signal_quality()
        net = self.modem.get_network_info()
        operator_name = self.modem.get_operator_name()
        eps_reg = self.modem.get_eps_registration_detail()
        cs_reg = self.modem.get_cs_registration_detail()
        reg = "Not Registered"
        if eps_reg.get("stat") in {"1", "5"}:
            reg = "Registered (LTE)"
        elif cs_reg.get("stat") in {"1", "5"}:
            reg = "Registered (2G/3G)"
        cell, lac = self.modem.get_cell_info()
        rx, tx = self.modem.get_data_usage()
        is_lte = "LTE" in net.get("type", "").upper()
        rsrp, rsrq, sinr = self.modem.get_extended_signal(is_lte)
        ip_address = self.modem.get_pdp_address()

        data = LTEStatus(
            timestamp=now,
            rssi=rssi,
            ber=ber,
            network_type="LTE" if is_lte else "OTHER",
            network_operator=operator_name,
            network_operator_numeric=net.get("operator", "Unknown"),
            network_band=net.get("band", ""),
            network_channel=net.get("channel", 0),
            cell_id=cell,
            lac=lac,
            registration_status=reg,
            eps_reg_status=eps_reg.get("stat", ""),
            eps_tac=eps_reg.get("tac", ""),
            eps_cell_id=eps_reg.get("ci", ""),
            eps_act=eps_reg.get("act", ""),
            cs_reg_status=cs_reg.get("stat", ""),
            cs_lac=cs_reg.get("lac", ""),
            cs_cell_id=cs_reg.get("ci", ""),
            cs_act=cs_reg.get("act", ""),
            ip_address=ip_address,
            connection_state="Connected" if "Registered" in reg else "Disconnected",
            rx_bytes=rx,
            tx_bytes=tx,
            rsrp=rsrp,
            rsrq=rsrq,
            sinr=sinr,
        )
        print(json.dumps(asdict(data), ensure_ascii=True))
        return data

    def worker(self):
        self.rotate_csv()
        while not self.stop_event.is_set():
            if time.time() - self.last_rotate > CSV_ROTATION_MINUTES * 60:
                self.rotate_csv()

            data = self.collect_once()
            self.csv_writer.writerow(asdict(data))
            self.csv_file.flush()
            self.data.append(data)
            self.data = self.data[-100:]
            time.sleep(COLLECTION_INTERVAL)

    def start(self):
        if self.state == CollectorState.COLLECTING:
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()
        self.state = CollectorState.COLLECTING

    def stop(self):
        self.stop_event.set()
        self.state = CollectorState.IDLE

# ================= API =================
@app.route("/api/current_data")
@app.route("/api/live_data")
def live_data():
    if not collector or not collector.data:
        return jsonify({})
    return jsonify(asdict(collector.data[-1]))

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LTE Remote Data Collector")
    parser.add_argument("--data-dir", default=DATA_DIR, help="Data directory")
    parser.add_argument("--control-port", type=int, default=CONTROL_PORT, help="Control API port")
    parser.add_argument("--serial-port", default=SERIAL_PORT, help="Serial port for LTE module")
    parser.add_argument("--interval", type=int, default=COLLECTION_INTERVAL, help="Collection interval in seconds")

    args = parser.parse_args()

    DATA_DIR = args.data_dir
    CONTROL_PORT = args.control_port
    SERIAL_PORT = args.serial_port
    COLLECTION_INTERVAL = args.interval

    print("=" * 60)
    print("LTE REMOTE DATA COLLECTOR")
    print("=" * 60)
    print(f"Control Port: {CONTROL_PORT}")
    print(f"Data Directory: {DATA_DIR}")
    print(f"Serial Port: {SERIAL_PORT}")
    print(f"Collection Interval: {COLLECTION_INTERVAL} seconds")
    print("=" * 60)

    collector = LTEDataCollector()
    collector.start()

    app.run(host="0.0.0.0", port=CONTROL_PORT)
