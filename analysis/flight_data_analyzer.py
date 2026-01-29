#!/usr/bin/env python3
"""
비행 데이터 분석 시스템
- ULG 비행 로그 + LTE 통신 품질 + Starlink 통신 품질 데이터 병합
- 지도 기반 통신 품질 히트맵 생성
- 자동 품질 보고서 생성
"""

import pyulog
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class FlightDataAnalyzer:
    """비행 데이터 분석기"""

    def __init__(self, ulg_path: str, lte_dir: str, starlink_dir: str):
        self.ulg_path = Path(ulg_path)
        self.lte_dir = Path(lte_dir)
        self.starlink_dir = Path(starlink_dir)

        # 데이터 저장소
        self.flight_data = None
        self.lte_data = None
        self.starlink_data = None
        self.merged_data = None

    def load_ulg_data(self) -> pd.DataFrame:
        """ULG 비행 로그에서 GPS 데이터 추출"""
        print(f"📁 Loading ULG: {self.ulg_path.name}")

        ulg = pyulog.ULog(str(self.ulg_path))

        # GPS 데이터 찾기
        gps_topic = None
        for topic in ulg.data_list:
            if topic.name == 'vehicle_gps_position':
                gps_topic = topic
                break

        if not gps_topic:
            raise ValueError("GPS data not found in ULG file")

        # DataFrame 생성
        df = pd.DataFrame({
            'timestamp_us': gps_topic.data['timestamp'],
            'latitude': gps_topic.data['latitude_deg'],
            'longitude': gps_topic.data['longitude_deg'],
            'altitude': gps_topic.data['altitude_msl_m'],
        })

        # ULG 타임스탬프를 초 단위로 변환
        df['time_sec'] = df['timestamp_us'] / 1e6

        print(f"✓ Loaded {len(df)} GPS points")
        print(f"  Duration: {df['time_sec'].max() - df['time_sec'].min():.2f} seconds")
        print(f"  Lat range: {df['latitude'].min():.6f} to {df['latitude'].max():.6f}")
        print(f"  Lon range: {df['longitude'].min():.6f} to {df['longitude'].max():.6f}")

        self.flight_data = df
        return df

    def load_lte_data(self) -> pd.DataFrame:
        """LTE CSV 파일들을 로드하고 병합"""
        print(f"\n📁 Loading LTE data from {self.lte_dir}")

        csv_files = sorted(self.lte_dir.glob('lte_data_*.csv'))
        print(f"  Found {len(csv_files)} LTE CSV files")

        dfs = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            dfs.append(df)

        # 모든 CSV 병합
        combined = pd.concat(dfs, ignore_index=True)

        # 타임스탬프 파싱
        combined['datetime'] = pd.to_datetime(combined['timestamp'], errors='coerce')
        # NaT 값을 제거하고 인덱스 재설정
        combined = combined.dropna(subset=['datetime']).reset_index(drop=True)
        # Unix 타임스탬프 변환 (NaT 체크 포함)
        combined['unix_timestamp'] = combined['datetime'].apply(
            lambda x: x.timestamp() if pd.notna(x) else np.nan
        )

        # 중복 제거 및 정렬
        combined = combined.drop_duplicates(subset=['timestamp']).sort_values('unix_timestamp')

        print(f"✓ Loaded {len(combined)} LTE records")
        print(f"  Time range: {combined['datetime'].min()} to {combined['datetime'].max()}")
        print(f"  RSSI range: {combined['rssi'].min()} to {combined['rssi'].max()} dBm")

        self.lte_data = combined
        return combined

    def load_starlink_data(self) -> pd.DataFrame:
        """Starlink CSV 파일들을 로드하고 병합"""
        print(f"\n📁 Loading Starlink data from {self.starlink_dir}")

        csv_files = sorted(self.starlink_dir.glob('starlink_real_*.csv'))
        print(f"  Found {len(csv_files)} Starlink CSV files")

        dfs = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            dfs.append(df)

        # 모든 CSV 병합
        combined = pd.concat(dfs, ignore_index=True)

        # 타임스탬프 파싱
        combined['datetime'] = pd.to_datetime(combined['timestamp'], errors='coerce')
        # NaT 값을 제거하고 인덱스 재설정
        combined = combined.dropna(subset=['datetime']).reset_index(drop=True)
        # Unix 타임스탬프 변환 (NaT 체크 포함)
        combined['unix_timestamp'] = combined['datetime'].apply(
            lambda x: x.timestamp() if pd.notna(x) else np.nan
        )

        # 중복 제거 및 정렬
        combined = combined.drop_duplicates(subset=['timestamp']).sort_values('unix_timestamp')

        print(f"✓ Loaded {len(combined)} Starlink records")
        print(f"  Time range: {combined['datetime'].min()} to {combined['datetime'].max()}")

        # ping_latency_ms에서 유효한 값만 사용
        valid_latency = combined[combined['ping_latency_ms'] >= 0]['ping_latency_ms']
        if len(valid_latency) > 0:
            print(f"  Latency range: {valid_latency.min():.2f} to {valid_latency.max():.2f} ms")
        else:
            print(f"  No valid latency data")

        self.starlink_data = combined
        return combined

    def find_time_offset(self) -> float:
        """
        LTE/Starlink CSV 타임스탬프와 ULG 타임스탬프 간의 오프셋 계산

        ULG는 부팅 이후 시간(초)이고, CSV는 UTC 타임스탬프이므로
        시작 시간을 기준으로 오프셋을 계산합니다.
        """
        # LTE 데이터의 첫 타임스탬프 (UTC)
        lte_start_utc = self.lte_data['unix_timestamp'].min()

        # ULG 데이터의 첫 타임스탬프 (부팅 이후 초)
        ulg_start_sec = self.flight_data['time_sec'].min()

        # 오프셋 = UTC 시작 시간 - ULG 시작 시간
        offset = lte_start_utc - ulg_start_sec

        print(f"\n⏱️  Time Offset Calculation:")
        print(f"  LTE start (UTC): {lte_start_utc:.2f}")
        print(f"  ULG start (sec): {ulg_start_sec:.2f}")
        print(f"  Offset: {offset:.2f} seconds")

        return offset

    def merge_data(self, time_window: float = 0.5) -> pd.DataFrame:
        """
        GPS 좌표에 LTE 및 Starlink 통신 품질 데이터를 병합

        Args:
            time_window: 매칭할 시간 윈도우 (초)
        """
        print(f"\n🔄 Merging flight data with communication quality...")

        # 시간 오프셋 계산
        time_offset = self.find_time_offset()

        # ULG 타임스탬프를 UTC로 변환
        self.flight_data['unix_timestamp'] = self.flight_data['time_sec'] + time_offset

        merged_records = []

        for _, flight_row in self.flight_data.iterrows():
            record = {
                'timestamp': flight_row['unix_timestamp'],
                'latitude': flight_row['latitude'],
                'longitude': flight_row['longitude'],
                'altitude': flight_row['altitude'],
            }

            # 가장 가까운 LTE 데이터 찾기
            lte_mask = np.abs(self.lte_data['unix_timestamp'] - flight_row['unix_timestamp']) < time_window
            if lte_mask.any():
                lte_closest = self.lte_data[lte_mask].iloc[0]
                record['lte_rssi'] = lte_closest['rssi']
                record['lte_rsrp'] = lte_closest['rsrp']
                record['lte_rsrq'] = lte_closest['rsrq']
                record['lte_sinr'] = lte_closest['sinr']
                record['lte_available'] = True
            else:
                record['lte_rssi'] = None
                record['lte_rsrp'] = None
                record['lte_rsrq'] = None
                record['lte_sinr'] = None
                record['lte_available'] = False

            # 가장 가까운 Starlink 데이터 찾기
            sl_mask = np.abs(self.starlink_data['unix_timestamp'] - flight_row['unix_timestamp']) < time_window
            if sl_mask.any():
                sl_closest = self.starlink_data[sl_mask].iloc[0]
                record['starlink_latency'] = sl_closest['ping_latency_ms']
                record['starlink_download'] = sl_closest['downlink_throughput_bps'] / 1e6  # Mbps
                record['starlink_upload'] = sl_closest['uplink_throughput_bps'] / 1e6  # Mbps
                record['starlink_snr'] = sl_closest['snr']
                record['starlink_azimuth'] = sl_closest['azimuth']
                record['starlink_elevation'] = sl_closest['elevation']
                record['starlink_gps_sats'] = sl_closest['gps_sats']
                record['starlink_available'] = True
            else:
                record['starlink_latency'] = None
                record['starlink_download'] = None
                record['starlink_upload'] = None
                record['starlink_snr'] = None
                record['starlink_azimuth'] = None
                record['starlink_elevation'] = None
                record['starlink_gps_sats'] = None
                record['starlink_available'] = False

            merged_records.append(record)

        merged_df = pd.DataFrame(merged_records)

        # 통계 출력
        lte_coverage = merged_df['lte_available'].sum() / len(merged_df) * 100
        sl_coverage = merged_df['starlink_available'].sum() / len(merged_df) * 100

        print(f"✓ Merged {len(merged_df)} flight points")
        print(f"  LTE coverage: {lte_coverage:.1f}%")
        print(f"  Starlink coverage: {sl_coverage:.1f}%")

        self.merged_data = merged_df
        return merged_df

    def get_statistics(self) -> Dict:
        """통신 품질 통계 계산"""
        if self.merged_data is None:
            raise ValueError("No merged data available. Run merge_data() first.")

        stats = {
            'flight': {
                'duration_sec': self.flight_data['time_sec'].max() - self.flight_data['time_sec'].min(),
                'total_points': len(self.merged_data),
                'distance_km': self._calculate_flight_distance(),
            },
            'lte': self._calculate_lte_stats(),
            'starlink': self._calculate_starlink_stats(),
        }

        return stats

    def _calculate_flight_distance(self) -> float:
        """비행 거리 계산 (km)"""
        from math import radians, sin, cos, sqrt, atan2

        total_distance = 0.0
        coords = self.merged_data[['latitude', 'longitude']].values

        for i in range(len(coords) - 1):
            lat1, lon1 = radians(coords[i][0]), radians(coords[i][1])
            lat2, lon2 = radians(coords[i+1][0]), radians(coords[i+1][1])

            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = 6371 * c  # Earth radius in km

            total_distance += distance

        return total_distance

    def _calculate_lte_stats(self) -> Dict:
        """LTE 통신 품질 통계"""
        lte_data = self.merged_data[self.merged_data['lte_available']]

        if len(lte_data) == 0:
            return {'available': False}

        return {
            'available': True,
            'coverage_percent': len(lte_data) / len(self.merged_data) * 100,
            'rssi': {
                'mean': lte_data['lte_rssi'].mean(),
                'min': lte_data['lte_rssi'].min(),
                'max': lte_data['lte_rssi'].max(),
                'std': lte_data['lte_rssi'].std(),
            },
            'rsrp': {
                'mean': lte_data['lte_rsrp'].mean(),
                'min': lte_data['lte_rsrp'].min(),
                'max': lte_data['lte_rsrp'].max(),
                'std': lte_data['lte_rsrp'].std(),
            },
            'sinr': {
                'mean': lte_data['lte_sinr'].mean(),
                'min': lte_data['lte_sinr'].min(),
                'max': lte_data['lte_sinr'].max(),
                'std': lte_data['lte_sinr'].std(),
            },
        }

    def _calculate_starlink_stats(self) -> Dict:
        """Starlink 통신 품질 통계"""
        sl_data = self.merged_data[self.merged_data['starlink_available']]

        if len(sl_data) == 0:
            return {'available': False}

        return {
            'available': True,
            'coverage_percent': len(sl_data) / len(self.merged_data) * 100,
            'latency_ms': {
                'mean': sl_data['starlink_latency'].mean(),
                'min': sl_data['starlink_latency'].min(),
                'max': sl_data['starlink_latency'].max(),
                'std': sl_data['starlink_latency'].std(),
            },
            'download_mbps': {
                'mean': sl_data['starlink_download'].mean(),
                'min': sl_data['starlink_download'].min(),
                'max': sl_data['starlink_download'].max(),
                'std': sl_data['starlink_download'].std(),
            },
            'upload_mbps': {
                'mean': sl_data['starlink_upload'].mean(),
                'min': sl_data['starlink_upload'].min(),
                'max': sl_data['starlink_upload'].max(),
                'std': sl_data['starlink_upload'].std(),
            },
        }

    def save_merged_data(self, output_path: str):
        """병합된 데이터를 CSV로 저장"""
        if self.merged_data is None:
            raise ValueError("No merged data available")

        self.merged_data.to_csv(output_path, index=False)
        print(f"\n💾 Saved merged data to: {output_path}")


