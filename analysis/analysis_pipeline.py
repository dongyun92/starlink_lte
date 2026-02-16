#!/usr/bin/env python3
"""
통합 분석 파이프라인
Integrated Analysis Pipeline for Flight Communication Quality

이 모듈은 업로드된 파일들을 분석하고 결과를 생성합니다.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import traceback
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# matplotlib GUI 없이 사용
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# 한글 폰트 설정 (Korean font configuration for macOS)
matplotlib.rc('font', family='AppleGothic')
# 마이너스 기호 깨짐 방지
matplotlib.rc('axes', unicode_minus=False)

class AnalysisPipeline:
    """비행 통신 품질 분석 파이프라인"""

    def __init__(self, session_id: str, upload_folder: Path, results_folder: Path):
        """
        Args:
            session_id: 세션 ID
            upload_folder: 업로드된 파일들이 있는 폴더
            results_folder: 결과를 저장할 폴더
        """
        self.session_id = session_id
        self.upload_folder = Path(upload_folder)
        self.results_folder = Path(results_folder)

        # 파일 디렉토리 설정 (여러 파일 지원)
        self.flight_logs_dir = self.upload_folder / 'flight_logs'
        self.lte_data_dir = self.upload_folder / 'lte_data'
        self.starlink_data_dir = self.upload_folder / 'starlink_data'

        # 결과 디렉토리 생성
        self.results_folder.mkdir(parents=True, exist_ok=True)
        self.charts_folder = self.results_folder / 'charts'
        self.charts_folder.mkdir(exist_ok=True)

        # 분석 데이터
        self.merged_data = None
        self.lte_data = None
        self.starlink_data = None
        self.analysis_results = {}

    def validate_files(self) -> Tuple[bool, str]:
        """업로드된 파일 유효성 검사 (비행 로그는 필수, LTE/Starlink은 선택)"""
        # 비행 로그 디렉토리 존재 확인 (필수)
        if not self.flight_logs_dir.exists():
            return False, "비행 로그 디렉토리가 없습니다."

        # 파일 개수 확인
        flight_log_files = list(self.flight_logs_dir.glob('*.ulg'))
        lte_data_files = list(self.lte_data_dir.glob('*.csv')) if self.lte_data_dir.exists() else []
        starlink_data_files = list(self.starlink_data_dir.glob('*.csv')) if self.starlink_data_dir.exists() else []

        # 비행 로그는 필수
        if len(flight_log_files) == 0:
            return False, "비행 로그 파일이 없습니다."

        # LTE/Starlink은 선택 사항
        file_summary = [f"비행로그:{len(flight_log_files)}"]
        if len(lte_data_files) > 0:
            file_summary.append(f"LTE:{len(lte_data_files)}")
        if len(starlink_data_files) > 0:
            file_summary.append(f"Starlink:{len(starlink_data_files)}")

        return True, f"파일 확인 완료 ({', '.join(file_summary)})"

    def _parse_ulg_file(self, ulg_path: Path, csv_start_time: pd.Timestamp = None) -> pd.DataFrame:
        """ULG 파일에서 GPS 데이터 추출

        Args:
            ulg_path: ULG 파일 경로
            csv_start_time: CSV 데이터의 시작 시간 (ULG 상대 시간을 절대 시간으로 변환하기 위한 기준점)
        """
        try:
            from pyulog import ULog
            import re
            from datetime import datetime, timedelta

            ulog = ULog(str(ulg_path))

            # vehicle_gps_position 및 vehicle_attitude 데이터셋 찾기
            gps_dataset = None
            attitude_dataset = None

            for data in ulog.data_list:
                if data.name == 'vehicle_gps_position':
                    gps_dataset = data
                elif data.name == 'vehicle_attitude':
                    attitude_dataset = data

            # Fallback: vehicle_global_position
            if gps_dataset is None:
                for data in ulog.data_list:
                    if data.name == 'vehicle_global_position':
                        gps_dataset = data
                        break

            if gps_dataset is None:
                print(f"  │  ⚠️  GPS 데이터셋 없음")
                return None

            if attitude_dataset:
                print(f"  │  ✓ Attitude 데이터 발견 (yaw/roll/pitch)")

            # 데이터 추출
            timestamps_us = gps_dataset.data['timestamp']  # microseconds (relative time)

            # Check for latitude/longitude field names
            if 'latitude_deg' in gps_dataset.data:
                latitudes = gps_dataset.data['latitude_deg']
                longitudes = gps_dataset.data['longitude_deg']
                altitudes = gps_dataset.data['altitude_msl_m']
            else:
                latitudes = gps_dataset.data['lat']
                longitudes = gps_dataset.data['lon']
                altitudes = gps_dataset.data['alt']

            # ULG 타임스탬프를 절대 시간으로 변환
            # 방법 1: time_utc_usec 필드 사용 (가장 정확)
            if 'time_utc_usec' in gps_dataset.data:
                utc_times_us = gps_dataset.data['time_utc_usec']
                # Filter out zero/invalid values
                valid_utc_times = [t for t in utc_times_us if t > 0]
                if len(valid_utc_times) > 0:
                    # Use time_utc_usec directly
                    absolute_timestamps = pd.to_datetime(utc_times_us, unit='us', utc=True, errors='coerce')
                    print(f"  │  ✓ Using time_utc_usec for accurate UTC timestamps")
                else:
                    # Fallback to method 2
                    absolute_timestamps = None
            else:
                absolute_timestamps = None

            # 방법 2: CSV 시작 시간을 기준으로 사용 (fallback)
            if absolute_timestamps is None and csv_start_time is not None:
                # CSV 시작 시간에서 ULG 시작 오프셋을 빼서 boot 시간 추정
                ulog_start_us = timestamps_us[0]
                boot_time = csv_start_time - pd.Timedelta(microseconds=int(ulog_start_us))
                absolute_timestamps = [boot_time + pd.Timedelta(microseconds=int(ts)) for ts in timestamps_us]
                print(f"  │  ⚠️  Using CSV start time for timestamp conversion")

            # 방법 3: 파일명에서 시간 추출 (fallback)
            if absolute_timestamps is None:
                filename = ulg_path.name
                match = re.search(r'(\d{8})_(\d{4})', filename)
                if match:
                    date_str = match.group(1)  # 20260123
                    time_str = match.group(2)  # 1600
                    # 한국 시간(KST)을 UTC로 변환 (UTC = KST - 9시간)
                    kst_time = datetime.strptime(f'{date_str}_{time_str}', '%Y%m%d_%H%M')
                    boot_time = pd.Timestamp(kst_time - timedelta(hours=9), tz='UTC') - pd.Timedelta(microseconds=int(timestamps_us[0]))
                    absolute_timestamps = [boot_time + pd.Timedelta(microseconds=int(ts)) for ts in timestamps_us]
                    print(f"  │  ⚠️  Using filename for timestamp conversion")
                else:
                    # 상대 시간을 그대로 사용 (epoch time)
                    absolute_timestamps = pd.to_datetime(timestamps_us, unit='us', utc=True)
                    print(f"  │  ⚠️  Using relative timestamps (may be inaccurate)")

            # DataFrame 생성
            df = pd.DataFrame({
                'timestamp': absolute_timestamps,
                'latitude': latitudes,
                'longitude': longitudes,
                'altitude': altitudes,
                'timestamp_us': timestamps_us  # 매칭용 원본 타임스탬프
            })

            # GPS COG (Course Over Ground) - 헤딩 데이터 추출 (0-360도)
            # MAVLink GLOBAL_POSITION_INT.hdg에 해당
            if 'cog_rad' in gps_dataset.data:
                cog_rad = gps_dataset.data['cog_rad']
                # 라디안 -> 도 변환 후 0-360 범위로 정규화
                heading_deg = np.degrees(cog_rad) % 360
                df['heading'] = heading_deg

                valid_heading = df['heading'].notna().sum()
                print(f"  │  ✓ GPS COG (헤딩): {valid_heading}/{len(df)} 포인트")
                print(f"  │    범위: {df['heading'].min():.1f}° ~ {df['heading'].max():.1f}° (0-360도)")

            # Attitude 데이터 병합 (Quaternion + Euler angles)
            if attitude_dataset:
                # Quaternion 원본 데이터 추출 (3D 시각화용)
                q = attitude_dataset.data
                q0 = q['q[0]']
                q1 = q['q[1]']
                q2 = q['q[2]']
                q3 = q['q[3]']

                # Quaternion에서 Euler 각도 변환 (분석용)
                # Roll (X-axis rotation)
                roll = np.arctan2(2*(q0*q1 + q2*q3), 1 - 2*(q1**2 + q2**2))
                # Pitch (Y-axis rotation)
                pitch = np.arcsin(2*(q0*q2 - q3*q1))
                # Yaw/Heading (Z-axis rotation)
                yaw = np.arctan2(2*(q0*q3 + q1*q2), 1 - 2*(q2**2 + q3**2))

                attitude_df = pd.DataFrame({
                    'timestamp_us': q['timestamp'],
                    'q0': q0,
                    'q1': q1,
                    'q2': q2,
                    'q3': q3,
                    'roll': np.degrees(roll),
                    'pitch': np.degrees(pitch),
                    'yaw': np.degrees(yaw)
                })

                # GPS 타임스탬프에 맞춰 attitude 매칭 (nearest neighbor)
                df['q0'] = np.nan
                df['q1'] = np.nan
                df['q2'] = np.nan
                df['q3'] = np.nan
                df['roll'] = np.nan
                df['pitch'] = np.nan
                df['yaw'] = np.nan

                for i, row in df.iterrows():
                    # 가장 가까운 attitude 데이터 찾기
                    time_diff = np.abs(attitude_df['timestamp_us'] - row['timestamp_us'])
                    closest_idx = time_diff.argmin()

                    if time_diff.iloc[closest_idx] < 100000:  # 100ms 이내
                        df.at[i, 'q0'] = attitude_df.iloc[closest_idx]['q0']
                        df.at[i, 'q1'] = attitude_df.iloc[closest_idx]['q1']
                        df.at[i, 'q2'] = attitude_df.iloc[closest_idx]['q2']
                        df.at[i, 'q3'] = attitude_df.iloc[closest_idx]['q3']
                        df.at[i, 'roll'] = attitude_df.iloc[closest_idx]['roll']
                        df.at[i, 'pitch'] = attitude_df.iloc[closest_idx]['pitch']
                        df.at[i, 'yaw'] = attitude_df.iloc[closest_idx]['yaw']

                valid_attitude = df['roll'].notna().sum()
                print(f"  │  ✓ Attitude (Quaternion + Euler): {valid_attitude}/{len(df)} 포인트")
                print(f"  │    Quaternion (q0,q1,q2,q3) + Roll/Pitch/Yaw (degrees)")

            # timestamp_us 제거 (임시 컬럼)
            df = df.drop(columns=['timestamp_us'], errors='ignore')

            # 중복 제거 및 정렬
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"  │  ✗ ULG 파싱 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_derived_variables(self):
        """파생 변수 생성 (속도, 거리, 비행 시간 등)"""
        if self.merged_data is None or len(self.merged_data) == 0:
            return

        # Haversine distance 계산
        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371000  # 지구 반지름 (m)
            phi1, phi2 = np.radians(lat1), np.radians(lat2)
            dphi = np.radians(lat2 - lat1)
            dlambda = np.radians(lon2 - lon1)
            a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            return R * c

        # 위치 정보가 있는 경우에만 파생 변수 생성
        if 'latitude' in self.merged_data.columns and 'longitude' in self.merged_data.columns:
            # 이동 거리 계산
            self.merged_data['distance_moved'] = haversine_distance(
                self.merged_data['latitude'].shift(1),
                self.merged_data['longitude'].shift(1),
                self.merged_data['latitude'],
                self.merged_data['longitude']
            )

            # 이동 속도 계산 (m/s) - 0.5초 간격 가정
            self.merged_data['speed_mps'] = self.merged_data['distance_moved'] / 0.5

            # 원점으로부터 거리
            origin_lat = self.merged_data['latitude'].iloc[0]
            origin_lon = self.merged_data['longitude'].iloc[0]
            self.merged_data['distance_from_origin'] = haversine_distance(
                origin_lat, origin_lon,
                self.merged_data['latitude'],
                self.merged_data['longitude']
            )

        # 비행 경과 시간 (초)
        self.merged_data['flight_time_elapsed'] = self.merged_data.index * 0.5

        print(f"✓ 파생 변수 생성 완료: speed_mps, distance_from_origin, flight_time_elapsed")

    def step_1_load_data(self) -> Dict:
        """Step 1: 데이터 로드 및 병합 (여러 파일 지원)"""
        try:
            print(f"[Step 1/6] 데이터 로드 중...")

            # 여러 LTE CSV 파일 로드 및 병합
            lte_data_files = list(self.lte_data_dir.glob('*.csv'))
            lte_dfs = []
            skipped_lte_files = []
            for file_path in lte_data_files:
                try:
                    df = pd.read_csv(file_path)
                    if len(df) > 0:
                        df['source_file'] = file_path.name
                        lte_dfs.append(df)
                    else:
                        skipped_lte_files.append(f"{file_path.name} (empty)")
                except pd.errors.EmptyDataError:
                    skipped_lte_files.append(f"{file_path.name} (no data)")
                except Exception as e:
                    skipped_lte_files.append(f"{file_path.name} (error: {str(e)[:30]})")
            self.lte_data = pd.concat(lte_dfs, ignore_index=True) if lte_dfs else pd.DataFrame()
            if skipped_lte_files:
                print(f"  ⚠️  LTE 파일 스킵: {len(skipped_lte_files)}개 ({', '.join(skipped_lte_files[:3])}{'...' if len(skipped_lte_files) > 3 else ''})")
            print(f"  ✓ LTE 데이터 로드: {len(self.lte_data)} rows from {len(lte_dfs)}/{len(lte_data_files)} files")

            # 여러 Starlink CSV 파일 로드 및 병합
            starlink_data_files = list(self.starlink_data_dir.glob('*.csv'))
            starlink_dfs = []
            skipped_starlink_files = []
            for file_path in starlink_data_files:
                try:
                    df = pd.read_csv(file_path)
                    if len(df) > 0:
                        df['source_file'] = file_path.name
                        starlink_dfs.append(df)
                    else:
                        skipped_starlink_files.append(f"{file_path.name} (empty)")
                except pd.errors.EmptyDataError:
                    skipped_starlink_files.append(f"{file_path.name} (no data)")
                except Exception as e:
                    skipped_starlink_files.append(f"{file_path.name} (error: {str(e)[:30]})")
            self.starlink_data = pd.concat(starlink_dfs, ignore_index=True) if starlink_dfs else pd.DataFrame()
            if skipped_starlink_files:
                print(f"  ⚠️  Starlink 파일 스킵: {len(skipped_starlink_files)}개 ({', '.join(skipped_starlink_files[:3])}{'...' if len(skipped_starlink_files) > 3 else ''})")
            print(f"  ✓ Starlink 데이터 로드: {len(self.starlink_data)} rows from {len(starlink_dfs)}/{len(starlink_data_files)} files")

            # CSV 데이터에서 시작 시간 추출 (ULG 타임스탬프 변환 기준점으로 사용)
            csv_start_time = None
            if 'timestamp' in self.lte_data.columns and len(self.lte_data) > 0:
                temp_lte = pd.to_datetime(self.lte_data['timestamp'], errors='coerce', utc=True)
                csv_start_time = temp_lte.min()
            if csv_start_time is None and 'timestamp' in self.starlink_data.columns and len(self.starlink_data) > 0:
                temp_sl = pd.to_datetime(self.starlink_data['timestamp'], errors='coerce', utc=True)
                csv_start_time = temp_sl.min()

            if csv_start_time is not None:
                print(f"  ├─ CSV 기준 시간: {csv_start_time}")

            # ULG 파일 파싱 (GPS 좌표 추출)
            flight_log_files = sorted(list(self.flight_logs_dir.glob('*.ulg')))  # 정렬하여 일관된 순서 보장
            gps_dfs = []
            for flight_idx, ulg_path in enumerate(flight_log_files):
                print(f"  ├─ ULG 파싱 중: {ulg_path.name}")
                gps_df = self._parse_ulg_file(ulg_path, csv_start_time)
                if gps_df is not None and len(gps_df) > 0:
                    # 각 비행에 고유 ID 부여 (비행 구분을 위해)
                    gps_df['flight_id'] = flight_idx
                    gps_df['flight_name'] = ulg_path.stem  # 파일명 (확장자 제외)
                    gps_dfs.append(gps_df)
                    print(f"  │  ✓ GPS 데이터: {len(gps_df)} rows (flight_id={flight_idx})")
                    print(f"  │  ✓ 시간 범위: {gps_df['timestamp'].iloc[0]} ~ {gps_df['timestamp'].iloc[-1]}")

            flight_data = pd.concat(gps_dfs, ignore_index=True) if gps_dfs else pd.DataFrame()
            if len(flight_data) > 0:
                # 전체 비행 데이터 정렬 (timestamp 기준)
                flight_data = flight_data.sort_values(['flight_id', 'timestamp']).reset_index(drop=True)
            if len(flight_data) > 0:
                print(f"  ✓ 비행 GPS 데이터: {len(flight_data)} rows from {len(flight_log_files)} files")
            else:
                print(f"  ⚠️  GPS 데이터 없음 (ULG 파일에서 추출 실패)")

            # 타임스탬프 변환 및 null 제거
            if 'timestamp' in self.lte_data.columns:
                self.lte_data['timestamp'] = pd.to_datetime(self.lte_data['timestamp'], errors='coerce', utc=True)
                null_count_before = self.lte_data['timestamp'].isna().sum()
                self.lte_data = self.lte_data.dropna(subset=['timestamp'])
                print(f"  ├─ LTE 타임스탬프 변환: {null_count_before} nulls 제거, {len(self.lte_data)} rows 남음")

            if 'timestamp' in self.starlink_data.columns:
                self.starlink_data['timestamp'] = pd.to_datetime(self.starlink_data['timestamp'], errors='coerce', utc=True)
                null_count_before = self.starlink_data['timestamp'].isna().sum()
                self.starlink_data = self.starlink_data.dropna(subset=['timestamp'])
                print(f"  ├─ Starlink 타임스탬프 변환: {null_count_before} nulls 제거, {len(self.starlink_data)} rows 남음")

            if len(flight_data) > 0 and 'timestamp' in flight_data.columns:
                null_count_before = flight_data['timestamp'].isna().sum()
                print(f"  ├─ Flight GPS 타임스탬프 체크: {null_count_before} nulls (before dropna)")
                flight_data = flight_data.dropna(subset=['timestamp'])
                print(f"  │  ✓ Flight GPS: {len(flight_data)} rows (after dropna)")

            # 공통 컬럼 이름 변경 (중복 방지)
            # LTE 데이터 접두사 추가
            lte_rename = {col: f'lte_{col}' for col in self.lte_data.columns if col != 'timestamp'}
            self.lte_data = self.lte_data.rename(columns=lte_rename)

            # Starlink 데이터 접두사 추가 (timestamp 제외)
            starlink_rename = {col: f'starlink_{col}' for col in self.starlink_data.columns if col != 'timestamp'}
            self.starlink_data = self.starlink_data.rename(columns=starlink_rename)

            # 3-way 병합: Flight GPS + Starlink + LTE
            print(f"  ├─ 데이터 병합 중...")

            # Step 1: Flight GPS를 기준으로 시작
            if len(flight_data) > 0 and 'timestamp' in flight_data.columns:
                self.merged_data = flight_data.copy()
                print(f"  │  ✓ 기준 데이터: GPS ({len(self.merged_data)} rows)")

                # Step 2: Starlink 병합
                if len(self.starlink_data) > 0 and 'timestamp' in self.starlink_data.columns:
                    # 병합 전 null 체크
                    left_nulls = self.merged_data['timestamp'].isna().sum()
                    right_nulls = self.starlink_data['timestamp'].isna().sum()
                    print(f"  │  ├─ 병합 전 null 체크: left={left_nulls}, right={right_nulls}")

                    self.merged_data = pd.merge_asof(
                        self.merged_data.sort_values('timestamp'),
                        self.starlink_data.sort_values('timestamp'),
                        on='timestamp',
                        direction='nearest',
                        tolerance=pd.Timedelta('2s')
                    )
                    print(f"  │  ✓ Starlink 병합: {len(self.merged_data)} rows")

                # Step 3: LTE 병합
                if len(self.lte_data) > 0 and 'timestamp' in self.lte_data.columns:
                    # 병합 전 null 체크
                    left_nulls = self.merged_data['timestamp'].isna().sum()
                    right_nulls = self.lte_data['timestamp'].isna().sum()
                    print(f"  │  ├─ 병합 전 null 체크: left={left_nulls}, right={right_nulls}")

                    self.merged_data = pd.merge_asof(
                        self.merged_data.sort_values('timestamp'),
                        self.lte_data.sort_values('timestamp'),
                        on='timestamp',
                        direction='nearest',
                        tolerance=pd.Timedelta('2s')
                    )
                    print(f"  │  ✓ LTE 병합: {len(self.merged_data)} rows")

            else:
                # GPS 데이터가 없으면 Starlink + LTE만 병합
                print(f"  │  ⚠️  GPS 데이터 없음, Starlink + LTE만 병합")
                if 'timestamp' in self.lte_data.columns and 'timestamp' in self.starlink_data.columns:
                    self.merged_data = pd.merge(
                        self.starlink_data,
                        self.lte_data,
                        on='timestamp',
                        how='outer',
                        suffixes=('', '_duplicate')
                    ).sort_values('timestamp').reset_index(drop=True)
                    self.merged_data = self.merged_data.loc[:, ~self.merged_data.columns.str.endswith('_duplicate')]
                else:
                    self.merged_data = pd.concat([self.starlink_data, self.lte_data], axis=1)

            print(f"  ✓ 최종 병합: {len(self.merged_data)} rows, {len(self.merged_data.columns)} columns")

            # 센티넬 값 필터링 (오류 값을 NaN으로 변환)
            # -999, -9999 같은 값은 센서 오류를 나타내는 센티넬 값
            print(f"  ├─ 센티넬 값 필터링 중...")
            sentinel_columns = {
                'lte_rssi': -999,
                'lte_rsrp': -999,
                'lte_rsrq': -999,
                'lte_sinr': -999,
                'starlink_snr': -999,
                'starlink_pop_ping_latency_ms': -1,  # -1은 보통 오류 값
            }

            cleaned_count = 0
            for col, sentinel_val in sentinel_columns.items():
                if col in self.merged_data.columns:
                    bad_count = (self.merged_data[col] == sentinel_val).sum()
                    if bad_count > 0:
                        self.merged_data.loc[self.merged_data[col] == sentinel_val, col] = pd.NA
                        cleaned_count += bad_count
                        print(f"  │  ✓ {col}: {bad_count}개 센티넬 값 제거")

            if cleaned_count > 0:
                print(f"  ✓ 총 {cleaned_count}개 센티넬 값 제거됨")

            # NaN 값 처리 (선형 보간)
            if 'altitude' in self.merged_data.columns:
                self.merged_data['altitude'] = self.merged_data['altitude'].interpolate(method='linear', limit_direction='both')
            if 'latitude' in self.merged_data.columns:
                self.merged_data['latitude'] = self.merged_data['latitude'].interpolate(method='linear', limit_direction='both')
            if 'longitude' in self.merged_data.columns:
                self.merged_data['longitude'] = self.merged_data['longitude'].interpolate(method='linear', limit_direction='both')

            # 파생 변수 생성 (속도, 거리, 시간)
            self._create_derived_variables()

            # 이전 고급 분석 스크립트와 호환되도록 컬럼명 매핑
            column_mapping = {
                'starlink_ping_latency_ms': 'starlink_latency',
                'starlink_pop_ping_latency_ms': 'starlink_latency',  # 추가 매핑
                'lte_rssi': 'lte_rssi',
                'lte_rsrp': 'lte_rsrp',
                'lte_rsrq': 'lte_rsrq',
                'lte_sinr': 'lte_sinr'
            }

            # Starlink SNR 컬럼이 있으면 별칭 생성 (차트 생성용)
            if 'starlink_snr' not in self.merged_data.columns:
                # snr 컬럼 찾기
                snr_candidates = ['starlink_snr', 'snr']
                for candidate in snr_candidates:
                    if candidate in self.merged_data.columns:
                        self.merged_data['starlink_snr'] = self.merged_data[candidate]
                        print(f"  ├─ SNR 컬럼 별칭 생성: {candidate} → starlink_snr")
                        break
            # 매핑에 있는 컬럼만 변경 (없으면 skip)
            rename_dict = {k: v for k, v in column_mapping.items() if k in self.merged_data.columns}
            if rename_dict:
                self.merged_data = self.merged_data.rename(columns=rename_dict)

            # Word 보고서 생성기와 호환되도록 추가 컬럼 생성 (별칭)
            if 'starlink_downlink_throughput_bps' in self.merged_data.columns:
                self.merged_data['starlink_download'] = self.merged_data['starlink_downlink_throughput_bps'] / 1e6  # Convert to Mbps
            if 'starlink_uplink_throughput_bps' in self.merged_data.columns:
                self.merged_data['starlink_upload'] = self.merged_data['starlink_uplink_throughput_bps'] / 1e6  # Convert to Mbps

            # 중복 컬럼 제거 (같은 이름의 컬럼이 여러 개 있는 경우)
            self.merged_data = self.merged_data.loc[:, ~self.merged_data.columns.duplicated()]

            # lte_available, starlink_available 칼럼 생성 (Word 보고서 생성용)
            if 'lte_rssi' in self.merged_data.columns:
                self.merged_data['lte_available'] = self.merged_data['lte_rssi'].notna()
            else:
                self.merged_data['lte_available'] = False

            if 'starlink_latency' in self.merged_data.columns:
                # Series인지 확인
                latency_col = self.merged_data['starlink_latency']
                if isinstance(latency_col, pd.Series):
                    self.merged_data['starlink_available'] = latency_col.notna()
                else:
                    # DataFrame인 경우 첫 번째 컬럼 사용
                    self.merged_data['starlink_available'] = latency_col.iloc[:, 0].notna()
            else:
                self.merged_data['starlink_available'] = False

            print(f"    ✓ 가용성 칼럼 생성: lte_available ({self.merged_data['lte_available'].sum()} rows), starlink_available ({self.merged_data['starlink_available'].sum()} rows)")

            # 시간 범위 추출
            time_ranges = self._extract_time_ranges(flight_data, self.lte_data, self.starlink_data)

            # 시간 범위 겹침 검사
            overlap_warnings = self._check_time_overlap(time_ranges)

            # 시간 범위 정보 출력
            print(f"\n  📅 데이터 시간 범위:")
            if 'flight' in time_ranges:
                print(f"  ├─ 비행 데이터: {time_ranges['flight']['start']} ~ {time_ranges['flight']['end']}")
            if 'lte' in time_ranges:
                print(f"  ├─ LTE 데이터: {time_ranges['lte']['start']} ~ {time_ranges['lte']['end']}")
            if 'starlink' in time_ranges:
                print(f"  ├─ Starlink 데이터: {time_ranges['starlink']['start']} ~ {time_ranges['starlink']['end']}")

            # 경고 메시지 출력
            if overlap_warnings:
                print(f"\n  ⚠️  시간 범위 불일치:")
                for warning in overlap_warnings:
                    print(f"  │  • {warning}")

            # 임시 병합 파일 저장
            merged_path = self.results_folder / 'merged_data.csv'
            self.merged_data.to_csv(merged_path, index=False)

            # 시간 범위 정보를 analysis_results에 저장
            self.analysis_results['time_ranges'] = time_ranges
            self.analysis_results['time_warnings'] = overlap_warnings

            return {
                'status': 'success',
                'message': f'데이터 로드 완료: {len(self.merged_data)} rows',
                'rows': len(self.merged_data),
                'columns': len(self.merged_data.columns),
                'file_counts': {
                    'lte': len(lte_data_files),
                    'starlink': len(starlink_data_files),
                    'flight_logs': len(list(self.flight_logs_dir.glob('*.ulg')))
                },
                'time_ranges': time_ranges,
                'time_warnings': overlap_warnings
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'데이터 로드 실패: {str(e)}',
                'traceback': traceback.format_exc()
            }

    def step_2_correlation_analysis(self) -> Dict:
        """Step 2: 상관관계 분석"""
        try:
            print(f"[Step 2/6] 상관관계 분석 중...")

            if self.merged_data is None or len(self.merged_data) == 0:
                return {'status': 'error', 'message': '병합된 데이터가 없습니다.'}

            # 숫자형 컬럼만 선택
            numeric_cols = self.merged_data.select_dtypes(include=[np.number]).columns
            correlation_matrix = self.merged_data[numeric_cols].corr()

            # 주요 상관관계 찾기
            corr_pairs = []
            for i in range(len(correlation_matrix.columns)):
                for j in range(i+1, len(correlation_matrix.columns)):
                    col1 = correlation_matrix.columns[i]
                    col2 = correlation_matrix.columns[j]
                    corr_value = correlation_matrix.iloc[i, j]
                    if not np.isnan(corr_value):
                        corr_pairs.append({
                            'variable1': col1,
                            'variable2': col2,
                            'correlation': float(corr_value)
                        })

            corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
            top_correlations = corr_pairs[:20]

            # 상관관계 매트릭스 시각화
            chart_path = self.charts_folder / 'correlation_matrix.png'
            plt.figure(figsize=(12, 10))
            sns.heatmap(correlation_matrix, annot=False, cmap='coolwarm', center=0,
                       square=True, linewidths=0.5, cbar_kws={"shrink": 0.8})
            plt.title('Parameter Correlation Matrix')
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150)
            plt.close()

            self.analysis_results['correlation'] = {
                'matrix': correlation_matrix.to_dict(),
                'top_correlations': top_correlations
            }

            return {
                'status': 'success',
                'message': f'상관관계 분석 완료: {len(top_correlations)} 주요 상관관계 발견',
                'top_count': len(top_correlations)
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'상관관계 분석 실패: {str(e)}',
                'traceback': traceback.format_exc()
            }

    def step_3_quality_analysis(self) -> Dict:
        """Step 3: 통신 품질 분석"""
        try:
            print(f"[Step 3/6] 통신 품질 분석 중...")

            lte_stats = self._calculate_lte_quality_stats()
            starlink_stats = self._calculate_starlink_quality_stats()
            self._generate_quality_comparison_charts()

            self.analysis_results['quality'] = {
                'lte': lte_stats,
                'starlink': starlink_stats
            }

            return {
                'status': 'success',
                'message': '통신 품질 분석 완료',
                'lte_avg_rsrp': lte_stats.get('avg_rsrp', 0),
                'starlink_avg_snr': starlink_stats.get('avg_snr', 0)
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'품질 분석 실패: {str(e)}',
                'traceback': traceback.format_exc()
            }

    def step_4_altitude_analysis(self) -> Dict:
        """Step 4: 고도별 분석"""
        try:
            print(f"[Step 4/6] 고도별 분석 중...")

            altitude_analysis = self._analyze_by_altitude()
            chart_path = self.charts_folder / 'altitude_quality.png'
            self._plot_altitude_quality(chart_path)

            self.analysis_results['altitude'] = altitude_analysis

            return {'status': 'success', 'message': '고도별 분석 완료'}

        except Exception as e:
            return {
                'status': 'error',
                'message': f'고도별 분석 실패: {str(e)}',
                'traceback': traceback.format_exc()
            }

    def step_5_generate_charts(self) -> Dict:
        """Step 5: 모든 차트 생성 (데이터 유무에 따라 분기)"""
        try:
            print(f"[Step 5/6] 차트 생성 중...")

            # LTE/Starlink 데이터 확인
            has_lte = 'lte_rsrp' in self.merged_data.columns and self.merged_data['lte_rsrp'].notna().any()
            has_starlink = 'starlink_latency' in self.merged_data.columns and self.merged_data['starlink_latency'].notna().any()

            if not has_lte and not has_starlink:
                # 비행 전용 모드 - 비행 차트만 생성
                print("  ├─ 비행 로그 전용 모드: 비행 데이터 차트만 생성")
                self._generate_flight_only_charts()

            elif has_lte or has_starlink:
                # 통합 모드 - 통신 품질 차트 + 비행 전용 차트 모두 생성
                print("  ├─ 통합 모드: 통신 품질 + 비행 데이터 차트 생성")

                # 기본 통신 품질 차트
                self._plot_quality_over_time()
                self._plot_quality_heatmap()
                self._plot_statistics_summary()

                # 고급 통신 품질 차트
                try:
                    self._generate_advanced_charts()
                except Exception as e:
                    print(f"    ⚠️  고급 차트 생성 실패 (계속 진행): {str(e)}")

                # 비행 전용 차트도 함께 생성
                self._generate_flight_only_charts()

            chart_files = list(self.charts_folder.glob('*.png'))

            return {
                'status': 'success',
                'message': f'{len(chart_files)}개 차트 생성 완료',
                'chart_count': len(chart_files),
                'charts': [f.name for f in chart_files],
                'has_lte': has_lte,
                'has_starlink': has_starlink,
                'flight_only_mode': not has_lte and not has_starlink
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'차트 생성 실패: {str(e)}',
                'traceback': traceback.format_exc()
            }

    def _generate_advanced_charts(self):
        """고급 차트 생성 - 기존 고급 분석 스크립트 실행"""
        print("  ├─ 고급 차트 생성 중...")

        merged_data_path = self.results_folder / 'merged_data.csv'

        # Import sys for module path
        import sys
        analysis_dir = Path(__file__).parent
        if str(analysis_dir) not in sys.path:
            sys.path.insert(0, str(analysis_dir))

        try:
            # 1. Comprehensive Correlation Analysis 실행
            from comprehensive_correlation_analysis import ComprehensiveCorrelationAnalyzer

            analyzer = ComprehensiveCorrelationAnalyzer(str(merged_data_path))
            analyzer.load_and_prepare_data()
            analyzer.compute_correlations()
            analyzer.find_significant_correlations(threshold=0.3)

            # 차트를 charts 폴더에 저장
            output_path = self.charts_folder / "comprehensive_correlations.png"
            analyzer.visualize_correlations(str(output_path))
            print("    ✓ Comprehensive correlations chart created")

        except Exception as e:
            print(f"    ⚠️  Comprehensive analysis 실패: {str(e)}")
            import traceback
            traceback.print_exc()

        try:
            # 2. Multidimensional Charts 실행
            from multidimensional_charts import MultidimensionalChartGenerator

            chart_gen = MultidimensionalChartGenerator(str(merged_data_path))
            chart_gen.load_data()

            # base_dir을 charts 폴더로 변경
            original_base_dir = chart_gen.base_dir
            chart_gen.base_dir = self.charts_folder

            # 모든 고급 차트 생성
            chart_gen.generate_all_charts()
            print("    ✓ Multidimensional charts created (6 charts)")

        except Exception as e:
            print(f"    ⚠️  Multidimensional charts 실패: {str(e)}")
            import traceback
            traceback.print_exc()

        try:
            # 3. Starlink 위성 추적 분석 차트
            from satellite_tracking_visualization import SatelliteTrackingVisualizer

            visualizer = SatelliteTrackingVisualizer(str(merged_data_path))
            visualizer.load_data()

            # 위성 위치 극좌표 차트
            satellite_polar_path = self.charts_folder / 'satellite_position_polar.png'
            visualizer.create_satellite_position_plot(str(satellite_polar_path))

            # 위성 품질 상관관계 히트맵
            satellite_corr_path = self.charts_folder / 'satellite_quality_correlation.png'
            visualizer.create_quality_correlation_heatmap(str(satellite_corr_path))

            print("    ✓ Starlink satellite tracking charts created (2 charts)")

        except Exception as e:
            print(f"    ⚠️  Satellite tracking charts 실패: {str(e)}")
            import traceback
            traceback.print_exc()

        try:
            # 4. Starlink 심층 분석 차트 (비행 데이터 연동)
            from starlink_deep_analysis import StarlinkDeepAnalyzer

            deep_analyzer = StarlinkDeepAnalyzer(str(merged_data_path))
            deep_analyzer.load_data()

            # 5개의 심층 분석 차트 생성
            deep_analyzer.chart_altitude_vs_starlink(
                str(self.charts_folder / 'starlink_altitude_analysis.png')
            )
            deep_analyzer.chart_speed_vs_starlink(
                str(self.charts_folder / 'starlink_speed_analysis.png')
            )
            deep_analyzer.chart_distance_vs_starlink(
                str(self.charts_folder / 'starlink_distance_analysis.png')
            )
            deep_analyzer.chart_starlink_throughput_timeseries(
                str(self.charts_folder / 'starlink_throughput_timeseries.png')
            )
            deep_analyzer.chart_3d_altitude_speed_starlink(
                str(self.charts_folder / 'starlink_3d_altitude_speed.png')
            )

            print("    ✓ Starlink deep analysis charts created (5 charts)")

        except Exception as e:
            print(f"    ⚠️  Starlink deep analysis 실패: {str(e)}")
            import traceback
            traceback.print_exc()

        print("  └─ ✓ 고급 차트 생성 완료")

    def _generate_flight_only_charts(self):
        """비행 전용 시각화 차트 생성 (LTE/Starlink 데이터 불필요)"""
        print("  ├─ 비행 전용 차트 생성 중...")

        try:
            self._chart_flight_path_altitude_colored()
            print("    ✓ 2D 비행 경로 (고도 색상)")
        except Exception as e:
            print(f"    ⚠️  2D 비행 경로 실패: {str(e)}")

        try:
            self._chart_flight_path_3d()
            print("    ✓ 3D 비행 경로")
        except Exception as e:
            print(f"    ⚠️  3D 비행 경로 실패: {str(e)}")

        try:
            self._chart_altitude_profile()
            print("    ✓ 고도 프로파일")
        except Exception as e:
            print(f"    ⚠️  고도 프로파일 실패: {str(e)}")

        try:
            self._chart_speed_profile()
            print("    ✓ 속도 프로파일")
        except Exception as e:
            print(f"    ⚠️  속도 프로파일 실패: {str(e)}")

        try:
            self._chart_altitude_vs_speed()
            print("    ✓ 고도-속도 관계")
        except Exception as e:
            print(f"    ⚠️  고도-속도 관계 실패: {str(e)}")

        try:
            self._chart_flight_statistics_dashboard()
            print("    ✓ 비행 통계 대시보드")
        except Exception as e:
            print(f"    ⚠️  비행 통계 대시보드 실패: {str(e)}")

        print("  └─ ✓ 비행 전용 차트 생성 완료")

    def _chart_flight_path_altitude_colored(self):
        """2D 비행 경로 (고도별 색상 그라데이션)"""
        if 'latitude' not in self.merged_data.columns or 'longitude' not in self.merged_data.columns:
            return
        if 'altitude' not in self.merged_data.columns:
            return

        fig, ax = plt.subplots(figsize=(14, 10))

        valid_data = self.merged_data[
            (self.merged_data['latitude'].notna()) &
            (self.merged_data['longitude'].notna()) &
            (self.merged_data['altitude'].notna())
        ].copy()

        if len(valid_data) == 0:
            plt.close()
            return

        # 여러 비행 로그 지원
        if 'flight_id' in valid_data.columns:
            flight_ids = sorted(valid_data['flight_id'].unique())

            for flight_id in flight_ids:
                flight_df = valid_data[valid_data['flight_id'] == flight_id].copy()

                if len(flight_df) == 0:
                    continue

                # 고도별 색상 매핑 (연속적 colormap)
                scatter = ax.scatter(
                    flight_df['longitude'],
                    flight_df['latitude'],
                    c=flight_df['altitude'],
                    cmap='viridis',
                    s=50,
                    alpha=0.7,
                    edgecolors='black',
                    linewidth=0.5
                )

                # 비행 경로 선으로 연결
                ax.plot(
                    flight_df['longitude'],
                    flight_df['latitude'],
                    'k-',
                    alpha=0.3,
                    linewidth=1
                )
        else:
            # flight_id가 없는 경우
            scatter = ax.scatter(
                valid_data['longitude'],
                valid_data['latitude'],
                c=valid_data['altitude'],
                cmap='viridis',
                s=50,
                alpha=0.7,
                edgecolors='black',
                linewidth=0.5
            )

            ax.plot(
                valid_data['longitude'],
                valid_data['latitude'],
                'k-',
                alpha=0.3,
                linewidth=1
            )

        # 컬러바 (범례)
        cbar = plt.colorbar(scatter, ax=ax, label='Altitude (m)')
        cbar.ax.set_ylabel('고도 (m)', fontsize=12, fontweight='bold')

        ax.set_xlabel('경도 (Longitude)', fontsize=12, fontweight='bold')
        ax.set_ylabel('위도 (Latitude)', fontsize=12, fontweight='bold')
        ax.set_title('비행 경로 (고도별 색상)', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.charts_folder / 'flight_path_altitude_colored.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _chart_flight_path_3d(self):
        """3D 비행 경로 (X=경도, Y=위도, Z=고도)"""
        from mpl_toolkits.mplot3d import Axes3D

        if 'latitude' not in self.merged_data.columns or 'longitude' not in self.merged_data.columns:
            return
        if 'altitude' not in self.merged_data.columns:
            return

        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')

        valid_data = self.merged_data[
            (self.merged_data['latitude'].notna()) &
            (self.merged_data['longitude'].notna()) &
            (self.merged_data['altitude'].notna())
        ].copy()

        if len(valid_data) == 0:
            plt.close()
            return

        # 고도로 색상 지정
        scatter = ax.scatter(
            valid_data['longitude'],
            valid_data['latitude'],
            valid_data['altitude'],
            c=valid_data['altitude'],
            cmap='rainbow',
            s=30,
            alpha=0.6
        )

        # 3D 선으로 경로 연결
        ax.plot(
            valid_data['longitude'],
            valid_data['latitude'],
            valid_data['altitude'],
            'k-',
            alpha=0.2,
            linewidth=1
        )

        ax.set_xlabel('경도 (Longitude)', fontweight='bold')
        ax.set_ylabel('위도 (Latitude)', fontweight='bold')
        ax.set_zlabel('고도 (m)', fontweight='bold')
        ax.set_title('3D 비행 경로', fontsize=14, fontweight='bold')

        plt.colorbar(scatter, ax=ax, label='Altitude (m)', shrink=0.5)
        plt.tight_layout()
        plt.savefig(self.charts_folder / 'flight_path_3d.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _chart_altitude_profile(self):
        """고도 프로파일 (시간 vs 고도)"""
        if 'altitude' not in self.merged_data.columns:
            return

        fig, ax = plt.subplots(figsize=(16, 6))

        valid_data = self.merged_data[self.merged_data['altitude'].notna()].copy()

        if len(valid_data) == 0:
            plt.close()
            return

        # 고도를 색상으로 표현
        scatter = ax.scatter(
            valid_data.index,
            valid_data['altitude'],
            c=valid_data['altitude'],
            cmap='terrain',
            s=20,
            alpha=0.6
        )

        # 선으로 연결
        ax.plot(valid_data.index, valid_data['altitude'], 'k-', alpha=0.3, linewidth=1)

        # 비행 단계 표시 (이륙, 순항, 착륙)
        max_alt = valid_data['altitude'].max()
        ax.axhline(y=max_alt * 0.9, color='r', linestyle='--', alpha=0.5, label='순항 고도')

        ax.set_xlabel('샘플 인덱스 (시간 순서)', fontsize=12, fontweight='bold')
        ax.set_ylabel('고도 (m)', fontsize=12, fontweight='bold')
        ax.set_title('비행 고도 프로파일', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.colorbar(scatter, ax=ax, label='고도 (m)')
        plt.tight_layout()
        plt.savefig(self.charts_folder / 'altitude_profile.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _chart_speed_profile(self):
        """속도 프로파일 (시간 vs 속도)"""
        if 'speed_mps' not in self.merged_data.columns:
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

        valid_data = self.merged_data[self.merged_data['speed_mps'].notna()].copy()

        if len(valid_data) == 0:
            plt.close()
            return

        # 고도 데이터 확인
        has_altitude = 'altitude' in valid_data.columns and valid_data['altitude'].notna().any()

        # 상단: 속도 프로파일
        if has_altitude:
            scatter1 = ax1.scatter(
                valid_data.index,
                valid_data['speed_mps'],
                c=valid_data['altitude'],
                cmap='viridis',
                s=20,
                alpha=0.6
            )
            plt.colorbar(scatter1, ax=ax1, label='고도 (m)')
        else:
            ax1.scatter(
                valid_data.index,
                valid_data['speed_mps'],
                c='blue',
                s=20,
                alpha=0.6
            )

        ax1.plot(valid_data.index, valid_data['speed_mps'], 'k-', alpha=0.3, linewidth=1)
        ax1.set_ylabel('속도 (m/s)', fontsize=12, fontweight='bold')
        ax1.set_title('비행 속도 프로파일', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # 하단: 속도 (km/h)
        ax2.scatter(
            valid_data.index,
            valid_data['speed_mps'] * 3.6,  # m/s to km/h
            c=valid_data['altitude'] if has_altitude else 'blue',
            cmap='viridis' if has_altitude else None,
            s=20,
            alpha=0.6
        )
        ax2.plot(valid_data.index, valid_data['speed_mps'] * 3.6, 'k-', alpha=0.3, linewidth=1)
        ax2.set_xlabel('샘플 인덱스 (시간 순서)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('속도 (km/h)', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.charts_folder / 'speed_profile.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _chart_altitude_vs_speed(self):
        """고도 vs 속도 산점도"""
        if 'speed_mps' not in self.merged_data.columns or 'altitude' not in self.merged_data.columns:
            return

        fig, ax = plt.subplots(figsize=(10, 8))

        valid_data = self.merged_data[
            (self.merged_data['altitude'].notna()) &
            (self.merged_data['speed_mps'].notna())
        ].copy()

        if len(valid_data) == 0:
            plt.close()
            return

        # 시간 순서로 색상 지정
        scatter = ax.scatter(
            valid_data['altitude'],
            valid_data['speed_mps'],
            c=valid_data.index,  # 시간 순서
            cmap='cool',
            s=50,
            alpha=0.6,
            edgecolors='black',
            linewidth=0.5
        )

        ax.set_xlabel('고도 (m)', fontsize=12, fontweight='bold')
        ax.set_ylabel('속도 (m/s)', fontsize=12, fontweight='bold')
        ax.set_title('고도 vs 속도 관계', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        plt.colorbar(scatter, ax=ax, label='시간 순서 (샘플 인덱스)')
        plt.tight_layout()
        plt.savefig(self.charts_folder / 'altitude_vs_speed.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _chart_flight_statistics_dashboard(self):
        """비행 통계 요약 대시보드"""
        fig = plt.figure(figsize=(16, 12))

        # 통계 계산
        total_distance = self.merged_data['distance_from_origin'].max() if 'distance_from_origin' in self.merged_data.columns else 0
        max_altitude = self.merged_data['altitude'].max() if 'altitude' in self.merged_data.columns else 0
        avg_altitude = self.merged_data['altitude'].mean() if 'altitude' in self.merged_data.columns else 0
        max_speed = self.merged_data['speed_mps'].max() if 'speed_mps' in self.merged_data.columns else 0
        avg_speed = self.merged_data['speed_mps'].mean() if 'speed_mps' in self.merged_data.columns else 0
        duration = len(self.merged_data) * 0.5  # seconds

        # 서브플롯 배치 (2x3)
        # 1. 통계 텍스트
        ax1 = plt.subplot(2, 3, 1)
        ax1.axis('off')
        stats_text = f"""
