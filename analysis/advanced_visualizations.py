#!/usr/bin/env python3
"""
고급 통신 품질 시각화 시스템
- 멀티 메트릭 히트맵 (RSSI, RSRP, RSRQ, SINR)
- 상관관계 매트릭스
- 시계열 다중 비교
- 품질 변동성 분석
"""

import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class AdvancedVisualizations:
    """고급 시각화 생성기"""

    def __init__(self, merged_data_path: str):
        self.data_path = Path(merged_data_path)
        self.df = None
        self.center_lat = None
        self.center_lon = None

    def load_data(self):
        """데이터 로드 및 준비"""
        print(f"📁 Loading merged data: {self.data_path.name}")
        self.df = pd.read_csv(self.data_path)

        # -999 값 필터링
        self.df.loc[self.df['lte_rsrp'] == -999, 'lte_rsrp'] = np.nan
        self.df.loc[self.df['lte_rsrq'] == -999, 'lte_rsrq'] = np.nan
        self.df.loc[self.df['lte_sinr'] == -999, 'lte_sinr'] = np.nan

        # 중심점 계산
        self.center_lat = self.df['latitude'].mean()
        self.center_lon = self.df['longitude'].mean()

        print(f"✓ Loaded {len(self.df)} data points")
        print(f"  Center: ({self.center_lat:.6f}, {self.center_lon:.6f})")

    def create_multi_metric_heatmap(self, output_path: str = "multi_metric_heatmap.html"):
        """멀티 메트릭 레이어 히트맵"""
        print(f"\n🗺️  Creating Multi-Metric Heatmap...")

        # 지도 생성
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=14,
            tiles='OpenStreetMap'
        )

        lte_data = self.df[self.df['lte_available'] == True].copy()

        # 1. RSSI 레이어
        lte_data['rssi_norm'] = (lte_data['lte_rssi'] + 113) / (51 - (-113))
        rssi_heat = [
            [row['latitude'], row['longitude'], row['rssi_norm']]
            for _, row in lte_data.iterrows() if not pd.isna(row['rssi_norm'])
        ]
        HeatMap(
            rssi_heat,
            name='RSSI (Signal Strength)',
            min_opacity=0.3,
            radius=15,
            gradient={0.0: 'red', 0.5: 'yellow', 1.0: 'green'}
        ).add_to(m)

        # 2. RSRP 레이어
        lte_rsrp_valid = lte_data[lte_data['lte_rsrp'].notna()].copy()
        if len(lte_rsrp_valid) > 0:
            lte_rsrp_valid['rsrp_norm'] = (lte_rsrp_valid['lte_rsrp'] + 120) / (50 - (-120))
            rsrp_heat = [
                [row['latitude'], row['longitude'], row['rsrp_norm']]
                for _, row in lte_rsrp_valid.iterrows() if not pd.isna(row['rsrp_norm'])
            ]
            HeatMap(
                rsrp_heat,
                name='RSRP (Reference Power)',
                min_opacity=0.3,
                radius=15,
                gradient={0.0: 'darkred', 0.5: 'orange', 1.0: 'lightgreen'}
            ).add_to(m)

        # 3. SINR 레이어
        lte_sinr_valid = lte_data[lte_data['lte_sinr'].notna()].copy()
        if len(lte_sinr_valid) > 0:
            lte_sinr_valid['sinr_norm'] = (lte_sinr_valid['lte_sinr'] + 10) / (30 - (-10))
            lte_sinr_valid['sinr_norm'] = lte_sinr_valid['sinr_norm'].clip(0, 1)
            sinr_heat = [
                [row['latitude'], row['longitude'], row['sinr_norm']]
                for _, row in lte_sinr_valid.iterrows() if not pd.isna(row['sinr_norm'])
            ]
            HeatMap(
                sinr_heat,
                name='SINR (Quality Indicator)',
                min_opacity=0.3,
                radius=15,
                gradient={0.0: 'purple', 0.5: 'yellow', 1.0: 'cyan'}
            ).add_to(m)

        # 4. Starlink Latency 레이어 (비교용)
        sl_data = self.df[self.df['starlink_available'] == True].copy()
        if len(sl_data) > 0:
            sl_data['latency_norm'] = 1 - (sl_data['starlink_latency'].clip(0, 150) / 150)
            sl_heat = [
                [row['latitude'], row['longitude'], row['latency_norm']]
                for _, row in sl_data.iterrows()
            ]
            HeatMap(
                sl_heat,
                name='Starlink Latency',
                min_opacity=0.3,
                radius=18,
                gradient={0.0: 'red', 0.5: 'yellow', 1.0: 'blue'}
            ).add_to(m)

        # 레이어 컨트롤
        folium.LayerControl(collapsed=False).add_to(m)

        # 범례 추가
        legend_html = '''
        <div style="position: fixed; bottom: 50px; left: 50px; width: 250px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:12px; padding: 10px;">
        <b>Quality Metrics Layers</b><br>
        🟢 <b>RSSI</b>: Overall signal strength<br>
        🟡 <b>RSRP</b>: Reference power level<br>
        🔵 <b>SINR</b>: Signal quality vs noise<br>
        🔴 <b>Starlink</b>: Latency performance<br><br>
        <i>Toggle layers in top-right corner</i>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # 저장
        output_file = Path(self.data_path).parent / output_path
        m.save(str(output_file))
        print(f"✓ Saved multi-metric heatmap: {output_file}")

    def create_correlation_heatmap(self, output_path: str = "correlation_heatmap.png"):
        """상관관계 히트맵"""
        print(f"\n📊 Creating Correlation Matrix...")

        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # LTE 상관관계
        lte_metrics = ['lte_rssi', 'lte_rsrp', 'lte_rsrq', 'lte_sinr']
        lte_corr = self.df[self.df['lte_available'] == True][lte_metrics].corr()

        sns.heatmap(lte_corr, annot=True, fmt='.3f', cmap='coolwarm',
                   center=0, vmin=-1, vmax=1,
                   square=True, linewidths=1,
                   cbar_kws={'label': 'Correlation'},
                   ax=axes[0])
        axes[0].set_title('LTE Metrics Correlation', fontsize=14, fontweight='bold')
        axes[0].set_xticklabels(['RSSI', 'RSRP', 'RSRQ', 'SINR'])
        axes[0].set_yticklabels(['RSSI', 'RSRP', 'RSRQ', 'SINR'], rotation=0)

        # Starlink 상관관계
        sl_metrics = ['starlink_latency', 'starlink_download', 'starlink_upload']
        sl_corr = self.df[self.df['starlink_available'] == True][sl_metrics].corr()

        sns.heatmap(sl_corr, annot=True, fmt='.3f', cmap='viridis',
                   center=0, vmin=-1, vmax=1,
                   square=True, linewidths=1,
                   cbar_kws={'label': 'Correlation'},
                   ax=axes[1])
        axes[1].set_title('Starlink Metrics Correlation', fontsize=14, fontweight='bold')
        axes[1].set_xticklabels(['Latency', 'Download', 'Upload'])
        axes[1].set_yticklabels(['Latency', 'Download', 'Upload'], rotation=0)

        plt.tight_layout()

        # 저장
        output_file = Path(self.data_path).parent / output_path
        plt.savefig(str(output_file), dpi=150, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved correlation heatmap: {output_file}")

    def create_time_series_comparison(self, output_path: str = "time_series_comparison.png"):
        """시계열 다중 메트릭 비교"""
        print(f"\n📈 Creating Time Series Comparison...")

        fig, axes = plt.subplots(3, 2, figsize=(16, 12))

        lte_data = self.df[self.df['lte_available'] == True].reset_index(drop=True)
        sl_data = self.df[self.df['starlink_available'] == True].reset_index(drop=True)

        # LTE 메트릭들
        # 1. RSSI
        axes[0, 0].plot(lte_data.index, lte_data['lte_rssi'], linewidth=0.5, alpha=0.7, color='blue')
        axes[0, 0].axhline(y=-70, color='green', linestyle='--', label='Excellent')
        axes[0, 0].axhline(y=-85, color='orange', linestyle='--', label='Good')
        axes[0, 0].set_title('LTE RSSI Over Time')
        axes[0, 0].set_ylabel('RSSI (dBm)')
        axes[0, 0].legend(loc='upper right')
        axes[0, 0].grid(True, alpha=0.3)

        # 2. RSRP
        axes[0, 1].plot(lte_data.index, lte_data['lte_rsrp'], linewidth=0.5, alpha=0.7, color='green')
        axes[0, 1].set_title('LTE RSRP Over Time')
        axes[0, 1].set_ylabel('RSRP (dBm)')
        axes[0, 1].grid(True, alpha=0.3)

        # 3. RSRQ
        axes[1, 0].plot(lte_data.index, lte_data['lte_rsrq'], linewidth=0.5, alpha=0.7, color='orange')
        axes[1, 0].set_title('LTE RSRQ Over Time')
        axes[1, 0].set_ylabel('RSRQ (dB)')
        axes[1, 0].grid(True, alpha=0.3)

        # 4. SINR
        axes[1, 1].plot(lte_data.index, lte_data['lte_sinr'], linewidth=0.5, alpha=0.7, color='red')
        axes[1, 1].axhline(y=20, color='green', linestyle='--', label='Excellent')
        axes[1, 1].axhline(y=13, color='orange', linestyle='--', label='Good')
        axes[1, 1].set_title('LTE SINR Over Time')
        axes[1, 1].set_ylabel('SINR (dB)')
        axes[1, 1].legend(loc='upper right')
        axes[1, 1].grid(True, alpha=0.3)

        # Starlink 메트릭들
        # 5. Latency
        axes[2, 0].plot(sl_data.index, sl_data['starlink_latency'], linewidth=0.5, alpha=0.7, color='purple')
        axes[2, 0].axhline(y=40, color='green', linestyle='--', label='Excellent')
        axes[2, 0].axhline(y=100, color='orange', linestyle='--', label='Good')
        axes[2, 0].set_title('Starlink Latency Over Time')
        axes[2, 0].set_ylabel('Latency (ms)')
        axes[2, 0].set_xlabel('Sample Index')
        axes[2, 0].legend(loc='upper right')
        axes[2, 0].grid(True, alpha=0.3)

        # 6. Throughput
        axes[2, 1].plot(sl_data.index, sl_data['starlink_download'], linewidth=0.5, alpha=0.7, label='Download', color='blue')
        axes[2, 1].plot(sl_data.index, sl_data['starlink_upload'], linewidth=0.5, alpha=0.7, label='Upload', color='green')
        axes[2, 1].set_title('Starlink Throughput Over Time')
        axes[2, 1].set_ylabel('Speed (Mbps)')
        axes[2, 1].set_xlabel('Sample Index')
        axes[2, 1].legend()
        axes[2, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        # 저장
        output_file = Path(self.data_path).parent / output_path
        plt.savefig(str(output_file), dpi=150, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved time series comparison: {output_file}")

    def create_quality_distribution_charts(self, output_path: str = "quality_distribution.png"):
        """품질 분포 차트"""
        print(f"\n📊 Creating Quality Distribution Charts...")

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))

        lte_data = self.df[self.df['lte_available'] == True]
        sl_data = self.df[self.df['starlink_available'] == True]

        # LTE 분포들
        # 1. RSSI 히스토그램
        axes[0, 0].hist(lte_data['lte_rssi'], bins=30, alpha=0.7, color='steelblue', edgecolor='black')
        axes[0, 0].axvline(x=lte_data['lte_rssi'].mean(), color='red', linestyle='--', linewidth=2, label='Mean')
        axes[0, 0].set_title('RSSI Distribution')
        axes[0, 0].set_xlabel('RSSI (dBm)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # 2. RSRP 히스토그램
        lte_rsrp_valid = lte_data['lte_rsrp'].dropna()
        axes[0, 1].hist(lte_rsrp_valid, bins=30, alpha=0.7, color='green', edgecolor='black')
        axes[0, 1].axvline(x=lte_rsrp_valid.mean(), color='red', linestyle='--', linewidth=2, label='Mean')
        axes[0, 1].set_title('RSRP Distribution')
        axes[0, 1].set_xlabel('RSRP (dBm)')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # 3. SINR 히스토그램
        lte_sinr_valid = lte_data['lte_sinr'].dropna()
        axes[0, 2].hist(lte_sinr_valid, bins=30, alpha=0.7, color='orange', edgecolor='black')
        axes[0, 2].axvline(x=lte_sinr_valid.mean(), color='red', linestyle='--', linewidth=2, label='Mean')
        axes[0, 2].set_title('SINR Distribution')
        axes[0, 2].set_xlabel('SINR (dB)')
        axes[0, 2].set_ylabel('Frequency')
        axes[0, 2].legend()
        axes[0, 2].grid(True, alpha=0.3)

        # Starlink 분포들
        # 4. Latency 히스토그램
        axes[1, 0].hist(sl_data['starlink_latency'], bins=30, alpha=0.7, color='purple', edgecolor='black')
        axes[1, 0].axvline(x=sl_data['starlink_latency'].mean(), color='red', linestyle='--', linewidth=2, label='Mean')
        axes[1, 0].set_title('Starlink Latency Distribution')
        axes[1, 0].set_xlabel('Latency (ms)')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # 5. Download 박스플롯
        axes[1, 1].boxplot([sl_data['starlink_download']], tick_labels=['Download'])
        axes[1, 1].set_title('Starlink Download Speed Distribution')
        axes[1, 1].set_ylabel('Speed (Mbps)')
        axes[1, 1].grid(True, alpha=0.3)

        # 6. Upload 박스플롯
        axes[1, 2].boxplot([sl_data['starlink_upload']], tick_labels=['Upload'])
        axes[1, 2].set_title('Starlink Upload Speed Distribution')
        axes[1, 2].set_ylabel('Speed (Mbps)')
        axes[1, 2].grid(True, alpha=0.3)

        plt.tight_layout()

        # 저장
        output_file = Path(self.data_path).parent / output_path
        plt.savefig(str(output_file), dpi=150, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved quality distribution charts: {output_file}")

    def generate_all(self):
        """모든 고급 시각화 생성"""
        print("="*80)
        print("🎨 GENERATING ADVANCED VISUALIZATIONS")
        print("="*80)

        # 데이터 로드
        self.load_data()

        # 모든 시각화 생성
        self.create_multi_metric_heatmap()
        self.create_correlation_heatmap()
        self.create_time_series_comparison()
        self.create_quality_distribution_charts()

        print("\n" + "="*80)
        print("✅ All Advanced Visualizations Complete!")
        print("="*80)


def main():
    """메인 실행"""
    print("="*80)
    print("🔬 ADVANCED VISUALIZATION GENERATOR")
    print("="*80)

    # 경로 설정
    base_dir = Path(__file__).parent
    merged_data = base_dir / "merged_flight_data.csv"

    # 시각화 생성기
    generator = AdvancedVisualizations(str(merged_data))

    # 모든 시각화 생성
    generator.generate_all()

    print("\n📁 Generated files:")
    print("  - multi_metric_heatmap.html")
    print("  - correlation_heatmap.png")
    print("  - time_series_comparison.png")
    print("  - quality_distribution.png")


if __name__ == "__main__":
    main()
