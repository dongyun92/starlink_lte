#!/usr/bin/env python3
"""
비행 고도와 통신 품질 상관관계 분석
Flight Altitude vs Communication Quality Analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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


class FlightQualityAnalyzer:
    """비행 고도와 통신 품질 분석기"""

    def __init__(self, merged_data_path: str):
        self.data_path = Path(merged_data_path)
        self.df = None

    def load_data(self):
        """데이터 로드"""
        print(f"📁 Loading data: {self.data_path.name}")
        self.df = pd.read_csv(self.data_path)

        # 비행 단계 분류
        self.df['flight_phase'] = self.classify_flight_phase(self.df['altitude'])

        print(f"✓ Total samples: {len(self.df)}")
        print(f"✓ Altitude range: {self.df['altitude'].min():.1f}m ~ {self.df['altitude'].max():.1f}m")

    def classify_flight_phase(self, altitude):
        """고도 기반 비행 단계 분류"""
        phases = []
        for alt in altitude:
            if alt < 30:
                phases.append('Ground/Takeoff')  # 지상/이륙
            elif alt < 60:
                phases.append('Climb')  # 상승
            elif alt < 90:
                phases.append('Cruise (Low)')  # 순항 (저고도)
            elif alt < 110:
                phases.append('Cruise (High)')  # 순항 (고고도)
            else:
                phases.append('Descent/Landing')  # 하강/착륙 준비
        return phases

    def create_altitude_quality_analysis(self, output_path: str = "altitude_quality_analysis.png"):
        """고도-품질 종합 분석 차트"""
        print(f"\n🛫 Creating Altitude vs Quality Analysis...")

        fig = plt.figure(figsize=(18, 12))

        # 1. 고도 시계열
        ax1 = plt.subplot(3, 3, 1)
        ax1.plot(self.df.index, self.df['altitude'], color='steelblue', linewidth=1.5, label='Altitude')
        ax1.fill_between(self.df.index, self.df['altitude'], alpha=0.3, color='steelblue')
        ax1.set_xlabel('Sample Index', fontsize=10)
        ax1.set_ylabel('Altitude (m)', fontsize=10)
        ax1.set_title('Flight Altitude Profile', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # 비행 단계 구간 표시
        phase_colors = {
            'Ground/Takeoff': '#FF6B6B',
            'Climb': '#4ECDC4',
            'Cruise (Low)': '#45B7D1',
            'Cruise (High)': '#96CEB4',
            'Descent/Landing': '#FFEAA7'
        }

        # 2. 고도 vs LTE RSSI
        ax2 = plt.subplot(3, 3, 2)
        valid_lte = self.df[self.df['lte_available'] == True]
        scatter = ax2.scatter(valid_lte['altitude'], valid_lte['lte_rssi'],
                             c=valid_lte.index, cmap='viridis', s=20, alpha=0.6)
        ax2.set_xlabel('Altitude (m)', fontsize=10)
        ax2.set_ylabel('LTE RSSI (dBm)', fontsize=10)
        ax2.set_title('Altitude vs LTE Signal Strength', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # 상관계수
        corr = valid_lte['altitude'].corr(valid_lte['lte_rssi'])
        ax2.text(0.05, 0.95, f'Correlation: {corr:.3f}',
                transform=ax2.transAxes, fontsize=9,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # 3. 고도 vs Starlink Latency
        ax3 = plt.subplot(3, 3, 3)
        valid_sl = self.df[self.df['starlink_available'] == True]
        scatter = ax3.scatter(valid_sl['altitude'], valid_sl['starlink_latency'],
                             c=valid_sl.index, cmap='plasma', s=20, alpha=0.6)
        ax3.set_xlabel('Altitude (m)', fontsize=10)
        ax3.set_ylabel('Starlink Latency (ms)', fontsize=10)
        ax3.set_title('Altitude vs Starlink Latency', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)

        corr = valid_sl['altitude'].corr(valid_sl['starlink_latency'])
        ax3.text(0.05, 0.95, f'Correlation: {corr:.3f}',
                transform=ax3.transAxes, fontsize=9,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # 4. 고도 + LTE RSSI 시계열 (2축)
        ax4 = plt.subplot(3, 3, 4)
        ax4_twin = ax4.twinx()

        ax4.plot(self.df.index, self.df['altitude'], color='steelblue', linewidth=1.5, label='Altitude', alpha=0.7)
        ax4_twin.plot(valid_lte.index, valid_lte['lte_rssi'], color='coral', linewidth=1.5, label='LTE RSSI', alpha=0.7)

        ax4.set_xlabel('Sample Index', fontsize=10)
        ax4.set_ylabel('Altitude (m)', fontsize=10, color='steelblue')
        ax4_twin.set_ylabel('LTE RSSI (dBm)', fontsize=10, color='coral')
        ax4.set_title('Altitude & LTE RSSI Time Series', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.tick_params(axis='y', labelcolor='steelblue')
        ax4_twin.tick_params(axis='y', labelcolor='coral')

        # 5. 고도 + Starlink Latency 시계열 (2축)
        ax5 = plt.subplot(3, 3, 5)
        ax5_twin = ax5.twinx()

        ax5.plot(self.df.index, self.df['altitude'], color='steelblue', linewidth=1.5, label='Altitude', alpha=0.7)
        ax5_twin.plot(valid_sl.index, valid_sl['starlink_latency'], color='purple', linewidth=1.5, label='Starlink Latency', alpha=0.7)

        ax5.set_xlabel('Sample Index', fontsize=10)
        ax5.set_ylabel('Altitude (m)', fontsize=10, color='steelblue')
        ax5_twin.set_ylabel('Latency (ms)', fontsize=10, color='purple')
        ax5.set_title('Altitude & Starlink Latency Time Series', fontsize=12, fontweight='bold')
        ax5.grid(True, alpha=0.3)
        ax5.tick_params(axis='y', labelcolor='steelblue')
        ax5_twin.tick_params(axis='y', labelcolor='purple')

        # 6. 비행 단계별 LTE 품질 박스플롯
        ax6 = plt.subplot(3, 3, 6)
        phase_order = ['Ground/Takeoff', 'Climb', 'Cruise (Low)', 'Cruise (High)', 'Descent/Landing']
        valid_phases = valid_lte[valid_lte['flight_phase'].isin(phase_order)]

        sns.boxplot(data=valid_phases, x='flight_phase', y='lte_rssi',
                   order=phase_order, palette='Set2', ax=ax6)
        ax6.set_xlabel('Flight Phase', fontsize=10)
        ax6.set_ylabel('LTE RSSI (dBm)', fontsize=10)
        ax6.set_title('LTE Quality by Flight Phase', fontsize=12, fontweight='bold')
        ax6.tick_params(axis='x', rotation=45)
        ax6.grid(True, alpha=0.3, axis='y')

        # 7. 비행 단계별 Starlink 품질 박스플롯
        ax7 = plt.subplot(3, 3, 7)
        valid_sl_phases = valid_sl[valid_sl['flight_phase'].isin(phase_order)]

        sns.boxplot(data=valid_sl_phases, x='flight_phase', y='starlink_latency',
                   order=phase_order, palette='Set3', ax=ax7)
        ax7.set_xlabel('Flight Phase', fontsize=10)
        ax7.set_ylabel('Starlink Latency (ms)', fontsize=10)
        ax7.set_title('Starlink Quality by Flight Phase', fontsize=12, fontweight='bold')
        ax7.tick_params(axis='x', rotation=45)
        ax7.grid(True, alpha=0.3, axis='y')

        # 8. 고도 vs Download Speed
        ax8 = plt.subplot(3, 3, 8)
        scatter = ax8.scatter(valid_sl['altitude'], valid_sl['starlink_download'],
                             c=valid_sl['starlink_latency'], cmap='RdYlGn_r', s=20, alpha=0.6)
        ax8.set_xlabel('Altitude (m)', fontsize=10)
        ax8.set_ylabel('Download Speed (Mbps)', fontsize=10)
        ax8.set_title('Altitude vs Download Speed', fontsize=12, fontweight='bold')
        ax8.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax8, label='Latency (ms)')

        corr = valid_sl['altitude'].corr(valid_sl['starlink_download'])
        ax8.text(0.05, 0.95, f'Correlation: {corr:.3f}',
                transform=ax8.transAxes, fontsize=9,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # 9. 비행 단계별 통계 요약
        ax9 = plt.subplot(3, 3, 9)
        ax9.axis('off')

        summary_text = "비행 단계별 통신 품질 요약\n" + "="*40 + "\n\n"

        for phase in phase_order:
            phase_data = self.df[self.df['flight_phase'] == phase]
            lte_data = phase_data[phase_data['lte_available'] == True]
            sl_data = phase_data[phase_data['starlink_available'] == True]

            if len(lte_data) > 0 or len(sl_data) > 0:
                summary_text += f"{phase}:\n"
                summary_text += f"  Samples: {len(phase_data)}\n"
                summary_text += f"  Altitude: {phase_data['altitude'].mean():.1f}m\n"

                if len(lte_data) > 0:
                    summary_text += f"  LTE RSSI: {lte_data['lte_rssi'].mean():.1f} dBm\n"

                if len(sl_data) > 0:
                    summary_text += f"  Starlink Latency: {sl_data['starlink_latency'].mean():.1f} ms\n"

                summary_text += "\n"

        ax9.text(0.05, 0.95, summary_text, ha='left', va='top',
                fontsize=8, family='monospace',
                bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.8))

        plt.suptitle('🛫 Flight Altitude vs Communication Quality Analysis',
                    fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        output_file = Path(self.data_path).parent / output_path
        plt.savefig(str(output_file), dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Saved: {output_file}")

    def print_statistics(self):
        """통계 출력"""
        print("\n" + "="*80)
        print("📊 FLIGHT-QUALITY CORRELATION STATISTICS")
        print("="*80)

        # 전체 상관관계
        print("\n🔗 Altitude Correlations:")
        print(f"  Altitude ↔ LTE RSSI: {self.df['altitude'].corr(self.df['lte_rssi']):.3f}")
        print(f"  Altitude ↔ Starlink Latency: {self.df['altitude'].corr(self.df['starlink_latency']):.3f}")
        print(f"  Altitude ↔ Download Speed: {self.df['altitude'].corr(self.df['starlink_download']):.3f}")

        # 비행 단계별 통계
        print("\n📈 Statistics by Flight Phase:")
        phase_stats = self.df.groupby('flight_phase').agg({
            'altitude': ['count', 'mean', 'min', 'max'],
            'lte_rssi': 'mean',
            'starlink_latency': 'mean'
        }).round(2)
        print(phase_stats)


def main():
    """메인 실행"""
    print("="*80)
    print("🛫 FLIGHT ALTITUDE vs COMMUNICATION QUALITY ANALYZER")
    print("="*80)

    base_dir = Path(__file__).parent
    merged_data = base_dir / "merged_flight_data.csv"

    analyzer = FlightQualityAnalyzer(str(merged_data))
    analyzer.load_data()
    analyzer.create_altitude_quality_analysis()
    analyzer.print_statistics()

    print("\n✅ Analysis Complete!")


if __name__ == "__main__":
    main()
