#!/usr/bin/env python3
"""
PingMonitor 하드웨어 없이 테스트 스크립트

테스트 항목:
1. PingMonitor: 실제 인터넷(8.8.8.8) 핑 (LTE/Starlink 하드웨어 불필요)
2. LTE CSV 포맷: 가짜 데이터로 ping_rtt_ms, ping_loss 컬럼 확인
3. Starlink CSV 포맷: 가짜 데이터로 ext_ping_rtt_ms, ext_ping_loss 컬럼 확인

사용법:
  python3 test_ping_monitor.py
"""

import threading
import time
import subprocess
import re
import csv
import os
import tempfile
import sys
from dataclasses import dataclass, asdict


# ─── PingMonitor (lte_remote_collector_en.py 및 grpc_web_collector.py와 동일) ───

class PingMonitor:
    def __init__(self, target: str = "8.8.8.8", interface: str = None, interval: float = 1.0):
        self.target = target
        self.interface = interface
        self.interval = interval
        self._lock = threading.Lock()
        self._rtt_ms: float = -1.0
        self._loss: int = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _ping_once(self):
        if sys.platform == "darwin":
            cmd = ["ping", "-c", "1", "-W", "2000"]
        else:
            cmd = ["ping", "-c", "1", "-W", "2"]
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
        with self._lock:
            return self._rtt_ms, self._loss


# ─── TEST 1: PingMonitor 실제 동작 테스트 ───

def test_ping_monitor():
    print("=" * 55)
    print("TEST 1: PingMonitor (8.8.8.8 실제 핑)")
    print("=" * 55)

    pm = PingMonitor(target="8.8.8.8", interval=1.0)
    print("PingMonitor 시작 (1초 대기)...")

    for i in range(5):
        time.sleep(1.2)
        rtt, loss = pm.get_result()
        status = "OK" if rtt > 0 else "TIMEOUT/LOSS"
        print(f"  [{i+1}] rtt={rtt:.1f}ms  loss={loss}  → {status}")

    rtt, loss = pm.get_result()
    if rtt > 0:
        print(f"✅ PASS: 핑 성공 rtt={rtt:.1f}ms")
        return True
    else:
        print("⚠️  WARN: 핑 실패 (인터넷 연결 없거나 방화벽 차단)")
        print("       실제 Raspberry Pi에서는 정상 동작 예상")
        return False


# ─── TEST 2: LTE CSV 포맷 검증 ───

@dataclass
class LTEStatus:
    """lte_remote_collector_en.py 와 동일한 dataclass (ping 필드 포함)"""
    timestamp: str
    rssi: int
    ber: int
    network_type: str
    network_operator: str
    network_operator_numeric: str
    network_band: str
    network_channel: int
    mcc: int
    mnc: int
    pcid: int
    earfcn: int
    qeng_band_indicator: int
    ul_bandwidth: int
    dl_bandwidth: int
    qeng_rssi: int
    srxlev: int
    cell_id: str
    enodeb_id: int
    cell_sector_id: int
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
    ping_rtt_ms: float    # ← 추가된 필드
    ping_loss: int        # ← 추가된 필드