def main():
    """테스트 실행"""
    print("=" * 60)
    print("FLIGHT DATA ANALYZER - TEST")
    print("=" * 60)

    # 경로 설정 (프로젝트 루트 기준)
    base_dir = Path(__file__).parent.parent
    ulg_path = base_dir / "resource/[1] RTL 비행로그_20260123_1600.ulg"
    lte_dir = base_dir / "resource"
    starlink_dir = base_dir / "resource"

    # 분석기 생성
    analyzer = FlightDataAnalyzer(ulg_path, lte_dir, starlink_dir)

    # 데이터 로드
    analyzer.load_ulg_data()
    analyzer.load_lte_data()
    analyzer.load_starlink_data()

    # 데이터 병합
    analyzer.merge_data(time_window=0.5)

    # 통계 계산
    stats = analyzer.get_statistics()

    print("\n" + "=" * 60)
    print("FLIGHT STATISTICS")
    print("=" * 60)
    print(f"Duration: {stats['flight']['duration_sec']:.2f} seconds")
    print(f"Total points: {stats['flight']['total_points']}")
    print(f"Distance: {stats['flight']['distance_km']:.3f} km")

    if stats['lte']['available']:
        print("\n" + "=" * 60)
        print("LTE QUALITY STATISTICS")
        print("=" * 60)
        print(f"Coverage: {stats['lte']['coverage_percent']:.1f}%")
        print(f"RSSI: {stats['lte']['rssi']['mean']:.1f} dBm (± {stats['lte']['rssi']['std']:.1f})")
        print(f"RSRP: {stats['lte']['rsrp']['mean']:.1f} dBm (± {stats['lte']['rsrp']['std']:.1f})")
        print(f"SINR: {stats['lte']['sinr']['mean']:.1f} dB (± {stats['lte']['sinr']['std']:.1f})")

    if stats['starlink']['available']:
        print("\n" + "=" * 60)
        print("STARLINK QUALITY STATISTICS")
        print("=" * 60)
        print(f"Coverage: {stats['starlink']['coverage_percent']:.1f}%")
        print(f"Latency: {stats['starlink']['latency_ms']['mean']:.1f} ms (± {stats['starlink']['latency_ms']['std']:.1f})")
        print(f"Download: {stats['starlink']['download_mbps']['mean']:.1f} Mbps (± {stats['starlink']['download_mbps']['std']:.1f})")
        print(f"Upload: {stats['starlink']['upload_mbps']['mean']:.1f} Mbps (± {stats['starlink']['upload_mbps']['std']:.1f})")

    # 병합 데이터 저장
    output_path = base_dir / "analysis/merged_flight_data.csv"
    analyzer.save_merged_data(str(output_path))


if __name__ == "__main__":
    main()
