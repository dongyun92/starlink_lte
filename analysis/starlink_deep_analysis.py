#!/usr/bin/env python3
"""
Starlink 심층 분석 - 비행 데이터 연동
Flight Log + Starlink 데이터 종합 분석
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class StarlinkDeepAnalyzer:
    """Starlink 심층 분석기 - 비행 데이터 연동"""

    def __init__(self, merged_data_path: str):
        self.data_path = Path(merged_data_path)
        self.df = None
        self.starlink_data = None

    def load_data(self):
        """데이터 로드"""
        print(f"📁 Loading merged data: {self.data_path.name}")
        self.df = pd.read_csv(self.data_path)

        # Starlink 데이터 필터링
        self.starlink_data = self.df[
            (self.df['starlink_available'] == True) |
            (self.df['starlink_latency'].notna())
        ].copy()

        print(f"✓ Loaded {len(self.starlink_data)} Starlink data points")

    def chart_altitude_vs_starlink(self, output_path: str):
        """고도 vs Starlink 품질 (4개 subplot)"""
        print("  ├─ 생성 중: 고도 vs Starlink 품질 분석...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. 고도 vs 지연시간
        ax1 = axes[0, 0]
        valid_data = self.starlink_data[
            (self.starlink_data['altitude'].notna()) &
            (self.starlink_data['starlink_latency'].notna())
        ].copy()

        if len(valid_data) > 0:
            scatter1 = ax1.scatter(valid_data['altitude'], valid_data['starlink_latency'],
                                  c=valid_data['speed_mps'] if 'speed_mps' in valid_data.columns else 'blue',
                                  cmap='plasma', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax1.set_xlabel('Altitude (m)', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Starlink Latency (ms)', fontsize=12, fontweight='bold')
            ax1.set_title('고도 vs Starlink 지연시간', fontsize=13, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            if 'speed_mps' in valid_data.columns:
                plt.colorbar(scatter1, ax=ax1, label='Speed (m/s)')

            # 추세선
            z = np.polyfit(valid_data['altitude'], valid_data['starlink_latency'], 2)
            p = np.poly1d(z)
            x_trend = np.linspace(valid_data['altitude'].min(), valid_data['altitude'].max(), 100)
            ax1.plot(x_trend, p(x_trend), "r--", alpha=0.8, linewidth=2, label='Trend')
            ax1.legend()

        # 2. 고도 vs 다운로드 처리량
        ax2 = axes[0, 1]
        valid_data2 = self.starlink_data[
            (self.starlink_data['altitude'].notna()) &
            (self.starlink_data['starlink_downlink_throughput_bps'].notna())
        ].copy()

        if len(valid_data2) > 0:
            scatter2 = ax2.scatter(valid_data2['altitude'],
                                  valid_data2['starlink_downlink_throughput_bps'] / 1e6,
                                  c=valid_data2['starlink_latency'] if 'starlink_latency' in valid_data2.columns else 'green',
                                  cmap='RdYlGn_r', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax2.set_xlabel('Altitude (m)', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Download Throughput (Mbps)', fontsize=12, fontweight='bold')
            ax2.set_title('고도 vs Starlink 다운로드 속도', fontsize=13, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            if 'starlink_latency' in valid_data2.columns:
                plt.colorbar(scatter2, ax=ax2, label='Latency (ms)')

        # 3. 고도 vs 업로드 처리량
        ax3 = axes[1, 0]
        valid_data3 = self.starlink_data[
            (self.starlink_data['altitude'].notna()) &
            (self.starlink_data['starlink_uplink_throughput_bps'].notna())
        ].copy()

        if len(valid_data3) > 0:
            scatter3 = ax3.scatter(valid_data3['altitude'],
                                  valid_data3['starlink_uplink_throughput_bps'] / 1e6,
                                  c=valid_data3['starlink_ping_drop_rate'] if 'starlink_ping_drop_rate' in valid_data3.columns else 'orange',
                                  cmap='Reds', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax3.set_xlabel('Altitude (m)', fontsize=12, fontweight='bold')
            ax3.set_ylabel('Upload Throughput (Mbps)', fontsize=12, fontweight='bold')
            ax3.set_title('고도 vs Starlink 업로드 속도', fontsize=13, fontweight='bold')
            ax3.grid(True, alpha=0.3)
            if 'starlink_ping_drop_rate' in valid_data3.columns:
                plt.colorbar(scatter3, ax=ax3, label='Ping Drop Rate')

        # 4. 고도 vs Ping Drop Rate
        ax4 = axes[1, 1]
        valid_data4 = self.starlink_data[
            (self.starlink_data['altitude'].notna()) &
            (self.starlink_data['starlink_ping_drop_rate'].notna())
        ].copy()

        if len(valid_data4) > 0:
            scatter4 = ax4.scatter(valid_data4['altitude'],
                                  valid_data4['starlink_ping_drop_rate'] * 100,
                                  c=valid_data4['starlink_latency'] if 'starlink_latency' in valid_data4.columns else 'red',
                                  cmap='YlOrRd', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax4.set_xlabel('Altitude (m)', fontsize=12, fontweight='bold')
            ax4.set_ylabel('Ping Drop Rate (%)', fontsize=12, fontweight='bold')
            ax4.set_title('고도 vs Ping 손실률', fontsize=13, fontweight='bold')
            ax4.grid(True, alpha=0.3)
            if 'starlink_latency' in valid_data4.columns:
                plt.colorbar(scatter4, ax=ax4, label='Latency (ms)')

        plt.suptitle('🛰️ Starlink 품질 vs 비행 고도 종합 분석', fontsize=16, fontweight='bold')
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(output_path, dpi=250, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 저장: {Path(output_path).name}")

    def chart_speed_vs_starlink(self, output_path: str):
        """속도 vs Starlink 품질"""
        print("  ├─ 생성 중: 이동 속도 vs Starlink 품질...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. 속도 vs 지연시간
        ax1 = axes[0, 0]
        valid_data = self.starlink_data[
            (self.starlink_data['speed_mps'].notna()) &
            (self.starlink_data['starlink_latency'].notna())
        ].copy()

        if len(valid_data) > 0:
            scatter1 = ax1.scatter(valid_data['speed_mps'], valid_data['starlink_latency'],
                                  c=valid_data['altitude'] if 'altitude' in valid_data.columns else 'blue',
                                  cmap='viridis', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax1.set_xlabel('Movement Speed (m/s)', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Starlink Latency (ms)', fontsize=12, fontweight='bold')
            ax1.set_title('이동 속도 vs Starlink 지연시간', fontsize=13, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            if 'altitude' in valid_data.columns:
                plt.colorbar(scatter1, ax=ax1, label='Altitude (m)')

        # 2. 속도 vs 다운로드 처리량
        ax2 = axes[0, 1]
        valid_data2 = self.starlink_data[
            (self.starlink_data['speed_mps'].notna()) &
            (self.starlink_data['starlink_downlink_throughput_bps'].notna())
        ].copy()

        if len(valid_data2) > 0:
            scatter2 = ax2.scatter(valid_data2['speed_mps'],
                                  valid_data2['starlink_downlink_throughput_bps'] / 1e6,
                                  c=valid_data2['altitude'] if 'altitude' in valid_data2.columns else 'green',
                                  cmap='viridis', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax2.set_xlabel('Movement Speed (m/s)', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Download Throughput (Mbps)', fontsize=12, fontweight='bold')
            ax2.set_title('이동 속도 vs Starlink 다운로드 속도', fontsize=13, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            if 'altitude' in valid_data2.columns:
                plt.colorbar(scatter2, ax=ax2, label='Altitude (m)')

        # 3. 속도 vs 업로드 처리량
        ax3 = axes[1, 0]
        valid_data3 = self.starlink_data[
            (self.starlink_data['speed_mps'].notna()) &
            (self.starlink_data['starlink_uplink_throughput_bps'].notna())
        ].copy()

        if len(valid_data3) > 0:
            scatter3 = ax3.scatter(valid_data3['speed_mps'],
                                  valid_data3['starlink_uplink_throughput_bps'] / 1e6,
                                  c=valid_data3['altitude'] if 'altitude' in valid_data3.columns else 'orange',
                                  cmap='viridis', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax3.set_xlabel('Movement Speed (m/s)', fontsize=12, fontweight='bold')
            ax3.set_ylabel('Upload Throughput (Mbps)', fontsize=12, fontweight='bold')
            ax3.set_title('이동 속도 vs Starlink 업로드 속도', fontsize=13, fontweight='bold')
            ax3.grid(True, alpha=0.3)
            if 'altitude' in valid_data3.columns:
                plt.colorbar(scatter3, ax=ax3, label='Altitude (m)')

        # 4. 속도 vs Ping Drop Rate
        ax4 = axes[1, 1]
        valid_data4 = self.starlink_data[
            (self.starlink_data['speed_mps'].notna()) &
            (self.starlink_data['starlink_ping_drop_rate'].notna())
        ].copy()

        if len(valid_data4) > 0:
            scatter4 = ax4.scatter(valid_data4['speed_mps'],
                                  valid_data4['starlink_ping_drop_rate'] * 100,
                                  c=valid_data4['altitude'] if 'altitude' in valid_data4.columns else 'red',
                                  cmap='YlOrRd', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax4.set_xlabel('Movement Speed (m/s)', fontsize=12, fontweight='bold')
            ax4.set_ylabel('Ping Drop Rate (%)', fontsize=12, fontweight='bold')
            ax4.set_title('이동 속도 vs Ping 손실률', fontsize=13, fontweight='bold')
            ax4.grid(True, alpha=0.3)
            if 'altitude' in valid_data4.columns:
                plt.colorbar(scatter4, ax=ax4, label='Altitude (m)')

        plt.suptitle('🚁 Starlink 품질 vs 이동 속도 종합 분석', fontsize=16, fontweight='bold')
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(output_path, dpi=250, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 저장: {Path(output_path).name}")

    def chart_distance_vs_starlink(self, output_path: str):
        """원점 거리 vs Starlink 품질"""
        print("  ├─ 생성 중: 원점 거리 vs Starlink 품질...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. 거리 vs 지연시간
        ax1 = axes[0, 0]
        valid_data = self.starlink_data[
            (self.starlink_data['distance_from_origin'].notna()) &
            (self.starlink_data['starlink_latency'].notna())
        ].copy()

        if len(valid_data) > 0:
            scatter1 = ax1.scatter(valid_data['distance_from_origin'], valid_data['starlink_latency'],
                                  c=valid_data['altitude'] if 'altitude' in valid_data.columns else 'blue',
                                  cmap='coolwarm', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax1.set_xlabel('Distance from Origin (m)', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Starlink Latency (ms)', fontsize=12, fontweight='bold')
            ax1.set_title('원점 거리 vs Starlink 지연시간', fontsize=13, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            if 'altitude' in valid_data.columns:
                plt.colorbar(scatter1, ax=ax1, label='Altitude (m)')

        # 2. 거리 vs 다운로드 처리량
        ax2 = axes[0, 1]
        valid_data2 = self.starlink_data[
            (self.starlink_data['distance_from_origin'].notna()) &
            (self.starlink_data['starlink_downlink_throughput_bps'].notna())
        ].copy()

        if len(valid_data2) > 0:
            scatter2 = ax2.scatter(valid_data2['distance_from_origin'],
                                  valid_data2['starlink_downlink_throughput_bps'] / 1e6,
                                  c=valid_data2['altitude'] if 'altitude' in valid_data2.columns else 'green',
                                  cmap='coolwarm', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax2.set_xlabel('Distance from Origin (m)', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Download Throughput (Mbps)', fontsize=12, fontweight='bold')
            ax2.set_title('원점 거리 vs Starlink 다운로드 속도', fontsize=13, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            if 'altitude' in valid_data2.columns:
                plt.colorbar(scatter2, ax=ax2, label='Altitude (m)')

        # 3. 거리 vs 연결 상태 (state)
        ax3 = axes[1, 0]
        if 'starlink_state' in self.starlink_data.columns:
            state_data = self.starlink_data[
                (self.starlink_data['distance_from_origin'].notna()) &
                (self.starlink_data['starlink_state'].notna())
            ].copy()

            if len(state_data) > 0:
                # 상태를 숫자로 변환
                state_map = {'CONNECTED': 2, 'SEARCHING': 1, 'DISCONNECTED': 0}
                state_data['state_numeric'] = state_data['starlink_state'].map(state_map).fillna(0)

                scatter3 = ax3.scatter(state_data['distance_from_origin'], state_data['state_numeric'],
                                      c=state_data['altitude'] if 'altitude' in state_data.columns else 'orange',
                                      cmap='coolwarm', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
                ax3.set_xlabel('Distance from Origin (m)', fontsize=12, fontweight='bold')
                ax3.set_ylabel('Connection State', fontsize=12, fontweight='bold')
                ax3.set_yticks([0, 1, 2])
                ax3.set_yticklabels(['Disconnected', 'Searching', 'Connected'])
                ax3.set_title('원점 거리 vs Starlink 연결 상태', fontsize=13, fontweight='bold')
                ax3.grid(True, alpha=0.3)
                if 'altitude' in state_data.columns:
                    plt.colorbar(scatter3, ax=ax3, label='Altitude (m)')

        # 4. 거리 vs Ping Drop Rate
        ax4 = axes[1, 1]
        valid_data4 = self.starlink_data[
            (self.starlink_data['distance_from_origin'].notna()) &
            (self.starlink_data['starlink_ping_drop_rate'].notna())
        ].copy()

        if len(valid_data4) > 0:
            scatter4 = ax4.scatter(valid_data4['distance_from_origin'],
                                  valid_data4['starlink_ping_drop_rate'] * 100,
                                  c=valid_data4['altitude'] if 'altitude' in valid_data4.columns else 'red',
                                  cmap='YlOrRd', s=40, alpha=0.6, edgecolors='black', linewidth=0.5)
            ax4.set_xlabel('Distance from Origin (m)', fontsize=12, fontweight='bold')
            ax4.set_ylabel('Ping Drop Rate (%)', fontsize=12, fontweight='bold')
            ax4.set_title('원점 거리 vs Ping 손실률', fontsize=13, fontweight='bold')
            ax4.grid(True, alpha=0.3)
            if 'altitude' in valid_data4.columns:
                plt.colorbar(scatter4, ax=ax4, label='Altitude (m)')

        plt.suptitle('📍 Starlink 품질 vs 원점 거리 종합 분석', fontsize=16, fontweight='bold')
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(output_path, dpi=250, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 저장: {Path(output_path).name}")

    def chart_starlink_throughput_timeseries(self, output_path: str):
        """Starlink 처리량 시계열 분석"""
        print("  ├─ 생성 중: Starlink 처리량 시계열...")

        fig, axes = plt.subplots(3, 1, figsize=(16, 12))

        # 1. 다운로드/업로드 처리량
        ax1 = axes[0]
        valid_data = self.starlink_data[
            (self.starlink_data['starlink_downlink_throughput_bps'].notna()) |
            (self.starlink_data['starlink_uplink_throughput_bps'].notna())
        ].copy()

        if len(valid_data) > 0:
            if 'starlink_downlink_throughput_bps' in valid_data.columns:
                ax1.plot(valid_data.index, valid_data['starlink_downlink_throughput_bps'] / 1e6,
                        color='steelblue', linewidth=2, label='Downlink', alpha=0.8)
            if 'starlink_uplink_throughput_bps' in valid_data.columns:
                ax1.plot(valid_data.index, valid_data['starlink_uplink_throughput_bps'] / 1e6,
                        color='coral', linewidth=2, label='Uplink', alpha=0.8)

            ax1.set_ylabel('Throughput (Mbps)', fontsize=12, fontweight='bold')
            ax1.set_title('Starlink 다운로드/업로드 처리량 변화', fontsize=13, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            ax1.legend(fontsize=10)

        # 2. 지연시간
        ax2 = axes[1]
        latency_data = self.starlink_data[self.starlink_data['starlink_latency'].notna()].copy()

        if len(latency_data) > 0:
            ax2.plot(latency_data.index, latency_data['starlink_latency'],
                    color='purple', linewidth=2, alpha=0.8)
            ax2.fill_between(latency_data.index, latency_data['starlink_latency'],
                            alpha=0.3, color='purple')
            ax2.set_ylabel('Latency (ms)', fontsize=12, fontweight='bold')
            ax2.set_title('Starlink 지연시간 변화', fontsize=13, fontweight='bold')
            ax2.grid(True, alpha=0.3)

            # 평균선
            mean_latency = latency_data['starlink_latency'].mean()
            ax2.axhline(y=mean_latency, color='red', linestyle='--', linewidth=2,
                       label=f'평균: {mean_latency:.1f} ms', alpha=0.7)
            ax2.legend(fontsize=10)

        # 3. Ping Drop Rate
        ax3 = axes[2]
        drop_data = self.starlink_data[self.starlink_data['starlink_ping_drop_rate'].notna()].copy()

        if len(drop_data) > 0:
            ax3.plot(drop_data.index, drop_data['starlink_ping_drop_rate'] * 100,
                    color='red', linewidth=2, marker='o', markersize=3, alpha=0.8)
            ax3.fill_between(drop_data.index, drop_data['starlink_ping_drop_rate'] * 100,
                            alpha=0.3, color='red')
            ax3.set_xlabel('Sample Index', fontsize=12, fontweight='bold')
            ax3.set_ylabel('Ping Drop Rate (%)', fontsize=12, fontweight='bold')
            ax3.set_title('Starlink Ping 손실률 변화', fontsize=13, fontweight='bold')
            ax3.grid(True, alpha=0.3)

            # 경고선 (5% 이상)
            ax3.axhline(y=5, color='orange', linestyle='--', linewidth=2,
                       label='경고 (5%)', alpha=0.7)
            ax3.legend(fontsize=10)

        plt.suptitle('⏱️ Starlink 품질 지표 시계열 분석', fontsize=16, fontweight='bold')
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(output_path, dpi=250, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 저장: {Path(output_path).name}")

    def chart_3d_altitude_speed_starlink(self, output_path: str):
        """3D: 고도-속도-Starlink 품질"""
        print("  ├─ 생성 중: 3D 고도-속도-Starlink 품질...")

        from mpl_toolkits.mplot3d import Axes3D

        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')

        valid_data = self.starlink_data[
            (self.starlink_data['altitude'].notna()) &
            (self.starlink_data['speed_mps'].notna()) &
            (self.starlink_data['starlink_latency'].notna())
        ].copy()

        if len(valid_data) > 0:
            scatter = ax.scatter(valid_data['altitude'],
                               valid_data['speed_mps'],
                               valid_data['starlink_latency'],
                               c=valid_data['starlink_downlink_throughput_bps'] / 1e6
                                 if 'starlink_downlink_throughput_bps' in valid_data.columns else 'blue',
                               cmap='RdYlGn', s=50, alpha=0.7, edgecolors='black', linewidth=0.5)

            ax.set_xlabel('Altitude (m)', fontsize=12, fontweight='bold', labelpad=10)
            ax.set_ylabel('Speed (m/s)', fontsize=12, fontweight='bold', labelpad=10)
            ax.set_zlabel('Starlink Latency (ms)', fontsize=12, fontweight='bold', labelpad=10)
            ax.set_title('3D: 고도 - 속도 - Starlink 지연시간', fontsize=14, fontweight='bold', pad=20)

            if 'starlink_downlink_throughput_bps' in valid_data.columns:
                plt.colorbar(scatter, ax=ax, label='Download (Mbps)', shrink=0.5, pad=0.1)

            # 회전 각도 설정
            ax.view_init(elev=20, azim=45)

        plt.tight_layout()
        plt.savefig(output_path, dpi=250, bbox_inches='tight')
        plt.close()
        print(f"    ✓ 저장: {Path(output_path).name}")

    def generate_all_charts(self, output_folder: Path):
        """모든 Starlink 심층 분석 차트 생성"""
        print("\n🛰️ Starlink 심층 분석 차트 생성 중...")

        output_folder = Path(output_folder)
        output_folder.mkdir(exist_ok=True)

        # 데이터 로드
        self.load_data()

        # 1. 고도 vs Starlink 품질
        self.chart_altitude_vs_starlink(
            str(output_folder / 'starlink_altitude_analysis.png')
        )

        # 2. 속도 vs Starlink 품질
        self.chart_speed_vs_starlink(
            str(output_folder / 'starlink_speed_analysis.png')
        )

        # 3. 거리 vs Starlink 품질
        self.chart_distance_vs_starlink(
            str(output_folder / 'starlink_distance_analysis.png')
        )

        # 4. Starlink 처리량 시계열
        self.chart_starlink_throughput_timeseries(
            str(output_folder / 'starlink_throughput_timeseries.png')
        )

        # 5. 3D 고도-속도-Starlink
        self.chart_3d_altitude_speed_starlink(
            str(output_folder / 'starlink_3d_altitude_speed.png')
        )

        print("  └─ ✓ Starlink 심층 분석 차트 생성 완료 (5개)")


def main():
    """테스트 실행"""
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python starlink_deep_analysis.py <merged_data.csv>")
        sys.exit(1)

    merged_data_path = sys.argv[1]
    output_folder = Path(merged_data_path).parent / 'charts'

    analyzer = StarlinkDeepAnalyzer(merged_data_path)
    analyzer.generate_all_charts(output_folder)

    print("\n✅ Starlink 심층 분석 완료!")


if __name__ == "__main__":
    main()
