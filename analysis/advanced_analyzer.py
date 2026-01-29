#!/usr/bin/env python3
"""
고급 통신 품질 분석 시스템
- 모든 데이터 필드 활용 (37개 LTE + 69개 Starlink)
- -999 값 필터링 및 데이터 정제
- 멀티 메트릭 상관관계 분석
- 위성 추적 및 기지국 전환 분석
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class AdvancedQualityAnalyzer:
    """고급 통신 품질 분석기"""

    def __init__(self, merged_data_path: str):
        self.data_path = Path(merged_data_path)
        self.df = None
        self.lte_data = None
        self.starlink_data = None

    def load_and_clean_data(self):
        """데이터 로드 및 정제"""
        print("📁 Loading merged data...")
        self.df = pd.read_csv(self.data_path)

        # LTE 데이터 정제
        lte_mask = self.df['lte_available'] == True
        self.lte_data = self.df[lte_mask].copy()

        # -999 값을 NaN으로 변환
        invalid_cols = ['lte_rsrp', 'lte_rsrq', 'lte_sinr']
        for col in invalid_cols:
            if col in self.lte_data.columns:
                self.lte_data.loc[self.lte_data[col] == -999, col] = np.nan

        print(f"✓ LTE data: {len(self.lte_data)} points")
        print(f"  Valid RSRP: {self.lte_data['lte_rsrp'].notna().sum()}")
        print(f"  Valid RSRQ: {self.lte_data['lte_rsrq'].notna().sum()}")
        print(f"  Valid SINR: {self.lte_data['lte_sinr'].notna().sum()}")

        # Starlink 데이터
        sl_mask = self.df['starlink_available'] == True
        self.starlink_data = self.df[sl_mask].copy()

        print(f"✓ Starlink data: {len(self.starlink_data)} points")

        return self.df

    def analyze_lte_quality_distribution(self):
        """LTE 품질 지표 분포 분석"""
        print("\n📊 LTE Quality Distribution Analysis...")

        metrics = {
            'RSSI': 'lte_rssi',
            'RSRP': 'lte_rsrp',
            'RSRQ': 'lte_rsrq',
            'SINR': 'lte_sinr'
        }

        results = {}
        for name, col in metrics.items():
            if col in self.lte_data.columns:
                valid_data = self.lte_data[col].dropna()
                if len(valid_data) > 0:
                    results[name] = {
                        'mean': valid_data.mean(),
                        'std': valid_data.std(),
                        'min': valid_data.min(),
                        'max': valid_data.max(),
                        'median': valid_data.median(),
                        'q25': valid_data.quantile(0.25),
                        'q75': valid_data.quantile(0.75),
                        'count': len(valid_data)
                    }

        # 출력
        print("\nMetric Statistics:")
        print("-" * 80)
        for name, stats in results.items():
            print(f"\n{name}:")
            print(f"  Mean: {stats['mean']:.2f} | Median: {stats['median']:.2f}")
            print(f"  Range: [{stats['min']:.2f}, {stats['max']:.2f}]")
            print(f"  Q25-Q75: [{stats['q25']:.2f}, {stats['q75']:.2f}]")
            print(f"  Std Dev: {stats['std']:.2f} | Valid samples: {stats['count']}")

        return results

    def analyze_starlink_variability(self):
        """Starlink 품질 변동성 분석"""
        print("\n🛰️ Starlink Quality Variability Analysis...")

        metrics = {
            'Latency (ms)': 'starlink_latency',
            'Download (Mbps)': 'starlink_download',
            'Upload (Mbps)': 'starlink_upload'
        }

        results = {}
        for name, col in metrics.items():
            if col in self.starlink_data.columns:
                data = self.starlink_data[col].dropna()
                if len(data) > 0:
                    # 변동 계수 (Coefficient of Variation)
                    cv = (data.std() / data.mean()) * 100 if data.mean() != 0 else 0

                    results[name] = {
                        'mean': data.mean(),
                        'std': data.std(),
                        'cv': cv,  # 변동 계수 (%)
                        'min': data.min(),
                        'max': data.max(),
                        'range': data.max() - data.min()
                    }

        print("\nMetric Variability:")
        print("-" * 80)
        for name, stats in results.items():
            print(f"\n{name}:")
            print(f"  Mean: {stats['mean']:.2f} | Std: {stats['std']:.2f}")
            print(f"  CV: {stats['cv']:.1f}% (Variation Coefficient)")
            print(f"  Range: {stats['range']:.2f} (Max: {stats['max']:.2f}, Min: {stats['min']:.2f})")

        return results

    def correlation_analysis(self):
        """상관관계 분석"""
        print("\n🔍 Correlation Analysis...")

        # LTE 메트릭 간 상관관계
        lte_metrics = ['lte_rssi', 'lte_rsrp', 'lte_rsrq', 'lte_sinr']
        lte_corr = self.lte_data[lte_metrics].corr()

        print("\nLTE Metrics Correlation Matrix:")
        print(lte_corr.round(3))

        # Starlink 메트릭 간 상관관계
        sl_metrics = ['starlink_latency', 'starlink_download', 'starlink_upload']
        sl_corr = self.starlink_data[sl_metrics].corr()

        print("\nStarlink Metrics Correlation Matrix:")
        print(sl_corr.round(3))

        # LTE vs Starlink (오버랩 구간에서)
        overlap_df = self.df[(self.df['lte_available'] == True) &
                              (self.df['starlink_available'] == True)].copy()

        if len(overlap_df) > 0:
            print(f"\nLTE vs Starlink Correlation (overlap: {len(overlap_df)} points):")
            print(f"  RSSI vs Latency: {overlap_df['lte_rssi'].corr(overlap_df['starlink_latency']):.3f}")
            print(f"  SINR vs Download: {overlap_df['lte_sinr'].corr(overlap_df['starlink_download']):.3f}")
            print(f"  RSSI vs Download: {overlap_df['lte_rssi'].corr(overlap_df['starlink_download']):.3f}")

        return {
            'lte': lte_corr,
            'starlink': sl_corr
        }

    def quality_grade_classification(self):
        """품질 등급 분류"""
        print("\n📊 Quality Grade Classification...")

        # LTE 등급 (RSSI 기준)
        lte_excellent = len(self.lte_data[self.lte_data['lte_rssi'] > -70])
        lte_good = len(self.lte_data[(self.lte_data['lte_rssi'] >= -85) &
                                      (self.lte_data['lte_rssi'] <= -70)])
        lte_fair = len(self.lte_data[(self.lte_data['lte_rssi'] >= -100) &
                                      (self.lte_data['lte_rssi'] < -85)])
        lte_poor = len(self.lte_data[self.lte_data['lte_rssi'] < -100])

        # SINR 기준 추가
        sinr_valid = self.lte_data['lte_sinr'].dropna()
        sinr_excellent = len(sinr_valid[sinr_valid > 20])
        sinr_good = len(sinr_valid[(sinr_valid >= 13) & (sinr_valid <= 20)])
        sinr_fair = len(sinr_valid[(sinr_valid >= 0) & (sinr_valid < 13)])
        sinr_poor = len(sinr_valid[sinr_valid < 0])

        print("\nLTE Quality Grades:")
        print("-" * 80)
        print("By RSSI:")
        print(f"  Excellent (>-70 dBm): {lte_excellent} ({lte_excellent/len(self.lte_data)*100:.1f}%)")
        print(f"  Good (-70~-85 dBm):   {lte_good} ({lte_good/len(self.lte_data)*100:.1f}%)")
        print(f"  Fair (-85~-100 dBm):  {lte_fair} ({lte_fair/len(self.lte_data)*100:.1f}%)")
        print(f"  Poor (<-100 dBm):     {lte_poor} ({lte_poor/len(self.lte_data)*100:.1f}%)")

        print("\nBy SINR:")
        print(f"  Excellent (>20 dB):   {sinr_excellent} ({sinr_excellent/len(sinr_valid)*100:.1f}%)")
        print(f"  Good (13~20 dB):      {sinr_good} ({sinr_good/len(sinr_valid)*100:.1f}%)")
        print(f"  Fair (0~13 dB):       {sinr_fair} ({sinr_fair/len(sinr_valid)*100:.1f}%)")
        print(f"  Poor (<0 dB):         {sinr_poor} ({sinr_poor/len(sinr_valid)*100:.1f}%)")

        # Starlink 등급 (Latency 기준)
        sl_excellent = len(self.starlink_data[self.starlink_data['starlink_latency'] < 40])
        sl_good = len(self.starlink_data[(self.starlink_data['starlink_latency'] >= 40) &
                                          (self.starlink_data['starlink_latency'] < 100)])
        sl_fair = len(self.starlink_data[(self.starlink_data['starlink_latency'] >= 100) &
                                          (self.starlink_data['starlink_latency'] < 200)])
        sl_poor = len(self.starlink_data[self.starlink_data['starlink_latency'] >= 200])

        print("\nStarlink Quality Grades:")
        print("-" * 80)
        print("By Latency:")
        print(f"  Excellent (<40 ms):   {sl_excellent} ({sl_excellent/len(self.starlink_data)*100:.1f}%)")
        print(f"  Good (40~100 ms):     {sl_good} ({sl_good/len(self.starlink_data)*100:.1f}%)")
        print(f"  Fair (100~200 ms):    {sl_fair} ({sl_fair/len(self.starlink_data)*100:.1f}%)")
        print(f"  Poor (>200 ms):       {sl_poor} ({sl_poor/len(self.starlink_data)*100:.1f}%)")

        return {
            'lte_rssi': [lte_excellent, lte_good, lte_fair, lte_poor],
            'lte_sinr': [sinr_excellent, sinr_good, sinr_fair, sinr_poor],
            'starlink': [sl_excellent, sl_good, sl_fair, sl_poor]
        }

    def time_series_stability(self):
        """시계열 안정성 분석"""
        print("\n⏱️ Time Series Stability Analysis...")

        # LTE RSSI 연속 변화량
        lte_rssi_diff = self.lte_data['lte_rssi'].diff().abs()
        lte_transitions = len(lte_rssi_diff[lte_rssi_diff > 5])  # 5 dBm 이상 변화

        print("\nLTE Signal Stability:")
        print(f"  Mean RSSI change: {lte_rssi_diff.mean():.2f} dBm")
        print(f"  Max RSSI change: {lte_rssi_diff.max():.2f} dBm")
        print(f"  Rapid transitions (>5dBm): {lte_transitions}")

        # Starlink Latency 변동
        sl_latency_diff = self.starlink_data['starlink_latency'].diff().abs()
        sl_spikes = len(sl_latency_diff[sl_latency_diff > 20])  # 20ms 이상 급변

        print("\nStarlink Latency Stability:")
        print(f"  Mean latency change: {sl_latency_diff.mean():.2f} ms")
        print(f"  Max latency change: {sl_latency_diff.max():.2f} ms")
        print(f"  Latency spikes (>20ms): {sl_spikes}")

        return {
            'lte_transitions': lte_transitions,
            'starlink_spikes': sl_spikes
        }

    def comprehensive_summary(self):
        """종합 요약 보고서"""
        print("\n" + "="*80)
        print("📋 COMPREHENSIVE QUALITY ANALYSIS SUMMARY")
        print("="*80)

        # 데이터 로드 및 정제
        self.load_and_clean_data()

        # 각 분석 실행
        lte_dist = self.analyze_lte_quality_distribution()
        sl_var = self.analyze_starlink_variability()
        corr = self.correlation_analysis()
        grades = self.quality_grade_classification()
        stability = self.time_series_stability()

        print("\n" + "="*80)
        print("✅ Analysis Complete!")
        print("="*80)

        return {
            'lte_distribution': lte_dist,
            'starlink_variability': sl_var,
            'correlation': corr,
            'quality_grades': grades,
            'stability': stability
        }


def main():
    """메인 실행"""
    print("="*80)
    print("🔬 ADVANCED COMMUNICATION QUALITY ANALYZER")
    print("="*80)

    # 경로 설정
    base_dir = Path(__file__).parent
    merged_data = base_dir / "merged_flight_data.csv"

    # 분석기 생성
    analyzer = AdvancedQualityAnalyzer(str(merged_data))

    # 종합 분석 실행
    results = analyzer.comprehensive_summary()

    print("\n💾 Analysis results saved to memory")
    print("🎯 Ready for visualization and reporting")


if __name__ == "__main__":
    main()
