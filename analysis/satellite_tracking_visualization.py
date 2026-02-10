#!/usr/bin/env python3
"""
Starlink 위성 추적 시각화
- 방위각/고도각 변화 분석
- 위성 위치와 통신 품질 상관관계
- 위성 전환 이벤트 탐지
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class SatelliteTrackingVisualizer:
    """위성 추적 시각화 클래스"""

    def __init__(self, merged_data_path: str):
        self.data_path = Path(merged_data_path)
        self.df = None
        self.starlink_data = None

    def load_data(self):
        """데이터 로드"""
        print(f"📁 Loading merged data: {self.data_path.name}")
        self.df = pd.read_csv(self.data_path)

        # Starlink 데이터만 필터링
        self.starlink_data = self.df[self.df['starlink_available'] == True].copy()

        print(f"✓ Loaded {len(self.starlink_data)} Starlink data points")
        print(f"  Azimuth range: [{self.starlink_data['starlink_azimuth'].min():.1f}°, "
              f"{self.starlink_data['starlink_azimuth'].max():.1f}°]")
        print(f"  Elevation range: [{self.starlink_data['starlink_elevation'].min():.1f}°, "
              f"{self.starlink_data['starlink_elevation'].max():.1f}°]")

    def create_satellite_position_plot(self, output_path: str = "satellite_position_polar.png"):
        """극좌표 위성 위치 플롯"""
        print(f"\n🛰️ Creating Satellite Position Polar Plot...")

        fig = plt.figure(figsize=(16, 10))

        # 1. Polar plot (azimuth/elevation)
        ax1 = plt.subplot(2, 3, 1, projection='polar')

        # Azimuth을 라디안으로 변환
        azimuth_rad = np.deg2rad(self.starlink_data['starlink_azimuth'])

        # Elevation을 반지름으로 (90° - elevation = radius)
        # 고도각 90°가 중심, 0°가 바깥쪽
        radius = 90 - self.starlink_data['starlink_elevation']

        # 시간에 따른 색상 그라디언트
        scatter = ax1.scatter(azimuth_rad, radius,
                             c=range(len(self.starlink_data)),
                             cmap='viridis', s=20, alpha=0.6)

        ax1.set_theta_zero_location('N')  # 북쪽을 0°로
        ax1.set_theta_direction(-1)  # 시계방향
        ax1.set_ylim(0, 90)
        ax1.set_yticks([0, 30, 60, 90])
        ax1.set_yticklabels(['90° (Zenith)', '60°', '30°', '0° (Horizon)'])
        ax1.set_title('Satellite Position\n(Azimuth-Elevation)', fontsize=12, pad=20)
        ax1.grid(True, alpha=0.3)

        plt.colorbar(scatter, ax=ax1, label='Time Progress', pad=0.1)

        # 2. Azimuth 시계열
        ax2 = plt.subplot(2, 3, 2)
        ax2.plot(self.starlink_data.index, self.starlink_data['starlink_azimuth'],
                 color='steelblue', linewidth=1.5)
        ax2.set_xlabel('Sample Index', fontsize=10)
        ax2.set_ylabel('Azimuth (°)', fontsize=10)
        ax2.set_title('Satellite Azimuth Over Time', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=1)

        # 3. Elevation 시계열
        ax3 = plt.subplot(2, 3, 3)
        ax3.plot(self.starlink_data.index, self.starlink_data['starlink_elevation'],
                 color='coral', linewidth=1.5)
        ax3.set_xlabel('Sample Index', fontsize=10)
        ax3.set_ylabel('Elevation (°)', fontsize=10)
        ax3.set_title('Satellite Elevation Over Time', fontsize=12)
        ax3.grid(True, alpha=0.3)
        ax3.axhline(y=25, color='orange', linestyle='--', alpha=0.5, linewidth=1,
                   label='Min Recommended (25°)')
        ax3.legend(fontsize=8)

        # 4. Elevation vs Latency 상관관계
        ax4 = plt.subplot(2, 3, 4)
        scatter = ax4.scatter(self.starlink_data['starlink_elevation'],
                            self.starlink_data['starlink_latency'],
                            c=self.starlink_data['starlink_azimuth'],
                            cmap='twilight', s=30, alpha=0.6)
        ax4.set_xlabel('Elevation (°)', fontsize=10)
        ax4.set_ylabel('Latency (ms)', fontsize=10)
        ax4.set_title('Elevation vs Latency', fontsize=12)
        ax4.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax4, label='Azimuth (°)')

        # 상관계수 계산
        corr = self.starlink_data['starlink_elevation'].corr(
            self.starlink_data['starlink_latency'])
        ax4.text(0.05, 0.95, f'Correlation: {corr:.3f}',
                transform=ax4.transAxes, fontsize=9,
                verticalalignment='top', bbox=dict(boxstyle='round',
                facecolor='wheat', alpha=0.5))

        # 5. Elevation vs Download Speed
        ax5 = plt.subplot(2, 3, 5)
        scatter = ax5.scatter(self.starlink_data['starlink_elevation'],
                            self.starlink_data['starlink_download'],
                            c=self.starlink_data['starlink_latency'],
                            cmap='RdYlGn_r', s=30, alpha=0.6)
        ax5.set_xlabel('Elevation (°)', fontsize=10)
        ax5.set_ylabel('Download Speed (Mbps)', fontsize=10)
        ax5.set_title('Elevation vs Download Speed', fontsize=12)
        ax5.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax5, label='Latency (ms)')

        corr = self.starlink_data['starlink_elevation'].corr(
            self.starlink_data['starlink_download'])
        ax5.text(0.05, 0.95, f'Correlation: {corr:.3f}',
                transform=ax5.transAxes, fontsize=9,
                verticalalignment='top', bbox=dict(boxstyle='round',
                facecolor='wheat', alpha=0.5))

        # 6. GPS Satellites Count 시계열
        ax6 = plt.subplot(2, 3, 6)
        ax6.plot(self.starlink_data.index, self.starlink_data['starlink_gps_sats'],
                 color='green', linewidth=1.5, marker='o', markersize=3)
        ax6.set_xlabel('Sample Index', fontsize=10)
        ax6.set_ylabel('GPS Satellites Count', fontsize=10)
        ax6.set_title('GPS Satellites Tracked Over Time', fontsize=12)
        ax6.grid(True, alpha=0.3)
        ax6.axhline(y=12, color='orange', linestyle='--', alpha=0.5, linewidth=1,
                   label='Good (≥12 sats)')
        ax6.legend(fontsize=8)

        plt.suptitle('Starlink Satellite Tracking Analysis',
                    fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        output_file = Path(self.data_path).parent / output_path
        plt.savefig(str(output_file), dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Saved satellite position plot: {output_file}")

    def analyze_satellite_transitions(self):
        """위성 전환 분석"""
        print(f"\n🔄 Analyzing Satellite Transitions...")

        # Azimuth 급변 탐지 (30° 이상 변화)
        azimuth_diff = self.starlink_data['starlink_azimuth'].diff().abs()
        azimuth_transitions = azimuth_diff[azimuth_diff > 30]

        # Elevation 급변 탐지 (10° 이상 변화)
        elevation_diff = self.starlink_data['starlink_elevation'].diff().abs()
        elevation_transitions = elevation_diff[elevation_diff > 10]

        print(f"\n📊 Transition Statistics:")
        print(f"  Azimuth transitions (>30°): {len(azimuth_transitions)}")
        print(f"  Elevation transitions (>10°): {len(elevation_transitions)}")

        if len(azimuth_transitions) > 0:
            print(f"\n  Major azimuth changes:")
            for idx in azimuth_transitions.head(5).index:
                prev_idx = idx - 1
                if prev_idx in self.starlink_data.index:
                    print(f"    Sample {idx}: {self.starlink_data.loc[prev_idx, 'starlink_azimuth']:.1f}° → "
                          f"{self.starlink_data.loc[idx, 'starlink_azimuth']:.1f}° "
                          f"(Δ{azimuth_diff.loc[idx]:.1f}°)")

        return {
            'azimuth_transitions': len(azimuth_transitions),
            'elevation_transitions': len(elevation_transitions)
        }

    def create_quality_correlation_heatmap(self, output_path: str = "satellite_quality_correlation.png"):
        """위성 각도와 품질 메트릭 상관관계 히트맵"""
        print(f"\n📊 Creating Quality Correlation Heatmap...")

        # 분석할 메트릭 선택
        metrics = [
            'starlink_azimuth',
            'starlink_elevation',
            'starlink_gps_sats',
            'starlink_latency',
            'starlink_download',
            'starlink_upload'
        ]

        # 상관관계 행렬 계산
        corr_matrix = self.starlink_data[metrics].corr()

        # 히트맵 생성
        fig, ax = plt.subplots(figsize=(10, 8))

        sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='RdBu_r',
                   center=0, vmin=-1, vmax=1, square=True,
                   linewidths=1, cbar_kws={'label': 'Correlation Coefficient'},
                   ax=ax)

        ax.set_title('Satellite Position vs Quality Metrics Correlation',
                    fontsize=14, fontweight='bold', pad=20)

        # 축 라벨 개선
        labels = [
            'Azimuth (°)',
            'Elevation (°)',
            'GPS Satellites',
            'Latency (ms)',
            'Download (Mbps)',
            'Upload (Mbps)'
        ]
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_yticklabels(labels, rotation=0)

        plt.tight_layout()

        output_file = Path(self.data_path).parent / output_path
        plt.savefig(str(output_file), dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Saved correlation heatmap: {output_file}")

        # 주요 상관관계 출력
        print(f"\n🔍 Key Correlations:")
        print(f"  Elevation ↔ Latency: {corr_matrix.loc['starlink_elevation', 'starlink_latency']:.3f}")
        print(f"  Elevation ↔ Download: {corr_matrix.loc['starlink_elevation', 'starlink_download']:.3f}")
        print(f"  GPS Sats ↔ Latency: {corr_matrix.loc['starlink_gps_sats', 'starlink_latency']:.3f}")
        print(f"  Azimuth ↔ Latency: {corr_matrix.loc['starlink_azimuth', 'starlink_latency']:.3f}")

    def comprehensive_analysis(self):
        """종합 위성 추적 분석"""
        print("\n" + "="*80)
        print("🛰️ COMPREHENSIVE SATELLITE TRACKING ANALYSIS")
        print("="*80)

        # 데이터 로드
        self.load_data()

        # 위성 위치 플롯
        self.create_satellite_position_plot()

        # 위성 전환 분석
        transitions = self.analyze_satellite_transitions()

        # 상관관계 히트맵
        self.create_quality_correlation_heatmap()

        print("\n" + "="*80)
        print("✅ Satellite Tracking Analysis Complete!")
        print("="*80)

        return transitions


def main():
    """메인 실행"""
    print("="*80)
    print("🛰️ STARLINK SATELLITE TRACKING VISUALIZER")
    print("="*80)

    # 경로 설정
    base_dir = Path(__file__).parent
    merged_data = base_dir / "merged_flight_data.csv"

    # 시각화 생성기
    visualizer = SatelliteTrackingVisualizer(str(merged_data))

    # 종합 분석 실행
    results = visualizer.comprehensive_analysis()

    print("\n📁 Generated files:")
    print(f"  - satellite_position_polar.png")
    print(f"  - satellite_quality_correlation.png")


if __name__ == "__main__":
    main()