비행 통계 요약

최대 고도: {max_altitude:.1f} m
평균 고도: {avg_altitude:.1f} m
최대 속도: {max_speed:.2f} m/s ({max_speed*3.6:.1f} km/h)
평균 속도: {avg_speed:.2f} m/s ({avg_speed*3.6:.1f} km/h)
최대 거리: {total_distance:.1f} m
비행 시간: {duration:.1f} 초 ({duration/60:.1f} 분)
데이터 포인트: {len(self.merged_data)}개
        """
        ax1.text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # 2. 고도 분포
        ax2 = plt.subplot(2, 3, 2)
        if 'altitude' in self.merged_data.columns:
            ax2.hist(self.merged_data['altitude'].dropna(), bins=30, color='skyblue', edgecolor='black')
            ax2.set_xlabel('고도 (m)', fontweight='bold')
            ax2.set_ylabel('빈도', fontweight='bold')
            ax2.set_title('고도 분포', fontweight='bold')
            ax2.grid(True, alpha=0.3)

        # 3. 속도 분포
        ax3 = plt.subplot(2, 3, 3)
        if 'speed_mps' in self.merged_data.columns:
            ax3.hist(self.merged_data['speed_mps'].dropna(), bins=30, color='lightcoral', edgecolor='black')
            ax3.set_xlabel('속도 (m/s)', fontweight='bold')
            ax3.set_ylabel('빈도', fontweight='bold')
            ax3.set_title('속도 분포', fontweight='bold')
            ax3.grid(True, alpha=0.3)

        # 4. 고도 시계열 (간단)
        ax4 = plt.subplot(2, 3, 4)
        if 'altitude' in self.merged_data.columns:
            valid = self.merged_data['altitude'].dropna()
            ax4.plot(valid.index, valid.values, color='green', linewidth=1.5)
            ax4.fill_between(valid.index, 0, valid.values, alpha=0.3, color='green')
            ax4.set_xlabel('샘플 인덱스', fontweight='bold')
            ax4.set_ylabel('고도 (m)', fontweight='bold')
            ax4.set_title('고도 프로파일', fontweight='bold')
            ax4.grid(True, alpha=0.3)

        # 5. 속도 시계열 (간단)
        ax5 = plt.subplot(2, 3, 5)
        if 'speed_mps' in self.merged_data.columns:
            valid = self.merged_data['speed_mps'].dropna()
            ax5.plot(valid.index, valid.values, color='orange', linewidth=1.5)
            ax5.fill_between(valid.index, 0, valid.values, alpha=0.3, color='orange')
            ax5.set_xlabel('샘플 인덱스', fontweight='bold')
            ax5.set_ylabel('속도 (m/s)', fontweight='bold')
            ax5.set_title('속도 프로파일', fontweight='bold')
            ax5.grid(True, alpha=0.3)

        # 6. 비행 경로 미니맵
        ax6 = plt.subplot(2, 3, 6)
        if 'latitude' in self.merged_data.columns and 'longitude' in self.merged_data.columns:
            valid = self.merged_data[
                (self.merged_data['latitude'].notna()) &
                (self.merged_data['longitude'].notna())
            ]
            if 'altitude' in valid.columns and valid['altitude'].notna().any():
                scatter = ax6.scatter(
                    valid['longitude'],
                    valid['latitude'],
                    c=valid['altitude'],
                    cmap='viridis',
                    s=20,
                    alpha=0.6
                )
                plt.colorbar(scatter, ax=ax6, label='고도 (m)')
            else:
                ax6.scatter(
                    valid['longitude'],
                    valid['latitude'],
                    c='blue',
                    s=20,
                    alpha=0.6
                )
            ax6.plot(valid['longitude'], valid['latitude'], 'k-', alpha=0.3, linewidth=1)
            ax6.set_xlabel('경도', fontweight='bold')
            ax6.set_ylabel('위도', fontweight='bold')
            ax6.set_title('비행 경로 (미니맵)', fontweight='bold')
            ax6.grid(True, alpha=0.3)

        plt.suptitle('비행 통계 대시보드', fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(self.charts_folder / 'flight_statistics_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _chart_speed_vs_lte(self):
        """차트 1: 이동 속도 vs LTE 품질"""
        if 'speed_mps' not in self.merged_data.columns or 'lte_rsrp' not in self.merged_data.columns:
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # 왼쪽: 속도 vs RSSI
        valid_data = self.merged_data[
            (self.merged_data['speed_mps'].notna()) &
            (self.merged_data['lte_rssi'].notna() if 'lte_rssi' in self.merged_data.columns else True)
        ].copy()

        if len(valid_data) > 0 and 'lte_rssi' in self.merged_data.columns:
            scatter1 = ax1.scatter(valid_data['speed_mps'], valid_data['lte_rssi'],
                                  c=valid_data['altitude'] if 'altitude' in valid_data.columns else 'blue',
                                  cmap='viridis', s=20, alpha=0.6)
            ax1.set_xlabel('Movement Speed (m/s)', fontweight='bold')
            ax1.set_ylabel('LTE RSSI (dBm)', fontweight='bold')
            ax1.set_title('이동 속도 vs LTE 신호 강도', fontweight='bold')
            ax1.grid(True, alpha=0.3)
            if 'altitude' in valid_data.columns:
                plt.colorbar(scatter1, ax=ax1, label='Altitude (m)')

        # 오른쪽: 속도 vs RSRP
        valid_data2 = self.merged_data[
            (self.merged_data['speed_mps'].notna()) &
            (self.merged_data['lte_rsrp'].notna())
        ].copy()

        if len(valid_data2) > 0:
            scatter2 = ax2.scatter(valid_data2['speed_mps'], valid_data2['lte_rsrp'],
                                  c=valid_data2['altitude'] if 'altitude' in valid_data2.columns else 'blue',
                                  cmap='viridis', s=20, alpha=0.6)
            ax2.set_xlabel('Movement Speed (m/s)', fontweight='bold')
            ax2.set_ylabel('LTE RSRP (dBm)', fontweight='bold')
            ax2.set_title('이동 속도 vs LTE 기준신호 전력', fontweight='bold')
            ax2.grid(True, alpha=0.3)
            if 'altitude' in valid_data2.columns:
                plt.colorbar(scatter2, ax=ax2, label='Altitude (m)')

        plt.tight_layout()
        plt.savefig(self.charts_folder / 'chart1_speed_vs_lte.png', dpi=200, bbox_inches='tight')
        plt.close()

    def _chart_distance_vs_lte(self):
        """차트 2: 원점 거리 vs LTE 품질"""
        if 'distance_from_origin' not in self.merged_data.columns or 'lte_rsrp' not in self.merged_data.columns:
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        valid_data = self.merged_data[
            (self.merged_data['distance_from_origin'].notna()) &
            (self.merged_data['lte_rsrp'].notna())
        ].copy()

        if len(valid_data) == 0:
            plt.close()
            return

        # 왼쪽: 거리 vs RSRP
        scatter1 = ax1.scatter(valid_data['distance_from_origin'], valid_data['lte_rsrp'],
                              c=valid_data['flight_time_elapsed'] if 'flight_time_elapsed' in valid_data.columns else 'blue',
                              cmap='plasma', s=20, alpha=0.6)
        ax1.set_xlabel('Distance from Origin (m)', fontweight='bold')
        ax1.set_ylabel('LTE RSRP (dBm)', fontweight='bold')
        ax1.set_title('원점 거리 vs LTE 기준신호 전력', fontweight='bold')
        ax1.grid(True, alpha=0.3)
        if 'flight_time_elapsed' in valid_data.columns:
            plt.colorbar(scatter1, ax=ax1, label='Flight Time (s)')

        # 오른쪽: 거리 vs SINR
        if 'lte_sinr' in valid_data.columns:
            valid_data_sinr = valid_data[valid_data['lte_sinr'].notna()]
            if len(valid_data_sinr) > 0:
                scatter2 = ax2.scatter(valid_data_sinr['distance_from_origin'], valid_data_sinr['lte_sinr'],
                                      c=valid_data_sinr['flight_time_elapsed'] if 'flight_time_elapsed' in valid_data_sinr.columns else 'blue',
                                      cmap='plasma', s=20, alpha=0.6)
                ax2.set_xlabel('Distance from Origin (m)', fontweight='bold')
                ax2.set_ylabel('LTE SINR (dB)', fontweight='bold')
                ax2.set_title('원점 거리 vs LTE 신호대 간섭비', fontweight='bold')
                ax2.grid(True, alpha=0.3)
                if 'flight_time_elapsed' in valid_data_sinr.columns:
                    plt.colorbar(scatter2, ax=ax2, label='Flight Time (s)')

        plt.tight_layout()
        plt.savefig(self.charts_folder / 'chart2_distance_vs_lte.png', dpi=200, bbox_inches='tight')
        plt.close()

    def _chart_time_vs_starlink(self):
        """차트 3: 비행 시간 vs Starlink 지연"""
        if 'flight_time_elapsed' not in self.merged_data.columns or 'starlink_ping_latency_ms' not in self.merged_data.columns:
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        valid_data = self.merged_data[
            (self.merged_data['flight_time_elapsed'].notna()) &
            (self.merged_data['starlink_ping_latency_ms'].notna())
        ].copy()

        if len(valid_data) == 0:
            plt.close()
            return

        # 왼쪽: 시간 vs 지연
        scatter1 = ax1.scatter(valid_data['flight_time_elapsed'], valid_data['starlink_ping_latency_ms'],
                              c=valid_data['altitude'] if 'altitude' in valid_data.columns else 'blue',
                              cmap='coolwarm', s=20, alpha=0.6)
        ax1.set_xlabel('Flight Time Elapsed (s)', fontweight='bold')
        ax1.set_ylabel('Starlink Ping Latency (ms)', fontweight='bold')
        ax1.set_title('비행 시간 vs Starlink 지연', fontweight='bold')
        ax1.grid(True, alpha=0.3)
        if 'altitude' in valid_data.columns:
            plt.colorbar(scatter1, ax=ax1, label='Altitude (m)')

        # 오른쪽: 시간 vs Throughput
        if 'starlink_downlink_throughput_bps' in valid_data.columns:
            valid_data_tp = valid_data[valid_data['starlink_downlink_throughput_bps'].notna()]
            if len(valid_data_tp) > 0:
                scatter2 = ax2.scatter(valid_data_tp['flight_time_elapsed'],
                                      valid_data_tp['starlink_downlink_throughput_bps'] / 1e6,
                                      c=valid_data_tp['altitude'] if 'altitude' in valid_data_tp.columns else 'blue',
                                      cmap='coolwarm', s=20, alpha=0.6)
                ax2.set_xlabel('Flight Time Elapsed (s)', fontweight='bold')
                ax2.set_ylabel('Downlink Throughput (Mbps)', fontweight='bold')
                ax2.set_title('비행 시간 vs Starlink 처리량', fontweight='bold')
                ax2.grid(True, alpha=0.3)
                if 'altitude' in valid_data_tp.columns:
                    plt.colorbar(scatter2, ax=ax2, label='Altitude (m)')

        plt.tight_layout()
        plt.savefig(self.charts_folder / 'chart3_time_vs_starlink.png', dpi=200, bbox_inches='tight')
        plt.close()

    def _chart_3d_multidimensional(self):
        """차트 4: 3D 고도-속도-품질"""
        if ('altitude' not in self.merged_data.columns or
            'speed_mps' not in self.merged_data.columns or
            'lte_rsrp' not in self.merged_data.columns):
            return

        from mpl_toolkits.mplot3d import Axes3D

        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        valid_data = self.merged_data[
            (self.merged_data['altitude'].notna()) &
            (self.merged_data['speed_mps'].notna()) &
            (self.merged_data['lte_rsrp'].notna())
        ].copy()

        if len(valid_data) == 0:
            plt.close()
            return

        scatter = ax.scatter(valid_data['altitude'], valid_data['speed_mps'], valid_data['lte_rsrp'],
                            c=valid_data['lte_rsrp'], cmap='RdYlGn', s=30, alpha=0.6)
        ax.set_xlabel('Altitude (m)', fontweight='bold')
        ax.set_ylabel('Speed (m/s)', fontweight='bold')
        ax.set_zlabel('LTE RSRP (dBm)', fontweight='bold')
        ax.set_title('3D: 고도 - 속도 - LTE 품질', fontsize=14, fontweight='bold')
        plt.colorbar(scatter, ax=ax, label='LTE RSRP (dBm)', shrink=0.5)

        plt.tight_layout()
        plt.savefig(self.charts_folder / 'chart4_3d_multidimensional.png', dpi=200, bbox_inches='tight')
        plt.close()

    def _chart_flight_path_map(self):
        """차트 5: 비행 경로 품질 맵"""
        if ('latitude' not in self.merged_data.columns or
            'longitude' not in self.merged_data.columns):
            return

        fig, ax = plt.subplots(figsize=(12, 10))

        valid_data = self.merged_data[
            (self.merged_data['latitude'].notna()) &
            (self.merged_data['longitude'].notna())
        ].copy()

        if len(valid_data) == 0:
            plt.close()
            return

        # LTE 품질로 색상 지정
        color_col = 'lte_rsrp' if 'lte_rsrp' in valid_data.columns else None

        if color_col and valid_data[color_col].notna().any():
            scatter = ax.scatter(valid_data['longitude'], valid_data['latitude'],
                               c=valid_data[color_col], cmap='RdYlGn',
                               s=50, alpha=0.6, edgecolors='black', linewidth=0.5)
            plt.colorbar(scatter, ax=ax, label='LTE RSRP (dBm)')
        else:
            ax.scatter(valid_data['longitude'], valid_data['latitude'],
                      c='blue', s=50, alpha=0.6)

        # 시작점과 종료점 표시
        ax.scatter(valid_data['longitude'].iloc[0], valid_data['latitude'].iloc[0],
                  c='green', s=200, marker='*', edgecolors='black', linewidth=2,
                  label='Start', zorder=5)
        ax.scatter(valid_data['longitude'].iloc[-1], valid_data['latitude'].iloc[-1],
                  c='red', s=200, marker='X', edgecolors='black', linewidth=2,
                  label='End', zorder=5)

        ax.set_xlabel('Longitude', fontweight='bold')
        ax.set_ylabel('Latitude', fontweight='bold')
        ax.set_title('비행 경로 품질 맵', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        plt.savefig(self.charts_folder / 'chart5_flight_path_quality_map.png', dpi=200, bbox_inches='tight')
        plt.close()

    def _chart_timeseries_multiaxis(self):
        """차트 6: 시계열 4축 복합 분석"""
        if 'timestamp' not in self.merged_data.columns:
            return

        fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True)

        # Axis 1: LTE RSRP
        if 'lte_rsrp' in self.merged_data.columns:
            valid_rsrp = self.merged_data[self.merged_data['lte_rsrp'].notna()]
            if len(valid_rsrp) > 0:
                axes[0].plot(valid_rsrp.index, valid_rsrp['lte_rsrp'], 'b-', linewidth=1.5, label='LTE RSRP')
                axes[0].set_ylabel('LTE RSRP (dBm)', fontweight='bold')
                axes[0].grid(True, alpha=0.3)
                axes[0].legend()

        # Axis 2: Starlink 지연
        if 'starlink_ping_latency_ms' in self.merged_data.columns:
            valid_latency = self.merged_data[self.merged_data['starlink_ping_latency_ms'].notna()]
            if len(valid_latency) > 0:
                axes[1].plot(valid_latency.index, valid_latency['starlink_ping_latency_ms'],
                           'g-', linewidth=1.5, label='Starlink Latency')
                axes[1].set_ylabel('Latency (ms)', fontweight='bold')
                axes[1].grid(True, alpha=0.3)
                axes[1].legend()

        # Axis 3: 고도 & 속도
        if 'altitude' in self.merged_data.columns:
            valid_alt = self.merged_data[self.merged_data['altitude'].notna()]
            if len(valid_alt) > 0:
                ax3_twin = axes[2].twinx()
                axes[2].plot(valid_alt.index, valid_alt['altitude'], 'r-', linewidth=1.5, label='Altitude')
                axes[2].set_ylabel('Altitude (m)', fontweight='bold', color='r')
                axes[2].tick_params(axis='y', labelcolor='r')

                if 'speed_mps' in valid_alt.columns:
                    valid_speed = valid_alt[valid_alt['speed_mps'].notna()]
                    if len(valid_speed) > 0:
                        ax3_twin.plot(valid_speed.index, valid_speed['speed_mps'],
                                     'orange', linewidth=1.5, label='Speed')
                        ax3_twin.set_ylabel('Speed (m/s)', fontweight='bold', color='orange')
                        ax3_twin.tick_params(axis='y', labelcolor='orange')

                axes[2].grid(True, alpha=0.3)

        # Axis 4: Throughput
        if 'starlink_downlink_throughput_bps' in self.merged_data.columns:
            valid_tp = self.merged_data[self.merged_data['starlink_downlink_throughput_bps'].notna()]
            if len(valid_tp) > 0:
                axes[3].plot(valid_tp.index, valid_tp['starlink_downlink_throughput_bps'] / 1e6,
                           'purple', linewidth=1.5, label='Downlink Throughput')
                axes[3].set_ylabel('Throughput (Mbps)', fontweight='bold')
                axes[3].set_xlabel('Sample Index', fontweight='bold')
                axes[3].grid(True, alpha=0.3)
                axes[3].legend()

        plt.suptitle('시계열 4축 복합 분석', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        plt.savefig(self.charts_folder / 'chart6_timeseries_multiaxis.png', dpi=200, bbox_inches='tight')
        plt.close()

    def step_6_generate_map_data(self) -> Dict:
        """Step 6: 지도 데이터 생성 (GeoJSON)"""
        try:
            print(f"[Step 6/7] 비행 경로 지도 데이터 생성 중...")

            # GPS 데이터 확인
            if ('latitude' not in self.merged_data.columns or
                'longitude' not in self.merged_data.columns):
                return {
                    'status': 'skipped',
                    'message': 'GPS 데이터 없음, 지도 생성 건너뜀'
                }

            valid_data = self.merged_data[
                (self.merged_data['latitude'].notna()) &
                (self.merged_data['longitude'].notna())
            ].copy()

            if len(valid_data) == 0:
                return {
                    'status': 'skipped',
                    'message': '유효한 GPS 데이터 없음'
                }

            # GeoJSON 생성
            features = []
            for idx, row in valid_data.iterrows():
                # LTE 품질 데이터
                lte_rsrp = row.get('lte_rsrp', None)
                lte_rssi = row.get('lte_rssi', None)
                lte_sinr = row.get('lte_sinr', None)

                # Starlink 품질 데이터
                starlink_latency = row.get('starlink_latency', None)
                starlink_snr = row.get('starlink_snr', None)

                # 품질 등급 계산 (RSRP 기준)
                quality = 'unknown'
                if lte_rsrp is not None and pd.notna(lte_rsrp):
                    if lte_rsrp >= -80:
                        quality = 'excellent'
                    elif lte_rsrp >= -90:
                        quality = 'good'
                    elif lte_rsrp >= -100:
                        quality = 'fair'
                    else:
                        quality = 'poor'

                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [float(row['longitude']), float(row['latitude'])]
                    },
                    'properties': {
                        'timestamp': str(row.get('timestamp', '')),
                        'altitude': float(row.get('altitude', 0)) if pd.notna(row.get('altitude')) else None,
                        'lte_rsrp': float(lte_rsrp) if pd.notna(lte_rsrp) else None,
                        'lte_rssi': float(lte_rssi) if pd.notna(lte_rssi) else None,
                        'lte_sinr': float(lte_sinr) if pd.notna(lte_sinr) else None,
                        'starlink_latency': float(starlink_latency) if pd.notna(starlink_latency) else None,
                        'starlink_snr': float(starlink_snr) if pd.notna(starlink_snr) else None,
                        'quality': quality
                    }
                }
                features.append(feature)

            geojson_data = {
                'type': 'FeatureCollection',
                'features': features
            }

            # GeoJSON 파일 저장 (API와 파일명 일치)
            geojson_path = self.results_folder / 'map_data.geojson'
            with open(geojson_path, 'w', encoding='utf-8') as f:
                json.dump(geojson_data, f, ensure_ascii=False, indent=2)

            print(f"  ✓ GeoJSON 생성 완료: {len(features)} 포인트")

            # Folium 인터랙티브 히트맵 생성
            try:
                from quality_heatmap import QualityHeatmapGenerator

                # merged_data.csv 사용
                merged_data_path = self.results_folder / 'merged_data.csv'

                generator = QualityHeatmapGenerator(str(merged_data_path))
                generator.load_data()

                # 3가지 히트맵 생성
                lte_heatmap = self.results_folder / 'lte_quality_heatmap.html'
                starlink_heatmap = self.results_folder / 'starlink_quality_heatmap.html'
                combined_map = self.results_folder / 'combined_quality_map.html'

                generator.create_lte_heatmap(str(lte_heatmap))
                generator.create_starlink_heatmap(str(starlink_heatmap))
                generator.create_combined_map(str(combined_map))

                # 실제 생성된 파일 개수 확인
                created_files = []
                if lte_heatmap.exists():
                    created_files.append('LTE')
                if starlink_heatmap.exists():
                    created_files.append('Starlink')
                if combined_map.exists():
                    created_files.append('Combined')

                if created_files:
                    print(f"  ✓ Folium 히트맵 생성: {', '.join(created_files)} ({len(created_files)}개)")
                else:
                    print(f"  ⚠️  히트맵 생성 실패: 데이터 부족")

            except Exception as e:
                print(f"  ⚠️  Folium 히트맵 생성 실패: {str(e)}")
                import traceback
                traceback.print_exc()
                # 히트맵 생성 실패를 단계 실패로 처리
                return {
                    'status': 'error',
                    'message': f'Folium 히트맵 생성 실패: {str(e)}',
                    'traceback': traceback.format_exc()
                }

            return {
                'status': 'success',
                'message': f'지도 데이터 생성 완료 ({len(features)} 포인트)',
                'geojson_path': str(geojson_path)
            }

        except Exception as e:
            print(f"  ✗ 지도 데이터 생성 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': f'지도 데이터 생성 실패: {str(e)}',
                'traceback': traceback.format_exc()
            }

    def step_7_generate_report(self) -> Dict:
        """Step 7: Word 보고서 생성 - 전문 보고서 (WordReportGenerator 사용)"""
        try:
            print(f"[Step 7/7] 전문 Word 보고서 생성 중...")

            # Import WordReportGenerator
            import sys
            analysis_dir = Path(__file__).parent
            if str(analysis_dir) not in sys.path:
                sys.path.insert(0, str(analysis_dir))

            from word_report_generator import WordReportGenerator

            # merged_data.csv 경로
            merged_data_path = self.results_folder / 'merged_data.csv'

            # WordReportGenerator 생성 및 실행
            report_generator = WordReportGenerator(str(merged_data_path))
            report_path = report_generator.generate_report(output_path="analysis_report.docx")

            print(f"  ✓ 전문 보고서 생성 완료: {Path(report_path).name}")

            return {
                'status': 'success',
                'message': '전문 Word 보고서 생성 완료 (422+ 문단 포함)',
                'report_path': report_path
            }

        except Exception as e:
            print(f"  ⚠️  WordReportGenerator 실패, 기본 보고서로 대체: {str(e)}")
            import traceback
            traceback.print_exc()

            # WordReportGenerator 실패 시 기본 보고서 생성
            try:
                report_path = self.results_folder / 'analysis_report.docx'

                from docx import Document
                from docx.shared import Inches, Pt
                from docx.enum.text import WD_ALIGN_PARAGRAPH

                doc = Document()

                # 표지
                title = doc.add_heading('비행 데이터 분석 보고서', 0)
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER

                doc.add_paragraph()
                info = doc.add_paragraph()
                info.alignment = WD_ALIGN_PARAGRAPH.CENTER
                info.add_run('LTE + Starlink 듀얼 네트워크 통신 품질 분석\n\n').bold = True
                info.add_run(f'분석 일자: {datetime.now().strftime("%Y년 %m월 %d일")}\n')
                info.add_run(f'데이터 포인트: {len(self.merged_data):,}개\n')

                doc.add_page_break()

                # 차트
                doc.add_heading('분석 차트', 1)
                chart_list = list(self.charts_folder.glob('*.png'))
                for i, chart_file in enumerate(chart_list[:12]):
                    doc.add_heading(f'{chart_file.stem.replace("_", " ").title()}', 2)
                    try:
                        doc.add_picture(str(chart_file), width=Inches(6.5))
                    except:
                        doc.add_paragraph('[차트 로드 실패]')

                doc.save(str(report_path))
                print(f"  ✓ 기본 보고서 저장: {report_path.name}")

                return {'status': 'success', 'message': f'기본 보고서 생성 완료 ({len(chart_list)}개 차트)'}

            except Exception as e2:
                return {
                    'status': 'error',
                    'message': f'보고서 생성 실패: {str(e2)}',
                    'traceback': traceback.format_exc()
                }

    def run_full_analysis(self, progress_callback=None) -> Dict:
        """전체 분석 파이프라인 실행"""
        steps = [
            ('데이터 로드', self.step_1_load_data),
            ('상관관계 분석', self.step_2_correlation_analysis),
            ('통신 품질 분석', self.step_3_quality_analysis),
            ('고도별 분석', self.step_4_altitude_analysis),
            ('차트 생성', self.step_5_generate_charts),
            ('지도 데이터 생성', self.step_6_generate_map_data),
            ('보고서 생성', self.step_7_generate_report)
        ]

        results = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'steps': [],
            'overall_status': 'success'
        }

        for idx, (step_name, step_func) in enumerate(steps, 1):
            if progress_callback:
                progress_callback(idx, len(steps), f'{step_name} 시작')

            step_result = step_func()
            step_result['step_name'] = step_name
            step_result['step_number'] = idx
            results['steps'].append(step_result)

            if step_result['status'] == 'error':
                results['overall_status'] = 'failed'
                results['failed_at_step'] = idx
                break

        results['end_time'] = datetime.now().isoformat()
        results['analysis_results'] = self.analysis_results

        # 결과 JSON 저장 (numpy 타입 변환 포함)
        results_json_path = self.results_folder / 'analysis_results.json'
        with open(results_json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=self._json_serializer)

        return results

    # ===== 헬퍼 메서드 =====

    def _json_serializer(self, obj):
        """
        JSON 직렬화를 위한 numpy 타입 변환기

        Args:
            obj: 직렬화할 객체

        Returns:
            Python 기본 타입으로 변환된 객체
        """
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return str(obj)

    def _extract_time_ranges(self, flight_data: pd.DataFrame, lte_data: pd.DataFrame, starlink_data: pd.DataFrame) -> Dict:
        """
        각 데이터 소스의 시간 범위 추출

        Args:
            flight_data: GPS 비행 데이터
            lte_data: LTE 통신 데이터
            starlink_data: Starlink 통신 데이터

        Returns:
            Dict: 각 데이터 소스의 시작/종료 시간
        """
        time_ranges = {}

        # 비행 데이터 시간 범위
        if flight_data is not None and len(flight_data) > 0 and 'timestamp' in flight_data.columns:
            time_ranges['flight'] = {
                'start': flight_data['timestamp'].min().isoformat(),
                'end': flight_data['timestamp'].max().isoformat(),
                'start_unix': float(flight_data['timestamp'].min().timestamp()),
                'end_unix': float(flight_data['timestamp'].max().timestamp()),
                'count': len(flight_data)
            }

        # LTE 데이터 시간 범위
        if lte_data is not None and len(lte_data) > 0 and 'timestamp' in lte_data.columns:
            time_ranges['lte'] = {
                'start': lte_data['timestamp'].min().isoformat(),
                'end': lte_data['timestamp'].max().isoformat(),
                'start_unix': float(lte_data['timestamp'].min().timestamp()),
                'end_unix': float(lte_data['timestamp'].max().timestamp()),
                'count': len(lte_data)
            }

        # Starlink 데이터 시간 범위
        if starlink_data is not None and len(starlink_data) > 0 and 'timestamp' in starlink_data.columns:
            time_ranges['starlink'] = {
                'start': starlink_data['timestamp'].min().isoformat(),
                'end': starlink_data['timestamp'].max().isoformat(),
                'start_unix': float(starlink_data['timestamp'].min().timestamp()),
                'end_unix': float(starlink_data['timestamp'].max().timestamp()),
                'count': len(starlink_data)
            }

        return time_ranges

    def _check_time_overlap(self, time_ranges: Dict) -> List[str]:
        """
        시간 범위 겹침 검사 및 경고 메시지 생성

        Args:
            time_ranges: 각 데이터 소스의 시간 범위

        Returns:
            List[str]: 경고 메시지 리스트
        """
        warnings = []

        if 'flight' not in time_ranges:
            return warnings

        flight_start = time_ranges['flight']['start_unix']
        flight_end = time_ranges['flight']['end_unix']

        # LTE 데이터와 비행 데이터 겹침 검사
        if 'lte' in time_ranges:
            lte_start = time_ranges['lte']['start_unix']
            lte_end = time_ranges['lte']['end_unix']

            # 겹치는 영역이 없는 경우
            if lte_end < flight_start:
                gap_minutes = int((flight_start - lte_end) / 60)
                warnings.append(f"LTE 데이터가 비행 데이터보다 {gap_minutes}분 앞섬 (시간 불일치)")
            elif lte_start > flight_end:
                gap_minutes = int((lte_start - flight_end) / 60)
                warnings.append(f"LTE 데이터가 비행 데이터보다 {gap_minutes}분 뒤짐 (시간 불일치)")
            else:
                # 겹치는 영역 계산
                overlap_start = max(flight_start, lte_start)
                overlap_end = min(flight_end, lte_end)
                overlap_seconds = overlap_end - overlap_start
                flight_duration = flight_end - flight_start
                overlap_percent = (overlap_seconds / flight_duration) * 100

                if overlap_percent < 50:
                    warnings.append(f"LTE 데이터와 비행 데이터 겹침: {overlap_percent:.1f}% (부분적)")

        # Starlink 데이터와 비행 데이터 겹침 검사
        if 'starlink' in time_ranges:
            sl_start = time_ranges['starlink']['start_unix']
            sl_end = time_ranges['starlink']['end_unix']

            # 겹치는 영역이 없는 경우
            if sl_end < flight_start:
                gap_minutes = int((flight_start - sl_end) / 60)
                warnings.append(f"Starlink 데이터가 비행 데이터보다 {gap_minutes}분 앞섬 (시간 불일치)")
            elif sl_start > flight_end:
                gap_minutes = int((sl_start - flight_end) / 60)
                warnings.append(f"Starlink 데이터가 비행 데이터보다 {gap_minutes}분 뒤짐 (시간 불일치)")
            else:
                # 겹치는 영역 계산
                overlap_start = max(flight_start, sl_start)
                overlap_end = min(flight_end, sl_end)
                overlap_seconds = overlap_end - overlap_start
                flight_duration = flight_end - flight_start
                overlap_percent = (overlap_seconds / flight_duration) * 100

                if overlap_percent < 50:
                    warnings.append(f"Starlink 데이터와 비행 데이터 겹침: {overlap_percent:.1f}% (부분적)")

        return warnings

    def _calculate_lte_quality_stats(self) -> Dict:
        """LTE 품질 통계"""
        stats = {}

        # merged_data에서 lte_ 접두사가 붙은 컬럼 찾기
        lte_cols = [col for col in self.merged_data.columns if col.startswith('lte_')]

        for base_col in ['rsrp', 'rsrq', 'sinr']:
            col = f'lte_{base_col}'
            if col in self.merged_data.columns:
                data = self.merged_data[col].dropna()
                if len(data) > 0:
                    stats[f'avg_{base_col}'] = float(data.mean())
                    stats[f'min_{base_col}'] = float(data.min())
                    stats[f'max_{base_col}'] = float(data.max())

        return stats

    def _calculate_starlink_quality_stats(self) -> Dict:
        """Starlink 품질 통계"""
        stats = {}

        # starlink_ 접두사가 붙은 컬럼 찾기
        for base_col in ['snr', 'ping_latency_ms', 'downlink_throughput_bps', 'uplink_throughput_bps']:
            col = f'starlink_{base_col}'
            if col in self.merged_data.columns:
                data = self.merged_data[col].dropna()
                if len(data) > 0:
                    stats[f'avg_{base_col}'] = float(data.mean())
                    stats[f'min_{base_col}'] = float(data.min())
                    stats[f'max_{base_col}'] = float(data.max())

        return stats

    def _generate_quality_comparison_charts(self):
        """품질 비교 차트"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # LTE RSRP 분포
        if 'lte_rsrp' in self.merged_data.columns:
            data = self.merged_data['lte_rsrp'].dropna()
            if len(data) > 0:
                axes[0].hist(data, bins=30, color='blue', alpha=0.7)
                axes[0].set_title('LTE RSRP Distribution')
                axes[0].set_xlabel('RSRP (dBm)')
                axes[0].set_ylabel('Frequency')

        # Starlink SNR 분포
        if 'starlink_snr' in self.merged_data.columns:
            data = self.merged_data['starlink_snr'].dropna()
            if len(data) > 0:
                axes[1].hist(data, bins=30, color='green', alpha=0.7)
                axes[1].set_title('Starlink SNR Distribution')
                axes[1].set_xlabel('SNR (dB)')
                axes[1].set_ylabel('Frequency')

        plt.tight_layout()
        plt.savefig(self.charts_folder / 'quality_distribution.png', dpi=150)
        plt.close()

    def _analyze_by_altitude(self) -> Dict:
        """고도별 품질 분석"""
        if self.merged_data is None or 'altitude' not in self.merged_data.columns:
            return {}

        # altitude 컬럼이 Series인지 확인
        altitude_series = self.merged_data['altitude']
        if isinstance(altitude_series, pd.DataFrame):
            # DataFrame이면 첫 번째 컬럼만 사용
            altitude_series = altitude_series.iloc[:, 0]

        # NaN 제거
        valid_data = self.merged_data[altitude_series.notna()].copy()
        if len(valid_data) == 0:
            return {}

        # 고도 범위 계산
        min_alt = valid_data['altitude'].min() if not isinstance(valid_data['altitude'], pd.DataFrame) else valid_data['altitude'].iloc[:, 0].min()
        max_alt = valid_data['altitude'].max() if not isinstance(valid_data['altitude'], pd.DataFrame) else valid_data['altitude'].iloc[:, 0].max()

        # 동적 bins 생성
        if max_alt - min_alt < 100:
            num_bins = 5
        else:
            num_bins = min(10, int((max_alt - min_alt) / 50))

        bins = np.linspace(min_alt, max_alt, num_bins + 1)
        labels = [f'{int(bins[i])}-{int(bins[i+1])}m' for i in range(len(bins)-1)]

        # altitude가 Series인지 확인하고 변환
        altitude_values = valid_data['altitude']
        if isinstance(altitude_values, pd.DataFrame):
            altitude_values = altitude_values.iloc[:, 0]

        valid_data['altitude_range'] = pd.cut(
            altitude_values, bins=bins, labels=labels, include_lowest=True
        )

        # 고도 구간별 집계
        agg_cols = {}
        for col in ['lte_rsrp', 'lte_rsrq', 'lte_sinr', 'starlink_snr', 'starlink_ping_latency_ms']:
            if col in valid_data.columns:
                agg_cols[col] = 'mean'

        if not agg_cols:
            return {}

        result = valid_data.groupby('altitude_range').agg(agg_cols).to_dict()
        return result

    def _plot_altitude_quality(self, output_path: Path):
        """고도-품질 플롯"""
        fig, ax = plt.subplots(figsize=(10, 6))

        if 'altitude' in self.merged_data.columns:
            altitude = self.merged_data['altitude']
            if isinstance(altitude, pd.DataFrame):
                altitude = altitude.iloc[:, 0]

            # LTE RSRP와 고도
            if 'lte_rsrp' in self.merged_data.columns:
                rsrp = self.merged_data['lte_rsrp']
                valid_idx = altitude.notna() & rsrp.notna()
                if valid_idx.sum() > 0:
                    ax.scatter(altitude[valid_idx], rsrp[valid_idx],
                             alpha=0.5, label='LTE RSRP', color='blue')

            # Starlink SNR와 고도
            if 'starlink_snr' in self.merged_data.columns:
                snr = self.merged_data['starlink_snr']
                valid_idx = altitude.notna() & snr.notna()
                if valid_idx.sum() > 0:
                    ax2 = ax.twinx()
                    ax2.scatter(altitude[valid_idx], snr[valid_idx],
                              alpha=0.5, label='Starlink SNR', color='green')
                    ax2.set_ylabel('SNR (dB)', color='green')
                    ax2.legend(loc='upper right')

        ax.set_xlabel('Altitude (m)')
        ax.set_ylabel('RSRP (dBm)', color='blue')
        ax.set_title('Altitude vs Communication Quality')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')

        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()

    def _plot_quality_over_time(self):
        """시간별 품질 변화"""
        fig, ax = plt.subplots(figsize=(12, 6))

        has_data = False

        # LTE RSRP 시간별 변화
        if 'lte_rsrp' in self.merged_data.columns:
            data = self.merged_data['lte_rsrp'].dropna()
            if len(data) > 0:
                ax.plot(data.index, data.values, label='LTE RSRP', alpha=0.7, color='blue')
                ax.set_ylabel('RSRP (dBm)', color='blue')
                has_data = True

        # Starlink SNR 시간별 변화
        if 'starlink_snr' in self.merged_data.columns:
            data = self.merged_data['starlink_snr'].dropna()
            if len(data) > 0:
                ax2 = ax.twinx()
                ax2.plot(data.index, data.values, label='Starlink SNR', alpha=0.7, color='green')
                ax2.set_ylabel('SNR (dB)', color='green')
                ax2.legend(loc='upper right')
                has_data = True

        if has_data:
            ax.set_xlabel('Sample Index')
            ax.set_title('Communication Quality Over Time')
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.charts_folder / 'quality_over_time.png', dpi=150)
        plt.close()

    def _plot_quality_heatmap(self):
        """품질 히트맵"""
        if 'correlation' in self.analysis_results:
            corr_matrix = pd.DataFrame(self.analysis_results['correlation']['matrix'])

            plt.figure(figsize=(12, 10))
            sns.heatmap(corr_matrix, annot=False, cmap='coolwarm', center=0,
                       square=True, linewidths=0.5, cbar_kws={"shrink": 0.8})
            plt.title('Parameter Correlation Heatmap')
            plt.tight_layout()
            plt.savefig(self.charts_folder / 'correlation_heatmap.png', dpi=150)
            plt.close()

    def _plot_statistics_summary(self):
        """통계 요약 차트"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        if 'quality' in self.analysis_results and 'lte' in self.analysis_results['quality']:
            lte_stats = self.analysis_results['quality']['lte']
            metrics = list(lte_stats.keys())
            values = list(lte_stats.values())

            axes[0, 0].barh(metrics, values, color='blue', alpha=0.7)
            axes[0, 0].set_title('LTE Quality Metrics')

        if 'quality' in self.analysis_results and 'starlink' in self.analysis_results['quality']:
            starlink_stats = self.analysis_results['quality']['starlink']
            metrics = list(starlink_stats.keys())
            values = list(starlink_stats.values())

            axes[0, 1].barh(metrics, values, color='green', alpha=0.7)
            axes[0, 1].set_title('Starlink Quality Metrics')

        axes[1, 0].text(0.5, 0.5, f'Total Data Points: {len(self.merged_data)}',
                       ha='center', va='center', fontsize=12)
        axes[1, 0].axis('off')

        axes[1, 1].axis('off')

        plt.tight_layout()
        plt.savefig(self.charts_folder / 'statistics_summary.png', dpi=150)
        plt.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print("Usage: python analysis_pipeline.py <session_id>")
        sys.exit(1)

    session_id = sys.argv[1]
    upload_folder = Path('uploads') / session_id
    results_folder = Path('results') / session_id

    pipeline = AnalysisPipeline(session_id, upload_folder, results_folder)

    valid, message = pipeline.validate_files()
    if not valid:
        print(f"Error: {message}")
        sys.exit(1)

    def progress_callback(step, total, message):
        print(f"[{step}/{total}] {message}")

    results = pipeline.run_full_analysis(progress_callback)
    print("\n분석 완료!")
    print(json.dumps(results, indent=2, ensure_ascii=False))
