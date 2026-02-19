#!/usr/bin/env python3
"""
범용 세션 분석 스크립트
- LTE 성능 분석 (RSRP/SINR/RSRQ)
- 3-Layer 통합 품질 분석 (RF + LTE + Starlink)
- 통계 데이터 CSV 생성

Usage: python analyze_session.py <session_id> <session_date>
Example: python analyze_session.py 1ed55628-37b6-4097-b796-8faef759db14 2026-01-23
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

def analyze_session(session_id: str, session_date: str):
    """세션 데이터를 분석하고 결과를 CSV로 저장"""

    print(f"\n{'='*60}")
    print(f"세션 분석 시작: {session_id}")
    print(f"비행 날짜: {session_date}")
    print(f"{'='*60}\n")

    # 파일 경로
    base_path = Path(__file__).parent.parent / 'analysis' / 'results' / session_id
    input_csv = base_path / 'merged_data.csv'
    output_dir = Path(__file__).parent / f'session_{session_date.replace("-", "")}'
    output_dir.mkdir(exist_ok=True)

    # 데이터 로드
    print(f"📂 데이터 로드: {input_csv}")
    df = pd.read_csv(input_csv)
    print(f"   총 데이터 포인트: {len(df):,}개")
    print(f"   컬럼: {list(df.columns[:10])}...")

    # ==============================================================
    # 1. RF/GPS 분석
    # ==============================================================
    print("\n" + "="*60)
    print("1️⃣ RF/GPS 성능 분석")
    print("="*60)

    if 'gps_nsat' in df.columns:
        avg_sats = df['gps_nsat'].mean()
        min_sats = df['gps_nsat'].min()
        max_sats = df['gps_nsat'].max()
        normal_count = (df['gps_nsat'] >= 10).sum()
        normal_pct = normal_count / len(df) * 100

        print(f"   평균 GPS 위성: {avg_sats:.1f}개")
        print(f"   범위: {min_sats:.0f} ~ {max_sats:.0f}개")
        print(f"   정상 (≥10개): {normal_pct:.1f}% ({normal_count:,}/{len(df):,})")

        df['rf_quality_ok'] = df['gps_nsat'] >= 10
    else:
        print("   ⚠️ GPS 데이터 없음")
        df['rf_quality_ok'] = True  # 기본값

    # ==============================================================
    # 2. LTE 분석
    # ==============================================================
    print("\n" + "="*60)
    print("2️⃣ LTE 성능 분석")
    print("="*60)

    lte_columns = ['lte_rsrp', 'lte_rssi', 'lte_rsrq', 'lte_sinr']
    has_lte = all(col in df.columns for col in lte_columns)

    if has_lte:
        # LTE 통계
        lte_stats = {
            'RSRP (dBm)': {
                'mean': df['lte_rsrp'].mean(),
                'min': df['lte_rsrp'].min(),
                'max': df['lte_rsrp'].max(),
                'excellent_pct': ((df['lte_rsrp'] > -80).sum() / len(df) * 100),
                'good_pct': (((df['lte_rsrp'] >= -90) & (df['lte_rsrp'] <= -80)).sum() / len(df) * 100),
                'poor_pct': ((df['lte_rsrp'] < -100).sum() / len(df) * 100)
            },
            'SINR (dB)': {
                'mean': df['lte_sinr'].mean(),
                'min': df['lte_sinr'].min(),
                'max': df['lte_sinr'].max(),
                'poor_pct': ((df['lte_sinr'] < 0).sum() / len(df) * 100)
            }
        }

        print(f"   📊 RSRP (신호 강도):")
        print(f"      평균: {lte_stats['RSRP (dBm)']['mean']:.1f} dBm")
        print(f"      범위: {lte_stats['RSRP (dBm)']['min']:.1f} ~ {lte_stats['RSRP (dBm)']['max']:.1f} dBm")
        print(f"      Excellent (>-80): {lte_stats['RSRP (dBm)']['excellent_pct']:.1f}%")
        print(f"      Good (-80~-90): {lte_stats['RSRP (dBm)']['good_pct']:.1f}%")
        print(f"      Poor (<-100): {lte_stats['RSRP (dBm)']['poor_pct']:.1f}%")

        print(f"\n   📊 SINR (신호 품질):")
        print(f"      평균: {lte_stats['SINR (dB)']['mean']:.1f} dB")
        print(f"      범위: {lte_stats['SINR (dB)']['min']:.1f} ~ {lte_stats['SINR (dB)']['max']:.1f} dB")
        print(f"      Poor (<0 dB): {lte_stats['SINR (dB)']['poor_pct']:.1f}%")

        # LTE 품질 판정 (RSRP > -110 AND SINR > 0)
        df['lte_quality_ok'] = (df['lte_rsrp'] > -110) & (df['lte_sinr'] > 0)
        lte_ok_count = df['lte_quality_ok'].sum()
        lte_ok_pct = lte_ok_count / len(df) * 100

        print(f"\n   ✅ LTE 품질 판정 (RSRP > -110 AND SINR > 0):")
        print(f"      정상: {lte_ok_pct:.1f}% ({lte_ok_count:,}/{len(df):,})")
        print(f"      비정상: {100-lte_ok_pct:.1f}% ({len(df)-lte_ok_count:,}/{len(df):,})")

        # LTE 통계 CSV 저장
        lte_stats_df = pd.DataFrame([{
            'metric': 'RSRP',
            'mean': lte_stats['RSRP (dBm)']['mean'],
            'min': lte_stats['RSRP (dBm)']['min'],
            'max': lte_stats['RSRP (dBm)']['max'],
            'excellent_pct': lte_stats['RSRP (dBm)']['excellent_pct'],
            'good_pct': lte_stats['RSRP (dBm)']['good_pct'],
            'poor_pct': lte_stats['RSRP (dBm)']['poor_pct']
        }, {
            'metric': 'SINR',
            'mean': lte_stats['SINR (dB)']['mean'],
            'min': lte_stats['SINR (dB)']['min'],
            'max': lte_stats['SINR (dB)']['max'],
            'poor_pct': lte_stats['SINR (dB)']['poor_pct']
        }])
        lte_stats_df.to_csv(output_dir / 'lte_statistics.csv', index=False)
        print(f"\n   💾 저장: {output_dir / 'lte_statistics.csv'}")
    else:
        print("   ⚠️ LTE 데이터 없음")
        df['lte_quality_ok'] = False

    # ==============================================================
    # 3. Starlink 분석
    # ==============================================================
    print("\n" + "="*60)
    print("3️⃣ Starlink 성능 분석")
    print("="*60)

    starlink_columns = ['starlink_state', 'starlink_downlink_throughput_bps', 'starlink_uplink_throughput_bps']
    has_starlink = all(col in df.columns for col in starlink_columns)

    if has_starlink:
        # Starlink 상태
        connected_count = (df['starlink_state'] == 'CONNECTED').sum()
        connected_pct = connected_count / len(df) * 100

        # 속도 통계 (bps → kbps)
        df['download_kbps'] = df['starlink_downlink_throughput_bps'] / 1000
        df['upload_kbps'] = df['starlink_uplink_throughput_bps'] / 1000

        avg_down = df['download_kbps'].mean()
        avg_up = df['upload_kbps'].mean()

        print(f"   🛰️ 연결 상태:")
        print(f"      CONNECTED: {connected_pct:.1f}% ({connected_count:,}/{len(df):,})")

        print(f"\n   📊 데이터 전송:")
        print(f"      평균 다운로드: {avg_down:.1f} kbps")
        print(f"      평균 업로드: {avg_up:.1f} kbps")

        # Starlink 품질 판정 (CONNECTED AND Download > 1 Mbps)
        df['starlink_quality_ok'] = (df['starlink_state'] == 'CONNECTED') & (df['download_kbps'] > 1000)
        starlink_ok_count = df['starlink_quality_ok'].sum()
        starlink_ok_pct = starlink_ok_count / len(df) * 100

        print(f"\n   ✅ Starlink 품질 판정 (CONNECTED AND Download > 1 Mbps):")
        print(f"      정상: {starlink_ok_pct:.1f}% ({starlink_ok_count:,}/{len(df):,})")
        print(f"      비정상: {100-starlink_ok_pct:.1f}% ({len(df)-starlink_ok_count:,}/{len(df):,})")

        # Roaming Alert 확인
        if 'starlink_alert_roaming' in df.columns:
            roaming_pct = (df['starlink_alert_roaming'] == True).sum() / len(df) * 100
            print(f"\n   ⚠️ Roaming Alert: {roaming_pct:.1f}%")

        # Starlink 통계 CSV 저장
        starlink_stats_df = pd.DataFrame([{
            'connected_pct': connected_pct,
            'avg_download_kbps': avg_down,
            'avg_upload_kbps': avg_up,
            'quality_ok_pct': starlink_ok_pct
        }])
        starlink_stats_df.to_csv(output_dir / 'starlink_statistics.csv', index=False)
        print(f"   💾 저장: {output_dir / 'starlink_statistics.csv'}")
    else:
        print("   ⚠️ Starlink 데이터 없음")
        df['starlink_quality_ok'] = False

    # ==============================================================
    # 4. 3-Layer 통합 품질 분석
    # ==============================================================
    print("\n" + "="*60)
    print("4️⃣ 3-Layer 통합 품질 분석")
    print("="*60)

    # 정상 신호 개수 계산
    df['signal_count'] = (
        df['rf_quality_ok'].astype(int) +
        df['lte_quality_ok'].astype(int) +
        df['starlink_quality_ok'].astype(int)
    )

    # 색상 코드 부여
    def get_color_code(count):
        if count == 3:
            return 'GREEN'
        elif count == 2:
            return 'YELLOW'
        elif count == 1:
            return 'ORANGE'
        else:
            return 'RED'

    df['signal_color'] = df['signal_count'].apply(get_color_code)

    # 색상별 통계
    color_stats = df['signal_color'].value_counts()
    total = len(df)

    print(f"   🎨 3-Layer 색상 분포:")
    for color in ['GREEN', 'YELLOW', 'ORANGE', 'RED']:
        count = color_stats.get(color, 0)
        pct = count / total * 100
        emoji = {'GREEN': '🟢', 'YELLOW': '🟡', 'ORANGE': '🟠', 'RED': '🔴'}[color]
        layer_count = {'GREEN': '3/3', 'YELLOW': '2/3', 'ORANGE': '1/3', 'RED': '0/3'}[color]
        print(f"      {emoji} {color} ({layer_count}): {pct:.1f}% ({count:,}개)")

    # 3-Layer 통계 CSV 저장
    three_layer_summary = pd.DataFrame([{
        'color': color,
        'count': color_stats.get(color, 0),
        'percentage': color_stats.get(color, 0) / total * 100
    } for color in ['GREEN', 'YELLOW', 'ORANGE', 'RED']])
    three_layer_summary.to_csv(output_dir / 'three_layer_summary.csv', index=False)
    print(f"\n   💾 저장: {output_dir / 'three_layer_summary.csv'}")

    # 전체 3-Layer 품질 데이터 저장
    three_layer_data = df[['timestamp', 'latitude', 'longitude', 'altitude',
                            'rf_quality_ok', 'lte_quality_ok', 'starlink_quality_ok',
                            'signal_count', 'signal_color']].copy()
    three_layer_data.to_csv(output_dir / 'three_layer_quality.csv', index=False)
    print(f"   💾 저장: {output_dir / 'three_layer_quality.csv'}")

    # ==============================================================
    # 5. 요약 통계
    # ==============================================================
    print("\n" + "="*60)
    print("📊 세션 분석 요약")
    print("="*60)

    summary = {
        'session_id': session_id,
        'session_date': session_date,
        'total_points': len(df),
        'rf_normal_pct': (df['rf_quality_ok'].sum() / len(df) * 100) if 'rf_quality_ok' in df else 0,
        'lte_normal_pct': (df['lte_quality_ok'].sum() / len(df) * 100) if has_lte else 0,
        'starlink_normal_pct': (df['starlink_quality_ok'].sum() / len(df) * 100) if has_starlink else 0,
        'green_pct': color_stats.get('GREEN', 0) / total * 100,
        'yellow_pct': color_stats.get('YELLOW', 0) / total * 100,
        'orange_pct': color_stats.get('ORANGE', 0) / total * 100,
        'red_pct': color_stats.get('RED', 0) / total * 100
    }

    print(f"   데이터 포인트: {summary['total_points']:,}개")
    print(f"   RF 정상률: {summary['rf_normal_pct']:.1f}%")
    print(f"   LTE 정상률: {summary['lte_normal_pct']:.1f}%")
    print(f"   Starlink 정상률: {summary['starlink_normal_pct']:.1f}%")
    print(f"   3-Layer 초록: {summary['green_pct']:.1f}%")
    print(f"   3-Layer 노랑: {summary['yellow_pct']:.1f}%")
    print(f"   3-Layer 오렌지: {summary['orange_pct']:.1f}%")
    print(f"   3-Layer 레드: {summary['red_pct']:.1f}%")

    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(output_dir / 'session_summary.csv', index=False)
    print(f"\n   💾 저장: {output_dir / 'session_summary.csv'}")

    print(f"\n{'='*60}")
    print(f"✅ 세션 분석 완료: {session_id}")
    print(f"{'='*60}\n")

    return summary

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python analyze_session.py <session_id> <session_date>")
        print("Example: python analyze_session.py 1ed55628-37b6-4097-b796-8faef759db14 2026-01-23")
        sys.exit(1)

    session_id = sys.argv[1]
    session_date = sys.argv[2]

    analyze_session(session_id, session_date)
