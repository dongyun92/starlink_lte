#!/usr/bin/env python3
"""
통신 품질 자동 보고서 생성기
- PDF 형식의 전문적인 품질 보고서 생성
- 통계 차트 및 분석 결과 포함
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 없이 실행
import seaborn as sns
from datetime import datetime
from pathlib import Path
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec


class QualityReportGenerator:
    """통신 품질 보고서 생성기"""

    def __init__(self, merged_data_path: str):
        self.data_path = Path(merged_data_path)
        self.df = None
        self.report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 스타일 설정
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (11, 8.5)  # Letter size
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.titlesize'] = 12
        plt.rcParams['axes.labelsize'] = 10

    def load_data(self):
        """데이터 로드"""
        print(f"📁 Loading merged data: {self.data_path.name}")
        self.df = pd.read_csv(self.data_path)
        print(f"✓ Loaded {len(self.df)} data points")

    def generate_report(self, output_path: str = "communication_quality_report.pdf"):
        """전체 보고서 생성"""
        print(f"\n📄 Generating quality report...")

        output_file = Path(self.data_path).parent / output_path

        with PdfPages(str(output_file)) as pdf:
            # 페이지 1: 표지 및 요약
            self._create_cover_page(pdf)

            # 페이지 2: LTE 품질 분석
            self._create_lte_analysis_page(pdf)

            # 페이지 3: Starlink 품질 분석
            self._create_starlink_analysis_page(pdf)

            # 페이지 4: 비교 분석
            self._create_comparison_page(pdf)

            # 메타데이터 추가
            d = pdf.infodict()
            d['Title'] = 'Communication Quality Analysis Report'
            d['Author'] = 'Flight Data Analyzer'
            d['Subject'] = 'LTE & Starlink Quality Analysis'
            d['Keywords'] = 'LTE, Starlink, Communication Quality'
            d['CreationDate'] = datetime.now()

        print(f"✓ Saved report: {output_file}")

    def _create_cover_page(self, pdf):
        """표지 페이지"""
        fig = plt.figure(figsize=(11, 8.5))
        fig.patch.set_facecolor('white')

        # 제목
        plt.text(0.5, 0.7, 'Communication Quality\nAnalysis Report',
                horizontalalignment='center', verticalalignment='center',
                fontsize=32, fontweight='bold')

        # 부제목
        plt.text(0.5, 0.55, 'LTE & Starlink Network Performance',
                horizontalalignment='center', verticalalignment='center',
                fontsize=18, color='gray')

        # 날짜
        plt.text(0.5, 0.45, f'Report Generated: {self.report_date}',
                horizontalalignment='center', verticalalignment='center',
                fontsize=12, color='gray')

        # 요약 통계
        lte_data = self.df[self.df['lte_available'] == True]
        sl_data = self.df[self.df['starlink_available'] == True]

        summary_text = f"""
        Flight Summary
        {'='*50}
        Total Data Points: {len(self.df):,}
        Flight Duration: {(self.df['timestamp'].max() - self.df['timestamp'].min()):.0f} seconds

        LTE Coverage: {len(lte_data)/len(self.df)*100:.1f}%
        Starlink Coverage: {len(sl_data)/len(self.df)*100:.1f}%
        """

        plt.text(0.5, 0.25, summary_text,
                horizontalalignment='center', verticalalignment='top',
                fontsize=12, family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        plt.axis('off')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _create_lte_analysis_page(self, pdf):
        """LTE 품질 분석 페이지"""
        lte_data = self.df[self.df['lte_available'] == True]

        if len(lte_data) == 0:
            print("⚠️  No LTE data for report")
            return

        fig = plt.figure(figsize=(11, 8.5))
        gs = GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

        # 제목
        fig.suptitle('LTE Communication Quality Analysis', fontsize=16, fontweight='bold')

        # 1. RSSI 시계열
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(range(len(lte_data)), lte_data['lte_rssi'], linewidth=0.5, alpha=0.7)
        ax1.axhline(y=-70, color='green', linestyle='--', label='Excellent (-70 dBm)')
        ax1.axhline(y=-85, color='orange', linestyle='--', label='Good (-85 dBm)')
        ax1.axhline(y=-100, color='red', linestyle='--', label='Fair (-100 dBm)')
        ax1.set_title('RSSI (Signal Strength) Over Time')
        ax1.set_xlabel('Sample Index')
        ax1.set_ylabel('RSSI (dBm)')
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True, alpha=0.3)

        # 2. RSSI 히스토그램
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.hist(lte_data['lte_rssi'], bins=30, alpha=0.7, color='steelblue', edgecolor='black')
        ax2.axvline(x=lte_data['lte_rssi'].mean(), color='red', linestyle='--', linewidth=2, label='Mean')
        ax2.set_title('RSSI Distribution')
        ax2.set_xlabel('RSSI (dBm)')
        ax2.set_ylabel('Frequency')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 3. RSRP 분포
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.hist(lte_data['lte_rsrp'], bins=30, alpha=0.7, color='coral', edgecolor='black')
        ax3.axvline(x=lte_data['lte_rsrp'].mean(), color='red', linestyle='--', linewidth=2, label='Mean')
        ax3.set_title('RSRP Distribution')
        ax3.set_xlabel('RSRP (dBm)')
        ax3.set_ylabel('Frequency')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 4. SINR 시계열
        ax4 = fig.add_subplot(gs[2, 0])
        ax4.plot(range(len(lte_data)), lte_data['lte_sinr'], linewidth=0.5, alpha=0.7, color='green')
        ax4.axhline(y=20, color='green', linestyle='--', label='Excellent (>20 dB)')
        ax4.axhline(y=13, color='orange', linestyle='--', label='Good (>13 dB)')
        ax4.axhline(y=0, color='red', linestyle='--', label='Poor (<0 dB)')
        ax4.set_title('SINR (Signal Quality) Over Time')
        ax4.set_xlabel('Sample Index')
        ax4.set_ylabel('SINR (dB)')
        ax4.legend(loc='upper right', fontsize=8)
        ax4.grid(True, alpha=0.3)

        # 5. 통계 테이블
        ax5 = fig.add_subplot(gs[2, 1])
        ax5.axis('off')

        stats_data = [
            ['Metric', 'Mean', 'Min', 'Max', 'Std'],
            ['RSSI (dBm)', f"{lte_data['lte_rssi'].mean():.1f}",
             f"{lte_data['lte_rssi'].min():.0f}",
             f"{lte_data['lte_rssi'].max():.0f}",
             f"{lte_data['lte_rssi'].std():.1f}"],
            ['RSRP (dBm)', f"{lte_data['lte_rsrp'].mean():.1f}",
             f"{lte_data['lte_rsrp'].min():.0f}",
             f"{lte_data['lte_rsrp'].max():.0f}",
             f"{lte_data['lte_rsrp'].std():.1f}"],
            ['SINR (dB)', f"{lte_data['lte_sinr'].mean():.1f}",
             f"{lte_data['lte_sinr'].min():.0f}",
             f"{lte_data['lte_sinr'].max():.0f}",
             f"{lte_data['lte_sinr'].std():.1f}"],
        ]

        table = ax5.table(cellText=stats_data, cellLoc='center',
                         loc='center', bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)

        # 헤더 스타일
        for i in range(5):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')

        ax5.set_title('LTE Quality Statistics', fontweight='bold', pad=20)

        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _create_starlink_analysis_page(self, pdf):
        """Starlink 품질 분석 페이지"""
        sl_data = self.df[self.df['starlink_available'] == True]

        if len(sl_data) == 0:
            print("⚠️  No Starlink data for report")
            return

        fig = plt.figure(figsize=(11, 8.5))
        gs = GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

        fig.suptitle('Starlink Communication Quality Analysis', fontsize=16, fontweight='bold')

        # 1. Latency 시계열
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(range(len(sl_data)), sl_data['starlink_latency'], linewidth=0.5, alpha=0.7, color='blue')
        ax1.axhline(y=40, color='green', linestyle='--', label='Excellent (<40 ms)')
        ax1.axhline(y=100, color='orange', linestyle='--', label='Good (<100 ms)')
        ax1.set_title('Latency Over Time')
        ax1.set_xlabel('Sample Index')
        ax1.set_ylabel('Latency (ms)')
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True, alpha=0.3)

        # 2. Latency 히스토그램
        ax2 = fig.add_subplot(gs[1, 0])
        valid_latency = sl_data[sl_data['starlink_latency'] >= 0]['starlink_latency']
        ax2.hist(valid_latency, bins=30, alpha=0.7, color='steelblue', edgecolor='black')
        ax2.axvline(x=valid_latency.mean(), color='red', linestyle='--', linewidth=2, label='Mean')
        ax2.set_title('Latency Distribution')
        ax2.set_xlabel('Latency (ms)')
        ax2.set_ylabel('Frequency')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 3. Download/Upload 속도
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.plot(range(len(sl_data)), sl_data['starlink_download'], linewidth=0.5, alpha=0.7, label='Download', color='green')
        ax3.plot(range(len(sl_data)), sl_data['starlink_upload'], linewidth=0.5, alpha=0.7, label='Upload', color='orange')
        ax3.set_title('Throughput Over Time')
        ax3.set_xlabel('Sample Index')
        ax3.set_ylabel('Speed (Mbps)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 4. Throughput 분포
        ax4 = fig.add_subplot(gs[2, 0])
        ax4.boxplot([sl_data['starlink_download'], sl_data['starlink_upload']],
                   labels=['Download', 'Upload'])
        ax4.set_title('Throughput Distribution')
        ax4.set_ylabel('Speed (Mbps)')
        ax4.grid(True, alpha=0.3)

        # 5. 통계 테이블
        ax5 = fig.add_subplot(gs[2, 1])
        ax5.axis('off')

        stats_data = [
            ['Metric', 'Mean', 'Min', 'Max', 'Std'],
            ['Latency (ms)', f"{valid_latency.mean():.1f}",
             f"{valid_latency.min():.1f}",
             f"{valid_latency.max():.1f}",
             f"{valid_latency.std():.1f}"],
            ['Download (Mbps)', f"{sl_data['starlink_download'].mean():.1f}",
             f"{sl_data['starlink_download'].min():.1f}",
             f"{sl_data['starlink_download'].max():.1f}",
             f"{sl_data['starlink_download'].std():.1f}"],
            ['Upload (Mbps)', f"{sl_data['starlink_upload'].mean():.1f}",
             f"{sl_data['starlink_upload'].min():.1f}",
             f"{sl_data['starlink_upload'].max():.1f}",
             f"{sl_data['starlink_upload'].std():.1f}"],
        ]

        table = ax5.table(cellText=stats_data, cellLoc='center',
                         loc='center', bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)

        for i in range(5):
            table[(0, i)].set_facecolor('#2196F3')
            table[(0, i)].set_text_props(weight='bold', color='white')

        ax5.set_title('Starlink Quality Statistics', fontweight='bold', pad=20)

        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _create_comparison_page(self, pdf):
        """LTE vs Starlink 비교 페이지"""
        lte_data = self.df[self.df['lte_available'] == True]
        sl_data = self.df[self.df['starlink_available'] == True]

        fig = plt.figure(figsize=(11, 8.5))
        gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

        fig.suptitle('LTE vs Starlink Comparison', fontsize=16, fontweight='bold')

        # 1. Coverage 비교
        ax1 = fig.add_subplot(gs[0, 0])
        coverage_data = [len(lte_data)/len(self.df)*100, len(sl_data)/len(self.df)*100]
        colors = ['#4CAF50', '#2196F3']
        bars = ax1.bar(['LTE', 'Starlink'], coverage_data, color=colors, alpha=0.7)
        ax1.set_title('Network Coverage')
        ax1.set_ylabel('Coverage (%)')
        ax1.set_ylim([0, 105])
        for bar, value in zip(bars, coverage_data):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')

        # 2. 품질 등급 분포
        ax2 = fig.add_subplot(gs[0, 1])

        # LTE 품질 등급 (RSSI 기준)
        lte_excellent = len(lte_data[lte_data['lte_rssi'] > -70])
        lte_good = len(lte_data[(lte_data['lte_rssi'] <= -70) & (lte_data['lte_rssi'] > -85)])
        lte_fair = len(lte_data[lte_data['lte_rssi'] <= -85])

        # Starlink 품질 등급 (Latency 기준)
        sl_excellent = len(sl_data[sl_data['starlink_latency'] < 40])
        sl_good = len(sl_data[(sl_data['starlink_latency'] >= 40) & (sl_data['starlink_latency'] < 100)])
        sl_fair = len(sl_data[sl_data['starlink_latency'] >= 100])

        x = np.arange(3)
        width = 0.35

        ax2.bar(x - width/2, [lte_excellent, lte_good, lte_fair], width, label='LTE', color='#4CAF50', alpha=0.7)
        ax2.bar(x + width/2, [sl_excellent, sl_good, sl_fair], width, label='Starlink', color='#2196F3', alpha=0.7)
        ax2.set_xticks(x)
        ax2.set_xticklabels(['Excellent', 'Good', 'Fair'])
        ax2.set_title('Quality Grade Distribution')
        ax2.set_ylabel('Number of Samples')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')

        # 3. 종합 권장사항
        ax3 = fig.add_subplot(gs[1, :])
        ax3.axis('off')

        # 통계 기반 권장사항 생성
        lte_quality = "Excellent" if lte_data['lte_rssi'].mean() > -70 else "Good" if lte_data['lte_rssi'].mean() > -85 else "Fair"
        sl_quality = "Excellent" if sl_data['starlink_latency'].mean() < 40 else "Good" if sl_data['starlink_latency'].mean() < 100 else "Fair"

        recommendations = f"""
        ANALYSIS SUMMARY & RECOMMENDATIONS
        {'='*80}

        Network Performance:
        • LTE Coverage: {len(lte_data)/len(self.df)*100:.1f}% | Overall Quality: {lte_quality}
        • Starlink Coverage: {len(sl_data)/len(self.df)*100:.1f}% | Overall Quality: {sl_quality}

        Key Findings:
        • LTE Average RSSI: {lte_data['lte_rssi'].mean():.1f} dBm
        • LTE Average SINR: {lte_data['lte_sinr'].mean():.1f} dB
        • Starlink Average Latency: {sl_data['starlink_latency'].mean():.1f} ms
        • Starlink Average Download: {sl_data['starlink_download'].mean():.1f} Mbps

        Recommendations:
        1. LTE provides {'excellent' if len(lte_data)/len(self.df) > 0.95 else 'good'} coverage throughout the flight
        2. Starlink {'shows reliable performance' if len(sl_data)/len(self.df) > 0.5 else 'has limited coverage'}
           in this flight area
        3. For mission-critical applications, {'dual network redundancy is available' if len(lte_data)/len(self.df) > 0.8 and len(sl_data)/len(self.df) > 0.5 else 'consider LTE as primary network'}

        Report Generated: {self.report_date}
        """

        ax3.text(0.05, 0.95, recommendations, transform=ax3.transAxes,
                fontsize=10, verticalalignment='top', family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        pdf.savefig(fig, bbox_inches='tight')
        plt.close()


def main():
    """테스트 실행"""
    print("=" * 60)
    print("QUALITY REPORT GENERATOR - TEST")
    print("=" * 60)

    # 경로 설정
    base_dir = Path(__file__).parent
    merged_data = base_dir / "merged_flight_data.csv"

    # 보고서 생성기
    generator = QualityReportGenerator(str(merged_data))

    # 데이터 로드
    generator.load_data()

    # 보고서 생성
    generator.generate_report()

    print("\n" + "=" * 60)
    print("✅ Quality report generated successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