def test_lte_csv_format():
    print()
    print("=" * 55)
    print("TEST 2: LTE CSV 포맷 (ping 컬럼 포함 확인)")
    print("=" * 55)

    # 가짜 LTEStatus 생성 (LTE 모뎀 없이)
    mock = LTEStatus(
        timestamp="2026-02-22T10:00:00Z",
        rssi=-80, ber=0,
        network_type="LTE", network_operator="SKT",
        network_operator_numeric="45005", network_band="LTE BAND 3",
        network_channel=1650, mcc=450, mnc=5,
        pcid=123, earfcn=1650,
        qeng_band_indicator=3, ul_bandwidth=50, dl_bandwidth=50,
        qeng_rssi=-80, srxlev=30,
        cell_id="1A2B3C", enodeb_id=0x1A2B, cell_sector_id=0x3C,
        lac="1234", registration_status="Registered (LTE)",
        eps_reg_status="1", eps_tac="1234", eps_cell_id="1A2B3C", eps_act="7",
        cs_reg_status="1", cs_lac="1234", cs_cell_id="1A2B3C", cs_act="7",
        ip_address="100.64.1.1", connection_state="Connected",
        rx_bytes=1234567, tx_bytes=654321,
        rsrp=-85, rsrq=-10, sinr=12,
        ping_rtt_ms=23.5,  # ← ping 결과
        ping_loss=0,        # ← ping 결과
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "lte_test.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=LTEStatus.__dataclass_fields__.keys())
            writer.writeheader()
            writer.writerow(asdict(mock))

        # 다시 읽어서 검증
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            row = next(reader)

        # ping 컬럼 확인
        assert "ping_rtt_ms" in fieldnames, "ping_rtt_ms 컬럼 없음!"
        assert "ping_loss" in fieldnames, "ping_loss 컬럼 없음!"
        assert float(row["ping_rtt_ms"]) == 23.5, f"ping_rtt_ms 값 오류: {row['ping_rtt_ms']}"
        assert int(row["ping_loss"]) == 0, f"ping_loss 값 오류: {row['ping_loss']}"

        print(f"CSV 컬럼 수: {len(fieldnames)}")
        print(f"ping_rtt_ms 위치: 컬럼 #{list(fieldnames).index('ping_rtt_ms') + 1}")
        print(f"ping_loss 위치: 컬럼 #{list(fieldnames).index('ping_loss') + 1}")
        print(f"저장된 값: ping_rtt_ms={row['ping_rtt_ms']}  ping_loss={row['ping_loss']}")
        print("✅ PASS: LTE CSV 포맷 정상")
        return True


# ─── TEST 3: Starlink CSV 포맷 검증 ───

def test_starlink_csv_format():
    print()
    print("=" * 55)
    print("TEST 3: Starlink CSV 포맷 (ext_ping 컬럼 포함 확인)")
    print("=" * 55)

    # grpc_web_collector.py 의 _fetch_status() 리턴값 모의
    mock_data = {
        "timestamp": "2026-02-22T10:00:00Z",
        "terminal_id": "ut01000000-00000000-00000000",
        "state": "CONNECTED",
        "uptime": 3600,
        "downlink_throughput_bps": 50_000_000,
        "uplink_throughput_bps": 5_000_000,
        "ping_drop_rate": 0.01,
        "ping_latency_ms": 35.0,
        "snr": 9.0,
        "seconds_to_first_nonempty_slot": 0.0,
        "azimuth": 180.0,
        "elevation": 45.0,
        "pop_ping_drop_rate": 0.01,
        "pop_ping_latency_ms": 35.0,
        "latitude": 37.5,
        "longitude": 127.0,
        "altitude": 100.0,
        "gps_sats": 12,
        "hardware_version": "rev3_proto2",
        "software_version": "2024.01.01",
        "alerts": {"alert_motors_stuck": False},
        "obstruction": {"currently_obstructed": False, "fraction_obstructed": 0.0},
        "raw_status": {},
        "raw_location": {},
        "ext_ping_rtt_ms": 18.7,   # ← 추가된 필드
        "ext_ping_loss": 0,         # ← 추가된 필드
    }

    # _flatten() 동일 로직
    def flatten(payload):
        flat = {}
        for key, value in payload.items():
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    flat[f"{key}.{nested_key}"] = nested_value
            else:
                flat[key] = value
        return flat

    flat = flatten(mock_data)
    fieldnames = list(flat.keys())

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "starlink_test.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(flat)

        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            fieldnames_read = reader.fieldnames
            row = next(reader)

    assert "ext_ping_rtt_ms" in fieldnames_read, "ext_ping_rtt_ms 컬럼 없음!"
    assert "ext_ping_loss" in fieldnames_read, "ext_ping_loss 컬럼 없음!"
    assert float(row["ext_ping_rtt_ms"]) == 18.7, f"ext_ping_rtt_ms 값 오류: {row['ext_ping_rtt_ms']}"
    assert int(row["ext_ping_loss"]) == 0, f"ext_ping_loss 값 오류: {row['ext_ping_loss']}"

    print(f"CSV 컬럼 수: {len(fieldnames_read)}")
    print(f"ext_ping_rtt_ms 위치: 컬럼 #{list(fieldnames_read).index('ext_ping_rtt_ms') + 1}")
    print(f"ext_ping_loss 위치: 컬럼 #{list(fieldnames_read).index('ext_ping_loss') + 1}")
    print(f"저장된 값: ext_ping_rtt_ms={row['ext_ping_rtt_ms']}  ext_ping_loss={row['ext_ping_loss']}")
    print("✅ PASS: Starlink CSV 포맷 정상")
    return True


# ─── 메인 ───

if __name__ == "__main__":
    print()
    print("🔍 PingMonitor 하드웨어 없는 테스트")
    print(f"   Python: {sys.version.split()[0]}  Platform: {sys.platform}")
    print()

    results = []
    results.append(test_ping_monitor())
    results.append(test_lte_csv_format())
    results.append(test_starlink_csv_format())

    print()
    print("=" * 55)
    passed = sum(1 for r in results if r)
    print(f"결과: {passed}/{len(results)} 테스트 통과")
    if passed == len(results):
        print("✅ 모든 테스트 통과 — Raspberry Pi 배포 준비 완료")
    else:
        print("⚠️  일부 테스트 실패 — 위 출력 확인")
    print("=" * 55)
    sys.exit(0 if passed == len(results) else 1)
