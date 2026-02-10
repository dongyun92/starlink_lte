#!/usr/bin/env python3
"""
다차원 관계 시각화 차트 생성
Multi-dimensional Relationship Visualization Charts
- 이동 속도, 위치, 고도, 시간의 복합 영향 분석
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정
import matplotlib.font_manager as fm

def get_korean_font():
    """macOS에서 사용 가능한 한글 폰트 찾기"""
    korean_fonts = ['AppleGothic', 'AppleSDGothicNeo-Regular', 'NanumGothic']
    available_fonts = [f.name for f in fm.fontManager.ttflist]

    for font in korean_fonts:
        if font in available_fonts:
            return font
    return 'DejaVu Sans'

korean_font = get_korean_font()
plt.rcParams['font.family'] = korean_font
plt.rcParams['axes.unicode_minus'] = False


class MultidimensionalChartGenerator:
    """다차원 관계 차트 생성기"""

    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.df = None
        self.base_dir = self.data_path.parent

    def load_data(self):
        """데이터 로드 및 파생 변수 생성"""
        print("📁 Loading comprehensive data...")

        # comprehensive_correlation_analysis.py에서 생성한 데이터 활용
        # 파생 변수를 다시 생성
        self.df = pd.read_csv(self.data_path)

        # 파생 변수 재생성
        self._create_derived_variables()

        print(f"✓ Loaded {len(self.df)} samples with {len(self.df.columns)} columns")

    def _create_derived_variables(self):
        """파생 변수 생성"""
        # Haversine distance
        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371000
            phi1, phi2 = np.radians(lat1), np.radians(lat2)
            dphi = np.radians(lat2 - lat1)
            dlambda = np.radians(lon2 - lon1)
            a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            return R * c

        self.df['distance_moved'] = haversine_distance(
            self.df['latitude'].shift(1), self.df['longitude'].shift(1),
            self.df['latitude'], self.df['longitude']
        )

        self.df['speed_mps'] = self.df['distance_moved'] / 0.5

        origin_lat = self.df['latitude'].iloc[0]
        origin_lon = self.df['longitude'].iloc[0]
        self.df['distance_from_origin'] = haversine_distance(
            origin_lat, origin_lon,
            self.df['latitude'], self.df['longitude']
        )

        self.df['flight_time_elapsed'] = self.df.index * 0.5

    def chart1_speed_vs_lte(self):
        """차트 1: 이동 속도 vs LTE 품질 (색상: 고도)"""
        print("\n📊 Creating Chart 1: Speed vs LTE Quality...")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # 왼쪽: 이동 속도 vs LTE RSSI (색상: 고도)
        valid_data = self.df[(self.df['speed_mps'].notna()) &
                            (self.df['lte_rssi'].notna())].copy()

        scatter1 = ax1.scatter(valid_data['speed_mps'], valid_data['lte_rssi'],
                              c=valid_data['altitude'], cmap='viridis',
                              s=20, alpha=0.6, edgecolors='none')
        ax1.set_xlabel('Movement Speed (m/s)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('LTE RSSI (dBm)', fontsize=12, fontweight='bold')
        ax1.set_title('이동 속도 vs LTE 신호 강도 (색상: 고도)',
                     fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        cbar1 = plt.colorbar(scatter1, ax=ax1, label='Altitude (m)')

        # 상관계수 표시
        corr = valid_data['speed_mps'].corr(valid_data['lte_rssi'])
        ax1.text(0.05, 0.95, f'Correlation: {corr:+.3f}\n(강한 양의 상관)',
                transform=ax1.transAxes, fontsize=11,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # 오른쪽: 이동 속도 vs LTE RSRP (색상: 고도)
        scatter2 = ax2.scatter(valid_data['speed_mps'], valid_data['lte_rsrp'],
                              c=valid_data['altitude'], cmap='viridis',
                              s=20, alpha=0.6, edgecolors='none')
        ax2.set_xlabel('Movement Speed (m/s)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('LTE RSRP (dBm)', fontsize=12, fontweight='bold')
        ax2.set_title('이동 속도 vs LTE 기준신호 전력 (색상: 고도)',
                     fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        cbar2 = plt.colorbar(scatter2, ax=ax2, label='Altitude (m)')

        corr2 = valid_data['speed_mps'].corr(valid_data['lte_rsrp'])
        ax2.text(0.05, 0.95, f'Correlation: {corr2:+.3f}\n(강한 양의 상관)',
                transform=ax2.transAxes, fontsize=11,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        plt.suptitle('핵심 발견: 이동 속도가 LTE 품질에 가장 큰 영향 (+0.592)',
                    fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()

        output_file = self.base_dir / "chart1_speed_vs_lte.png"
        plt.savefig(str(output_file), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {output_file}")

    def chart2_distance_vs_lte(self):
        """차트 2: 원점 거리 vs LTE 품질 (색상: 비행 시간)"""
        print("\n📊 Creating Chart 2: Distance from Origin vs LTE Quality...")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        valid_data = self.df[(self.df['distance_from_origin'].notna()) &
                            (self.df['lte_rssi'].notna())].copy()

        # 왼쪽: 원점 거리 vs LTE RSSI (색상: 비행 시간)
        scatter1 = ax1.scatter(valid_data['distance_from_origin'],
                              valid_data['lte_rssi'],
                              c=valid_data['flight_time_elapsed'],
                              cmap='plasma',
                              s=20, alpha=0.6, edgecolors='none')
        ax1.set_xlabel('Distance from Origin (m)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('LTE RSSI (dBm)', fontsize=12, fontweight='bold')
        ax1.set_title('원점 거리 vs LTE 신호 강도 (색상: 비행 시간)',
                     fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        cbar1 = plt.colorbar(scatter1, ax=ax1, label='Flight Time (s)')

        corr = valid_data['distance_from_origin'].corr(valid_data['lte_rssi'])
        ax1.text(0.05, 0.95, f'Correlation: {corr:+.3f}\n(강한 양의 상관)',
                transform=ax1.transAxes, fontsize=11,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # 오른쪽: 고도별 분포 (색상 구분)
        # 비행 단계별로 색상 구분
        for phase_name, color in [('Ground/Takeoff', '#FF6B6B'),
                                   ('Climb', '#4ECDC4'),
                                   ('Cruise_Low', '#45B7D1'),
                                   ('Cruise_High', '#96CEB4'),
                                   ('Descent/Landing', '#FFEAA7')]:
            phase_data = valid_data[valid_data['altitude'].apply(
                lambda alt: (alt < 30 and phase_name == 'Ground/Takeoff') or
                           (30 <= alt < 60 and phase_name == 'Climb') or
                           (60 <= alt < 90 and phase_name == 'Cruise_Low') or
                           (90 <= alt < 110 and phase_name == 'Cruise_High') or
                           (alt >= 110 and phase_name == 'Descent/Landing')
            )]

            if len(phase_data) > 0:
                ax2.scatter(phase_data['distance_from_origin'],
                           phase_data['lte_rssi'],
                           c=color, label=phase_name, s=20, alpha=0.6)

        ax2.set_xlabel('Distance from Origin (m)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('LTE RSSI (dBm)', fontsize=12, fontweight='bold')
        ax2.set_title('비행 단계별 원점 거리-품질 관계',
                     fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='lower right', fontsize=9)

        plt.suptitle('핵심 발견: 원점에서 멀수록 LTE 품질 향상 (+0.533)',
                    fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()

        output_file = self.base_dir / "chart2_distance_vs_lte.png"
        plt.savefig(str(output_file), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {output_file}")

    def chart3_time_vs_starlink(self):
        """차트 3: 비행 시간 vs Starlink 지연 (색상: 고도)"""
        print("\n📊 Creating Chart 3: Flight Time vs Starlink Latency...")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        valid_data = self.df[self.df['starlink_latency'].notna()].copy()

        # 왼쪽: 비행 시간 vs Starlink 지연 (색상: 고도)
        scatter1 = ax1.scatter(valid_data['flight_time_elapsed'],
                              valid_data['starlink_latency'],
                              c=valid_data['altitude'], cmap='coolwarm',
                              s=20, alpha=0.6, edgecolors='none')
        ax1.set_xlabel('Flight Time Elapsed (s)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Starlink Latency (ms)', fontsize=12, fontweight='bold')
        ax1.set_title('비행 시간 경과 vs Starlink 지연 (색상: 고도)',
                     fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        cbar1 = plt.colorbar(scatter1, ax=ax1, label='Altitude (m)')

        corr = valid_data['flight_time_elapsed'].corr(valid_data['starlink_latency'])
        ax1.text(0.05, 0.95,
                f'Correlation: {corr:+.3f}\n(가장 강한 상관!)\n\n시간 경과 → 지연 증가\n(온도/배터리 영향 추정)',
                transform=ax1.transAxes, fontsize=11,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='#FFE6E6', alpha=0.9))

        # 오른쪽: 추세선 포함
        ax2.scatter(valid_data['flight_time_elapsed'],
                   valid_data['starlink_latency'],
                   c=valid_data['altitude'], cmap='coolwarm',
                   s=20, alpha=0.6, edgecolors='none')

        # 추세선 추가
        z = np.polyfit(valid_data['flight_time_elapsed'],
                      valid_data['starlink_latency'], 1)
        p = np.poly1d(z)
        ax2.plot(valid_data['flight_time_elapsed'],
                p(valid_data['flight_time_elapsed']),
                "r--", linewidth=2, label=f'Trend: y={z[0]:.3f}x+{z[1]:.1f}')

        ax2.set_xlabel('Flight Time Elapsed (s)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Starlink Latency (ms)', fontsize=12, fontweight='bold')
        ax2.set_title('지연 증가 추세 (선형 회귀)',
                     fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper left', fontsize=10)
        cbar2 = plt.colorbar(scatter1, ax=ax2, label='Altitude (m)')

        # 통계 정보
        latency_start = valid_data['starlink_latency'].iloc[:100].mean()
        latency_end = valid_data['starlink_latency'].iloc[-100:].mean()
        increase = latency_end - latency_start
        increase_pct = (increase / latency_start) * 100

        ax2.text(0.05, 0.95,
                f'시작: {latency_start:.1f}ms\n종료: {latency_end:.1f}ms\n증가: +{increase:.1f}ms ({increase_pct:.0f}%)',
                transform=ax2.transAxes, fontsize=11,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        plt.suptitle('CRITICAL: 비행 시간 경과가 Starlink 지연에 가장 큰 영향 (+0.586)',
                    fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()

        output_file = self.base_dir / "chart3_time_vs_starlink.png"
        plt.savefig(str(output_file), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {output_file}")

    def chart4_3d_altitude_speed_quality(self):
        """차트 4: 3D 산점도 - 고도 + 속도 + LTE RSSI"""
        print("\n📊 Creating Chart 4: 3D Scatter - Altitude + Speed + LTE Quality...")

        fig = plt.figure(figsize=(16, 12))

        # 3D 서브플롯 2개
        ax1 = fig.add_subplot(221, projection='3d')
        ax2 = fig.add_subplot(222, projection='3d')
        ax3 = fig.add_subplot(223)
        ax4 = fig.add_subplot(224)

        valid_data = self.df[(self.df['speed_mps'].notna()) &
                            (self.df['lte_rssi'].notna())].copy()

        # 3D 플롯 1: 고도 + 속도 + LTE RSSI (색상: RSSI)
        scatter1 = ax1.scatter(valid_data['altitude'],
                              valid_data['speed_mps'],
                              valid_data['lte_rssi'],
                              c=valid_data['lte_rssi'], cmap='RdYlGn',
                              s=20, alpha=0.6)
        ax1.set_xlabel('Altitude (m)', fontsize=10, fontweight='bold')
        ax1.set_ylabel('Speed (m/s)', fontsize=10, fontweight='bold')
        ax1.set_zlabel('LTE RSSI (dBm)', fontsize=10, fontweight='bold')
        ax1.set_title('3D: 고도 + 속도 + LTE 품질', fontsize=12, fontweight='bold')
        fig.colorbar(scatter1, ax=ax1, label='RSSI (dBm)', shrink=0.5)

        # 3D 플롯 2: 고도 + 거리 + LTE RSSI (색상: 비행 시간)
        scatter2 = ax2.scatter(valid_data['altitude'],
                              valid_data['distance_from_origin'],
                              valid_data['lte_rssi'],
                              c=valid_data['flight_time_elapsed'], cmap='plasma',
                              s=20, alpha=0.6)
        ax2.set_xlabel('Altitude (m)', fontsize=10, fontweight='bold')
        ax2.set_ylabel('Distance from Origin (m)', fontsize=10, fontweight='bold')
        ax2.set_zlabel('LTE RSSI (dBm)', fontsize=10, fontweight='bold')
        ax2.set_title('3D: 고도 + 원점거리 + LTE 품질', fontsize=12, fontweight='bold')
        fig.colorbar(scatter2, ax=ax2, label='Flight Time (s)', shrink=0.5)

        # 2D 투영 1: 고도 vs 속도 (색상: RSSI)
        scatter3 = ax3.scatter(valid_data['altitude'],
                              valid_data['speed_mps'],
                              c=valid_data['lte_rssi'], cmap='RdYlGn',
                              s=30, alpha=0.6, edgecolors='black', linewidth=0.5)
        ax3.set_xlabel('Altitude (m)', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Movement Speed (m/s)', fontsize=11, fontweight='bold')
        ax3.set_title('2D 투영: 고도 vs 속도 (색상: LTE RSSI)',
                     fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        fig.colorbar(scatter3, ax=ax3, label='LTE RSSI (dBm)')

        # 최고 품질 영역 표시
        best_quality = valid_data[valid_data['lte_rssi'] >= -75]
        ax3.scatter(best_quality['altitude'], best_quality['speed_mps'],
                   s=100, facecolors='none', edgecolors='red', linewidth=2,
                   label='Best Quality (RSSI ≥ -75dBm)')
        ax3.legend(loc='lower right')

        # 2D 투영 2: 속도 vs 거리 (색상: RSSI)
        scatter4 = ax4.scatter(valid_data['speed_mps'],
                              valid_data['distance_from_origin'],
                              c=valid_data['lte_rssi'], cmap='RdYlGn',
                              s=30, alpha=0.6, edgecolors='black', linewidth=0.5)
        ax4.set_xlabel('Movement Speed (m/s)', fontsize=11, fontweight='bold')
        ax4.set_ylabel('Distance from Origin (m)', fontsize=11, fontweight='bold')
        ax4.set_title('2D 투영: 속도 vs 원점거리 (색상: LTE RSSI)',
                     fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        fig.colorbar(scatter4, ax=ax4, label='LTE RSSI (dBm)')

        plt.suptitle('복합 요인 분석: 고도 + 속도 + 위치가 동시에 LTE 품질 결정',
                    fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        output_file = self.base_dir / "chart4_3d_multidimensional.png"
        plt.savefig(str(output_file), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {output_file}")

    def chart5_flight_path_map(self):
        """차트 5: 비행 경로 맵 (색상: 품질)"""
        print("\n📊 Creating Chart 5: Flight Path Map with Quality...")

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 14))

        # 1. LTE RSSI 품질 맵
        scatter1 = ax1.scatter(self.df['longitude'], self.df['latitude'],
                              c=self.df['lte_rssi'], cmap='RdYlGn',
                              s=50, alpha=0.7, edgecolors='black', linewidth=0.3)
        ax1.plot(self.df['longitude'], self.df['latitude'],
                'k-', alpha=0.2, linewidth=1, zorder=1)
        ax1.scatter(self.df['longitude'].iloc[0], self.df['latitude'].iloc[0],
                   c='green', s=200, marker='o', edgecolors='black', linewidth=2,
                   label='Start', zorder=5)
        ax1.scatter(self.df['longitude'].iloc[-1], self.df['latitude'].iloc[-1],
                   c='red', s=200, marker='X', edgecolors='black', linewidth=2,
                   label='End', zorder=5)
        ax1.set_xlabel('Longitude', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Latitude', fontsize=11, fontweight='bold')
        ax1.set_title('비행 경로 (색상: LTE RSSI)', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right')
        fig.colorbar(scatter1, ax=ax1, label='LTE RSSI (dBm)')

        # 2. Starlink 지연 맵
        valid_sl = self.df[self.df['starlink_latency'].notna()].copy()
        scatter2 = ax2.scatter(valid_sl['longitude'], valid_sl['latitude'],
                              c=valid_sl['starlink_latency'], cmap='RdYlGn_r',
                              s=50, alpha=0.7, edgecolors='black', linewidth=0.3)
        ax2.plot(self.df['longitude'], self.df['latitude'],
                'k-', alpha=0.2, linewidth=1, zorder=1)
        ax2.scatter(self.df['longitude'].iloc[0], self.df['latitude'].iloc[0],
                   c='green', s=200, marker='o', edgecolors='black', linewidth=2,
                   label='Start', zorder=5)
        ax2.scatter(self.df['longitude'].iloc[-1], self.df['latitude'].iloc[-1],
                   c='red', s=200, marker='X', edgecolors='black', linewidth=2,
                   label='End', zorder=5)
        ax2.set_xlabel('Longitude', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Latitude', fontsize=11, fontweight='bold')
        ax2.set_title('비행 경로 (색상: Starlink Latency)', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper right')
        fig.colorbar(scatter2, ax=ax2, label='Latency (ms)')

        # 3. 고도 맵
        scatter3 = ax3.scatter(self.df['longitude'], self.df['latitude'],
                              c=self.df['altitude'], cmap='terrain',
                              s=50, alpha=0.7, edgecolors='black', linewidth=0.3)
        ax3.plot(self.df['longitude'], self.df['latitude'],
                'k-', alpha=0.2, linewidth=1, zorder=1)
        ax3.scatter(self.df['longitude'].iloc[0], self.df['latitude'].iloc[0],
                   c='green', s=200, marker='o', edgecolors='black', linewidth=2,
                   label='Start', zorder=5)
        ax3.scatter(self.df['longitude'].iloc[-1], self.df['latitude'].iloc[-1],
                   c='red', s=200, marker='X', edgecolors='black', linewidth=2,
                   label='End', zorder=5)
        ax3.set_xlabel('Longitude', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Latitude', fontsize=11, fontweight='bold')
        ax3.set_title('비행 경로 (색상: 고도)', fontsize=13, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='upper right')
        fig.colorbar(scatter3, ax=ax3, label='Altitude (m)')

        # 4. 이동 속도 맵
        valid_speed = self.df[self.df['speed_mps'].notna()].copy()
        scatter4 = ax4.scatter(valid_speed['longitude'], valid_speed['latitude'],
                              c=valid_speed['speed_mps'], cmap='YlOrRd',
                              s=50, alpha=0.7, edgecolors='black', linewidth=0.3)
        ax4.plot(self.df['longitude'], self.df['latitude'],
                'k-', alpha=0.2, linewidth=1, zorder=1)
        ax4.scatter(self.df['longitude'].iloc[0], self.df['latitude'].iloc[0],
                   c='green', s=200, marker='o', edgecolors='black', linewidth=2,
                   label='Start', zorder=5)
        ax4.scatter(self.df['longitude'].iloc[-1], self.df['latitude'].iloc[-1],
                   c='red', s=200, marker='X', edgecolors='black', linewidth=2,
                   label='End', zorder=5)
        ax4.set_xlabel('Longitude', fontsize=11, fontweight='bold')
        ax4.set_ylabel('Latitude', fontsize=11, fontweight='bold')
        ax4.set_title('비행 경로 (색상: 이동 속도)', fontsize=13, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.legend(loc='upper right')
        fig.colorbar(scatter4, ax=ax4, label='Speed (m/s)')

        plt.suptitle('지리적 품질 분포: 위치별 통신 품질 및 비행 특성',
                    fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout(rect=[0, 0, 1, 0.99])

        output_file = self.base_dir / "chart5_flight_path_quality_map.png"
        plt.savefig(str(output_file), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {output_file}")

    def chart6_timeseries_multiaxis(self):
        """차트 6: 시계열 복합 차트 (4개 Y축)"""
        print("\n📊 Creating Chart 6: Multi-axis Time Series...")

        fig, ax1 = plt.subplots(figsize=(20, 8))

        # 주 Y축: LTE RSSI
        color1 = '#2E86AB'
        ax1.set_xlabel('Sample Index', fontsize=12, fontweight='bold')
        ax1.set_ylabel('LTE RSSI (dBm)', fontsize=12, fontweight='bold', color=color1)
        line1 = ax1.plot(self.df.index, self.df['lte_rssi'],
                        color=color1, linewidth=2, label='LTE RSSI', alpha=0.8)
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.grid(True, alpha=0.3)

        # 보조 Y축 1: 고도
        ax2 = ax1.twinx()
        color2 = '#A23B72'
        ax2.set_ylabel('Altitude (m)', fontsize=12, fontweight='bold', color=color2)
        line2 = ax2.plot(self.df.index, self.df['altitude'],
                        color=color2, linewidth=2, label='Altitude', alpha=0.7)
        ax2.tick_params(axis='y', labelcolor=color2)

        # 보조 Y축 2: 이동 속도
        ax3 = ax1.twinx()
        ax3.spines['right'].set_position(('outward', 60))
        color3 = '#F18F01'
        ax3.set_ylabel('Speed (m/s)', fontsize=12, fontweight='bold', color=color3)
        valid_speed = self.df[self.df['speed_mps'].notna()]
        line3 = ax3.plot(valid_speed.index, valid_speed['speed_mps'],
                        color=color3, linewidth=1.5, label='Speed', alpha=0.7)
        ax3.tick_params(axis='y', labelcolor=color3)

        # 보조 Y축 3: 원점 거리
        ax4 = ax1.twinx()
        ax4.spines['right'].set_position(('outward', 120))
        color4 = '#6A994E'
        ax4.set_ylabel('Distance from Origin (m)', fontsize=12, fontweight='bold', color=color4)
        line4 = ax4.plot(self.df.index, self.df['distance_from_origin'],
                        color=color4, linewidth=1.5, label='Distance', alpha=0.7, linestyle='--')
        ax4.tick_params(axis='y', labelcolor=color4)

        # 범례 통합
        lines = line1 + line2 + line3 + line4
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left', fontsize=11, framealpha=0.9)

        # 주요 구간 표시
        # 샘플 800-1200: 최고 품질 구간
        ax1.axvspan(800, 1200, alpha=0.2, color='green', label='Best Quality Zone')
        ax1.text(1000, ax1.get_ylim()[1]*0.95, 'BEST QUALITY\n(고고도+빠른이동+원거리)',
                ha='center', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

        # 샘플 0-310: Poor 구간
        ax1.axvspan(0, 310, alpha=0.2, color='red')
        ax1.text(155, ax1.get_ylim()[0]*1.05, 'Poor Quality\n(저고도+느린이동)',
                ha='center', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='#FFE6E6', alpha=0.8))

        plt.title('시계열 복합 분석: LTE 품질 + 고도 + 속도 + 위치 (4개 요인 동시 비교)',
                 fontsize=15, fontweight='bold', pad=20)

        plt.tight_layout()

        output_file = self.base_dir / "chart6_timeseries_multiaxis.png"
        plt.savefig(str(output_file), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {output_file}")

    def generate_all_charts(self):
        """모든 차트 생성"""
        self.load_data()

        self.chart1_speed_vs_lte()
        self.chart2_distance_vs_lte()
        self.chart3_time_vs_starlink()
        self.chart4_3d_altitude_speed_quality()
        self.chart5_flight_path_map()
        self.chart6_timeseries_multiaxis()

        print("\n" + "="*80)
        print("✅ ALL 6 MULTI-DIMENSIONAL CHARTS GENERATED")
        print("="*80)
        print("\n생성된 차트:")
        print("  1. chart1_speed_vs_lte.png - 이동 속도 vs LTE 품질")
        print("  2. chart2_distance_vs_lte.png - 원점 거리 vs LTE 품질")
        print("  3. chart3_time_vs_starlink.png - 비행 시간 vs Starlink 지연")
        print("  4. chart4_3d_multidimensional.png - 3D 복합 분석")
        print("  5. chart5_flight_path_quality_map.png - 비행 경로 품질 맵")
        print("  6. chart6_timeseries_multiaxis.png - 시계열 4축 복합")


def main():
    """메인 실행"""
    base_dir = Path(__file__).parent
    merged_data = base_dir / "merged_flight_data.csv"

    generator = MultidimensionalChartGenerator(str(merged_data))
    generator.generate_all_charts()


if __name__ == "__main__":
    main()
