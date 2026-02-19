"""
ULG → TXT 변환기 API
비행시험 데이터 양식(TXT) 출력
"""
import io
import os
import tempfile
import numpy as np
import pandas as pd
import utm as utm_lib

from flask import Blueprint, render_template, request, Response, jsonify
from pyulog import ULog

ulg_converter_bp = Blueprint('ulg_converter', __name__)


# ──────────────────────────────────────────────
# 헬퍼: 토픽 꺼내기
# ──────────────────────────────────────────────

def _get_topic(ulog: ULog, name: str, multi_id: int = 0) -> pd.DataFrame | None:
    for d in ulog.data_list:
        if d.name == name and d.multi_id == multi_id:
            df = pd.DataFrame(d.data)
            df['ts'] = df['timestamp'] / 1e6  # μs → s
            return df.sort_values('ts').reset_index(drop=True)
    return None


def _quat_to_euler(q0, q1, q2, q3):
    """쿼터니언 → Roll/Pitch/Yaw (degrees)"""
    roll  = np.degrees(np.arctan2(2*(q0*q1 + q2*q3), 1 - 2*(q1**2 + q2**2)))
    sin_p = np.clip(2*(q0*q2 - q3*q1), -1.0, 1.0)
    pitch = np.degrees(np.arcsin(sin_p))
    yaw   = np.degrees(np.arctan2(2*(q0*q3 + q1*q2), 1 - 2*(q2**2 + q3**2)))
    return roll, pitch, yaw


def _interp_to(base_ts: np.ndarray, src_df: pd.DataFrame, col: str) -> np.ndarray:
    """src_df[col]을 base_ts 기준으로 선형 보간"""
    if src_df is None:
        return np.zeros(len(base_ts))
    return np.interp(base_ts, src_df['ts'].values, src_df[col].values,
                     left=src_df[col].values[0], right=src_df[col].values[-1])


# ──────────────────────────────────────────────
# 변환 핵심 함수
# ──────────────────────────────────────────────

def convert_ulg_to_txt(ulg_path: str) -> str:
    ulog = ULog(ulg_path)

    # 기준 토픽: vehicle_global_position (≈25 Hz)
    gp = _get_topic(ulog, 'vehicle_global_position')
    if gp is None:
        raise ValueError("vehicle_global_position 토픽이 없습니다 (GPS 데이터 없음)")

    base_ts = gp['ts'].values
    t0 = base_ts[0]
    time_sec = base_ts - t0  # 경과 시간 (초)

    # ── 위치: lat/lon → UTM ──────────────────
    lats = gp['lat'].values
    lons = gp['lon'].values
    alts = gp['alt'].values

    utm_x = np.empty(len(lats))
    utm_y = np.empty(len(lats))
    for i, (la, lo) in enumerate(zip(lats, lons)):
        easting, northing, _, _ = utm_lib.from_latlon(la, lo)
        utm_x[i] = easting
        utm_y[i] = northing
    utm_z = alts.copy()

    # ── 기압고도 / 기압 ──────────────────────
    ad = _get_topic(ulog, 'vehicle_air_data')
    alt_baro = _interp_to(base_ts, ad, 'baro_alt_meter') if ad is not None else alts
    ps_pa    = _interp_to(base_ts, ad, 'baro_pressure_pa') if ad is not None else np.zeros(len(base_ts))

    # ── 동압 (피토관) ─────────────────────────
    dp = _get_topic(ulog, 'differential_pressure')
    pd_pa = _interp_to(base_ts, dp, 'differential_pressure_pa') if dp is not None else np.zeros(len(base_ts))

    # ── 대기속도 ─────────────────────────────
    asp = _get_topic(ulog, 'airspeed')
    tas_ms  = _interp_to(base_ts, asp, 'true_airspeed_m_s') if asp is not None else np.zeros(len(base_ts))
    tas_kmh = tas_ms * 3.6

    # ── 자세: 쿼터니언 → 오일러 ───────────────
    att = _get_topic(ulog, 'vehicle_attitude')
    if att is not None:
        q0 = _interp_to(base_ts, att, 'q[0]')
        q1 = _interp_to(base_ts, att, 'q[1]')
        q2 = _interp_to(base_ts, att, 'q[2]')
        q3 = _interp_to(base_ts, att, 'q[3]')
        roll_deg, pitch_deg, yaw_deg = _quat_to_euler(q0, q1, q2, q3)
    else:
        roll_deg = pitch_deg = yaw_deg = np.zeros(len(base_ts))

    # ── 각속도: rad/s → deg/s ─────────────────
    av = _get_topic(ulog, 'vehicle_angular_velocity')
    if av is not None:
        p_dps = np.degrees(_interp_to(base_ts, av, 'xyz[0]'))
        q_dps = np.degrees(_interp_to(base_ts, av, 'xyz[1]'))
        r_dps = np.degrees(_interp_to(base_ts, av, 'xyz[2]'))
    else:
        p_dps = q_dps = r_dps = np.zeros(len(base_ts))

    # AOA / AOS : 센서 없으면 0
    aoa = np.zeros(len(base_ts))
    aos = np.zeros(len(base_ts))

    # ── TXT 생성 ─────────────────────────────
    header = (
        "Time UTM-X(m) UTM-Y(m) UTM-Z(m) Alt.(m) TrueAirspeed(km/h) "
        "Ps(pascal) Pd(pascal) AOA(deg) AOS(deg) "
        "Roll(deg) Pitch(deg) Yaw(deg) P(deg/s) Q(deg/s) R(deg/s)"
    )
    lines = [header]
    for i in range(len(base_ts)):
        line = (
            f"{time_sec[i]:.3f} "
            f"{utm_x[i]:.3f} {utm_y[i]:.3f} {utm_z[i]:.3f} "
            f"{alt_baro[i]:.3f} "
            f"{tas_kmh[i]:.3f} "
            f"{ps_pa[i]:.3f} {pd_pa[i]:.3f} "
            f"{aoa[i]:.3f} {aos[i]:.3f} "
            f"{roll_deg[i]:.4f} {pitch_deg[i]:.4f} {yaw_deg[i]:.4f} "
            f"{p_dps[i]:.4f} {q_dps[i]:.4f} {r_dps[i]:.4f}"
        )
        lines.append(line)

    return "\n".join(lines)


# ──────────────────────────────────────────────
# Flask 라우트
# ──────────────────────────────────────────────

@ulg_converter_bp.route('/converter')
def converter_page():
    return render_template('ulg_converter.html')


@ulg_converter_bp.route('/converter/convert', methods=['POST'])
def converter_convert():
    if 'file' not in request.files:
        return jsonify({'error': '파일이 없습니다'}), 400

    f = request.files['file']
    if not f.filename.endswith('.ulg'):
        return jsonify({'error': '.ulg 파일만 지원합니다'}), 400

    # 임시 파일로 저장 (pyulog는 파일 경로 필요)
    with tempfile.NamedTemporaryFile(suffix='.ulg', delete=False) as tmp:
        tmp_path = tmp.name
        f.save(tmp_path)

    try:
        txt_content = convert_ulg_to_txt(tmp_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        os.unlink(tmp_path)

    # 파일명: 원본 .ulg → .txt
    out_name = f.filename.replace('.ulg', '.txt')

    return Response(
        txt_content,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename="{out_name}"',
            'Content-Type': 'text/plain; charset=utf-8',
        }
    )
