#!/usr/bin/env python3
"""
종합 파라미터 상관관계 분석
Comprehensive Parameter Correlation Analysis
- 모든 원본 변수 + 파생 변수 간 상관관계 분석
- 통신 품질에 영향을 미치는 모든 요인 식별
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


class ComprehensiveCorrelationAnalyzer:
    """종합 상관관계 분석기"""

    def __init__(self, merged_data_path: str):
        self.data_path = Path(merged_data_path)
        self.df = None
        self.correlation_results = {}

    def load_and_prepare_data(self):
        """데이터 로드 및 파생 변수 생성"""
        print("="*80)
        print("📊 COMPREHENSIVE CORRELATION ANALYSIS")
        print("="*80)

        print(f"\n📁 Loading: {self.data_path.name}")
        self.df = pd.read_csv(self.data_path)

        print(f"✓ Loaded {len(self.df)} samples")
        print(f"✓ Original columns: {len(self.df.columns)}")

        # 파생 변수 생성
        print("\n🔧 Creating derived variables...")
        self._create_derived_variables()

        print(f"✓ Total columns after derivation: {len(self.df.columns)}")

    def _create_derived_variables(self):
        """모든 파생 변수 생성"""

        # 1. 위치 이동 관련 변수
        print("  - Position movement variables...")
        self.df['lat_change'] = self.df['latitude'].diff()
        self.df['lon_change'] = self.df['longitude'].diff()

        # Haversine distance (미터)
        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371000  # Earth radius in meters
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

        # 이동 속도 (m/s) - 샘플링 간격 0.5초 가정
        self.df['speed_mps'] = self.df['distance_moved'] / 0.5

        # 이동 방향 (bearing, degrees)
        def calculate_bearing(lat1, lon1, lat2, lon2):
            lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
            dlon = lon2 - lon1
            x = np.sin(dlon) * np.cos(lat2)
            y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
            bearing = np.arctan2(x, y)
            return (np.degrees(bearing) + 360) % 360

        self.df['bearing'] = calculate_bearing(
            self.df['latitude'].shift(1), self.df['longitude'].shift(1),
            self.df['latitude'], self.df['longitude']
        )

        # 2. 고도 변화 관련 변수
        print("  - Altitude change variables...")
        self.df['altitude_change'] = self.df['altitude'].diff()
        self.df['altitude_rate'] = self.df['altitude_change'] / 0.5  # m/s

        # 상승/하강/정지 상태
        def classify_vertical_movement(rate):
            if pd.isna(rate):
                return 'unknown'
            elif rate > 1.0:
                return 'climbing'
            elif rate < -1.0:
                return 'descending'
            else:
                return 'stable'

        self.df['vertical_status'] = self.df['altitude_rate'].apply(classify_vertical_movement)

        # 3. 통신 품질 등급
        print("  - Communication quality grades...")

        # LTE 품질 등급
        def lte_quality_grade(rssi):
            if pd.isna(rssi):
                return np.nan
            elif rssi >= -70:
                return 'Excellent'
            elif rssi >= -80:
                return 'Good'
            elif rssi >= -90:
                return 'Fair'
            else:
                return 'Poor'

        self.df['lte_quality_grade'] = self.df['lte_rssi'].apply(lte_quality_grade)

        # Starlink 품질 등급
        def starlink_quality_grade(latency):
            if pd.isna(latency):
                return np.nan
            elif latency < 50:
                return 'Excellent'
            elif latency < 80:
                return 'Good'
            elif latency < 120:
                return 'Fair'
            else:
                return 'Poor'

        self.df['starlink_quality_grade'] = self.df['starlink_latency'].apply(starlink_quality_grade)

        # 4. LTE 신호 품질 변화
        print("  - Signal quality changes...")
        self.df['lte_rssi_change'] = self.df['lte_rssi'].diff()
        self.df['lte_rsrp_change'] = self.df['lte_rsrp'].diff()
        self.df['starlink_latency_change'] = self.df['starlink_latency'].diff()

        # 급격한 RSSI 변화 (기지국 전환 가능성)
        self.df['rssi_spike'] = (self.df['lte_rssi_change'].abs() > 5).astype(int)

        # 5. 비행 단계
        print("  - Flight phases...")
        def classify_flight_phase(altitude):
            if altitude < 30:
                return 'Ground/Takeoff'
            elif altitude < 60:
                return 'Climb'
            elif altitude < 90:
                return 'Cruise_Low'
            elif altitude < 110:
                return 'Cruise_High'
            else:
                return 'Descent/Landing'

        self.df['flight_phase'] = self.df['altitude'].apply(classify_flight_phase)

        # 6. 네트워크 가용성 조합
        print("  - Network availability combinations...")
        self.df['network_status'] = 'None'
        self.df.loc[self.df['lte_available'] & self.df['starlink_available'], 'network_status'] = 'Both'
        self.df.loc[self.df['lte_available'] & ~self.df['starlink_available'], 'network_status'] = 'LTE_Only'
        self.df.loc[~self.df['lte_available'] & self.df['starlink_available'], 'network_status'] = 'Starlink_Only'

        # 7. 누적 비행 시간 (초)
        self.df['flight_time_elapsed'] = self.df.index * 0.5

        # 8. 원점으로부터의 거리
        print("  - Distance from origin...")
        origin_lat = self.df['latitude'].iloc[0]
        origin_lon = self.df['longitude'].iloc[0]

        self.df['distance_from_origin'] = haversine_distance(
            origin_lat, origin_lon,
            self.df['latitude'], self.df['longitude']
        )

        print(f"✓ Created {len(self.df.columns) - 17} derived variables")

    def compute_correlations(self):
        """모든 수치형 변수 간 상관관계 계산"""
        print("\n🔗 Computing comprehensive correlations...")

        # 수치형 변수만 선택
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()

        # Boolean 변수는 0/1로 변환
        for col in numeric_cols:
            if self.df[col].dtype == bool:
                self.df[col] = self.df[col].astype(int)

        # 상관관계 매트릭스 계산
        self.correlation_matrix = self.df[numeric_cols].corr()

        print(f"✓ Computed {len(numeric_cols)} × {len(numeric_cols)} correlation matrix")

        # 통신 품질 관련 변수 식별
        quality_vars = [
            'lte_rssi', 'lte_rsrp', 'lte_rsrq', 'lte_sinr',
            'starlink_latency', 'starlink_download', 'starlink_upload'
        ]

        # 각 품질 변수에 대한 상관관계 추출
        for quality_var in quality_vars:
            if quality_var in self.correlation_matrix.columns:
                corr_series = self.correlation_matrix[quality_var].sort_values(ascending=False)
                # 자기 자신 제외
                corr_series = corr_series[corr_series.index != quality_var]
                self.correlation_results[quality_var] = corr_series

        return self.correlation_matrix

    def find_significant_correlations(self, threshold=0.3):
        """유의미한 상관관계 식별"""
        print(f"\n📈 Identifying significant correlations (|r| > {threshold})...")

        significant = {}

        for quality_var, corr_series in self.correlation_results.items():
            sig_corr = corr_series[corr_series.abs() > threshold]
            if len(sig_corr) > 0:
                significant[quality_var] = sig_corr

                print(f"\n🎯 {quality_var}:")
                for var, corr_value in sig_corr.head(10).items():
                    print(f"   {var:30s}: {corr_value:+.3f}")

        return significant

    def visualize_correlations(self, output_path="comprehensive_correlations.png"):
        """상관관계 시각화"""
        print(f"\n📊 Creating comprehensive correlation visualizations...")

        fig = plt.figure(figsize=(24, 16))

        # 1. 전체 상관관계 히트맵 (주요 변수만)
        ax1 = plt.subplot(3, 3, 1)

        # 주요 변수 선택
        key_vars = [
            'altitude', 'latitude', 'longitude', 'distance_from_origin',
            'speed_mps', 'altitude_rate',
            'lte_rssi', 'lte_rsrp', 'lte_rsrq', 'lte_sinr',
            'starlink_latency', 'starlink_download', 'starlink_upload',
            'lte_rssi_change', 'starlink_latency_change', 'rssi_spike'
        ]

        available_key_vars = [v for v in key_vars if v in self.correlation_matrix.columns]
        key_corr_matrix = self.correlation_matrix.loc[available_key_vars, available_key_vars]

        sns.heatmap(key_corr_matrix, annot=False, cmap='RdBu_r', center=0,
                   vmin=-1, vmax=1, square=True, ax=ax1, cbar_kws={'label': 'Correlation'})
        ax1.set_title('Overall Correlation Heatmap (Key Variables)', fontsize=14, fontweight='bold')
        plt.setp(ax1.get_xticklabels(), rotation=45, ha='right', fontsize=8)
        plt.setp(ax1.get_yticklabels(), rotation=0, fontsize=8)

        # 2-4. LTE 품질 변수별 Top 상관관계
        lte_vars = ['lte_rssi', 'lte_rsrp', 'lte_sinr']

        for idx, lte_var in enumerate(lte_vars):
            ax = plt.subplot(3, 3, 2 + idx)

            if lte_var in self.correlation_results:
                top_corr = self.correlation_results[lte_var].head(15)

                colors = ['#2EBD85' if x > 0 else '#F6465D' for x in top_corr.values]
                bars = ax.barh(range(len(top_corr)), top_corr.values, color=colors, alpha=0.7)
                ax.set_yticks(range(len(top_corr)))
                ax.set_yticklabels(top_corr.index, fontsize=8)
                ax.set_xlabel('Correlation Coefficient', fontsize=10)
                ax.set_title(f'Top Correlations with {lte_var}', fontsize=12, fontweight='bold')
                ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
                ax.grid(True, alpha=0.3, axis='x')

                # 값 표시
                for i, (bar, val) in enumerate(zip(bars, top_corr.values)):
                    ax.text(val, i, f' {val:.3f}', va='center', fontsize=7)

        # 5-7. Starlink 품질 변수별 Top 상관관계
        sl_vars = ['starlink_latency', 'starlink_download', 'starlink_upload']

        for idx, sl_var in enumerate(sl_vars):
            ax = plt.subplot(3, 3, 5 + idx)

            if sl_var in self.correlation_results:
                top_corr = self.correlation_results[sl_var].head(15)

                colors = ['#2EBD85' if x > 0 else '#F6465D' for x in top_corr.values]
                bars = ax.barh(range(len(top_corr)), top_corr.values, color=colors, alpha=0.7)
                ax.set_yticks(range(len(top_corr)))
                ax.set_yticklabels(top_corr.index, fontsize=8)
                ax.set_xlabel('Correlation Coefficient', fontsize=10)
                ax.set_title(f'Top Correlations with {sl_var}', fontsize=12, fontweight='bold')
                ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
                ax.grid(True, alpha=0.3, axis='x')

                # 값 표시
                for i, (bar, val) in enumerate(zip(bars, top_corr.values)):
                    ax.text(val, i, f' {val:.3f}', va='center', fontsize=7)

        # 8. 고도 vs 위치 vs LTE RSSI (3D scatter)
        ax8 = plt.subplot(3, 3, 8)

        valid_data = self.df[self.df['lte_available']].copy()
        scatter = ax8.scatter(valid_data['distance_from_origin'],
                             valid_data['altitude'],
                             c=valid_data['lte_rssi'],
                             cmap='RdYlGn', s=10, alpha=0.6)
        ax8.set_xlabel('Distance from Origin (m)', fontsize=10)
        ax8.set_ylabel('Altitude (m)', fontsize=10)
        ax8.set_title('LTE RSSI by Position & Altitude', fontsize=12, fontweight='bold')
        plt.colorbar(scatter, ax=ax8, label='LTE RSSI (dBm)')
        ax8.grid(True, alpha=0.3)

        # 9. 이동 속도 vs 품질 변화
        ax9 = plt.subplot(3, 3, 9)

        valid_speed = self.df[(self.df['speed_mps'].notna()) & (self.df['lte_rssi_change'].notna())].copy()
        scatter = ax9.scatter(valid_speed['speed_mps'],
                             valid_speed['lte_rssi_change'].abs(),
                             c=valid_speed['altitude'],
                             cmap='viridis', s=10, alpha=0.6)
        ax9.set_xlabel('Movement Speed (m/s)', fontsize=10)
        ax9.set_ylabel('|LTE RSSI Change| (dBm)', fontsize=10)
        ax9.set_title('Signal Change vs Movement Speed', fontsize=12, fontweight='bold')
        plt.colorbar(scatter, ax=ax9, label='Altitude (m)')
        ax9.grid(True, alpha=0.3)

        plt.suptitle('Comprehensive Correlation Analysis - All Parameters',
                    fontsize=18, fontweight='bold', y=0.995)
        plt.tight_layout(rect=[0, 0, 1, 0.99])

        output_file = Path(self.data_path).parent / output_path
        plt.savefig(str(output_file), dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Saved: {output_file}")

    def generate_correlation_report(self, output_path="correlation_report.txt"):
        """상관관계 분석 리포트 생성"""
        print(f"\n📝 Generating correlation report...")

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("종합 상관관계 분석 리포트")
        report_lines.append("Comprehensive Correlation Analysis Report")
        report_lines.append("=" * 80)
        report_lines.append("")

        # 데이터 개요
        report_lines.append("📊 데이터 개요 (Data Overview)")
        report_lines.append("-" * 80)
        report_lines.append(f"총 샘플 수: {len(self.df)}")
        report_lines.append(f"총 변수 수: {len(self.df.columns)}")
        report_lines.append(f"수치형 변수 수: {len(self.df.select_dtypes(include=[np.number]).columns)}")
        report_lines.append("")

        # 유의미한 상관관계 요약
        report_lines.append("🎯 주요 발견사항 (Key Findings)")
        report_lines.append("-" * 80)

        significant = self.find_significant_correlations(threshold=0.3)

        for quality_var, corr_series in significant.items():
            report_lines.append(f"\n📌 {quality_var} 상관관계:")
            report_lines.append("")

            for var, corr_value in corr_series.head(10).items():
                direction = "양의" if corr_value > 0 else "음의"
                strength = "강한" if abs(corr_value) > 0.5 else "중간"

                report_lines.append(f"  • {var:30s}: {corr_value:+.3f} ({strength} {direction} 상관)")

            report_lines.append("")

        # 비행 단계별 품질 통계
        report_lines.append("\n🛫 비행 단계별 통신 품질 (Quality by Flight Phase)")
        report_lines.append("-" * 80)

        phase_stats = self.df.groupby('flight_phase').agg({
            'altitude': ['count', 'mean', 'min', 'max'],
            'lte_rssi': 'mean',
            'starlink_latency': 'mean',
            'speed_mps': 'mean'
        }).round(2)

        report_lines.append(str(phase_stats))
        report_lines.append("")

        # 리포트 저장
        output_file = Path(self.data_path).parent / output_path
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        print(f"✓ Saved: {output_file}")

        # 콘솔 출력
        print("\n" + '\n'.join(report_lines[:50]))  # 처음 50줄만 출력


def main():
    """메인 실행"""
    base_dir = Path(__file__).parent
    merged_data = base_dir / "merged_flight_data.csv"

    analyzer = ComprehensiveCorrelationAnalyzer(str(merged_data))
    analyzer.load_and_prepare_data()
    analyzer.compute_correlations()
    analyzer.find_significant_correlations(threshold=0.3)
    analyzer.visualize_correlations()
    analyzer.generate_correlation_report()

    print("\n" + "="*80)
    print("✅ COMPREHENSIVE CORRELATION ANALYSIS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
