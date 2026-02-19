#!/usr/bin/env python3
"""
Cross-Session 비교 분석 스크립트
4개 세션의 통신 품질 데이터를 비교 분석하여 공통 패턴과 변화 추이를 도출

Sessions:
- 2026-01-23 (1ed55628): 8,101 points
- 2026-02-05 (9dbb5928): 17,147 points
- 2026-02-12 (7a8259f5): 52,365 points
- 2026-02-13 (0287eaf7): 27,248 points
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.font_manager as fm

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

def load_session_summaries():
    """4개 세션의 요약 데이터 로드"""

    sessions = [
        {'id': '1ed55628-37b6-4097-b796-8faef759db14', 'date': '2026-01-23', 'label': '01-23'},
        {'id': '9dbb5928-8c0d-4feb-9d38-c6701d9317be', 'date': '2026-02-05', 'label': '02-05'},
        {'id': '7a8259f5-b794-4089-8ce3-9edb8db2ac88', 'date': '2026-02-12', 'label': '02-12 (고흥)'},
        {'id': '0287eaf7-45c3-41f6-b676-1154d09c2ff4', 'date': '2026-02-13', 'label': '02-13'}
    ]

    summaries = []
    base_dir = Path(__file__).parent

    for session in sessions:
        session_date = session['date'].replace('-', '')

        # session_summary.csv 로드
        summary_file = base_dir / f'session_{session_date}' / 'session_summary.csv'
        if summary_file.exists():
            df = pd.read_csv(summary_file)
            df['label'] = session['label']
            summaries.append(df)
        else:
            print(f"⚠️ {session['label']} session_summary.csv 없음")

    if summaries:
        return pd.concat(summaries, ignore_index=True)
    else:
        return None

def load_lte_statistics():
    """4개 세션의 LTE 통계 데이터 로드"""

    sessions = [
        {'date': '20260123', 'label': '01-23'},
        {'date': '20260205', 'label': '02-05'},
        {'date': '20260212', 'label': '02-12 (고흥)'},
        {'date': '20260213', 'label': '02-13'}
    ]

    lte_stats = []
    base_dir = Path(__file__).parent

    for session in sessions:
        lte_file = base_dir / f'session_{session["date"]}' / 'lte_statistics.csv'
        if lte_file.exists():
            df = pd.read_csv(lte_file)
            df['session'] = session['label']
            lte_stats.append(df)
        else:
            print(f"⚠️ {session['label']} lte_statistics.csv 없음")

    if lte_stats:
        return pd.concat(lte_stats, ignore_index=True)
    else:
        return None

def analyze_temporal_trends(summary_df):
    """시간대별 변화 추이 분석"""

    print("\n" + "="*60)
    print("📈 시간대별 변화 추이 분석")
    print("="*60)

    # 시간 순서대로 정렬
    summary_df = summary_df.sort_values('session_date')

    print("\n세션별 통신 품질 변화:")
    print("-" * 60)
    for _, row in summary_df.iterrows():
        print(f"\n{row['label']} ({row['session_date']}):")
        print(f"  데이터 포인트: {row['total_points']:,}개")
        print(f"  RF 정상률: {row['rf_normal_pct']:.1f}%")
        print(f"  LTE 정상률: {row['lte_normal_pct']:.1f}%")
        print(f"  Starlink 정상률: {row['starlink_normal_pct']:.1f}%")
        print(f"  3-Layer 노랑: {row['yellow_pct']:.1f}%")
        print(f"  3-Layer 오렌지: {row['orange_pct']:.1f}%")

    return summary_df

def analyze_common_patterns(summary_df, lte_df):
    """공통 패턴 분석"""

    print("\n" + "="*60)
    print("🔍 공통 패턴 분석")
    print("="*60)

    # 1. RF/GPS 성능
    print("\n1️⃣ RF/GPS 성능:")
    rf_ok = summary_df['rf_normal_pct'] == 100.0
    if rf_ok.all():
        print("   ✅ 모든 세션에서 RF/GPS 100% 정상 (문제 없음)")
    else:
        print(f"   ⚠️ 일부 세션에서 RF/GPS 문제 발생")

    # 2. LTE 성능
    print("\n2️⃣ LTE 성능:")
    lte_normal = summary_df['lte_normal_pct']
    print(f"   평균 정상률: {lte_normal.mean():.1f}%")
    print(f"   범위: {lte_normal.min():.1f}% ~ {lte_normal.max():.1f}%")

    # LTE SINR 문제 분석
    if lte_df is not None:
        print("\n   SINR Poor (<0 dB) 비율:")
        sinr_data = lte_df[lte_df['metric'] == 'SINR']
        for _, row in sinr_data.iterrows():
            if not pd.isna(row['poor_pct']):
                print(f"      {row['session']}: {row['poor_pct']:.1f}%")

        # 패턴 분석
        sinr_poor = sinr_data[sinr_data['poor_pct'].notna()]['poor_pct']
        if len(sinr_poor) >= 2:
            high_sinr_sessions = sinr_poor[sinr_poor > 40].count()
            if high_sinr_sessions >= 2:
                print(f"\n   🚨 공통 문제: {high_sinr_sessions}개 세션에서 SINR Poor > 40% (간섭/잡음 문제)")

    # 3. Starlink 성능
    print("\n3️⃣ Starlink 성능:")
    starlink_normal = summary_df['starlink_normal_pct']
    print(f"   평균 정상률: {starlink_normal.mean():.1f}%")
    print(f"   최대 정상률: {starlink_normal.max():.1f}%")

    if starlink_normal.max() < 1.0:
        print("   🚨 공통 문제: 모든 세션에서 Starlink < 1% 정상 (In-motion 정책 제한 추정)")

    # 4. 3-Layer 통합
    print("\n4️⃣ 3-Layer 통합 품질:")
    green_pct = summary_df['green_pct']
    print(f"   초록(3/3) 평균: {green_pct.mean():.1f}%")

    if green_pct.max() == 0.0:
        print("   🚨 공통 문제: 모든 세션에서 완벽한 통신(초록) 0% (RF + LTE + Starlink 동시 정상 없음)")

    yellow_pct = summary_df['yellow_pct']
    orange_pct = summary_df['orange_pct']
    print(f"   노랑(2/3) 평균: {yellow_pct.mean():.1f}%")
    print(f"   오렌지(1/3) 평균: {orange_pct.mean():.1f}%")

def analyze_data_quality_issues(summary_df):
    """데이터 품질 이슈 분석"""

    print("\n" + "="*60)
    print("⚠️ 데이터 품질 이슈 분석")
    print("="*60)

    # LTE 데이터 손상 확인
    lte_zero = summary_df[summary_df['lte_normal_pct'] == 0.0]
    if len(lte_zero) > 0:
        print("\n❌ LTE 데이터 손상 세션:")
        for _, row in lte_zero.iterrows():
            print(f"   {row['label']}: LTE 정상률 0.0% (데이터 수집 실패 또는 모듈 고장)")

    # Starlink 연결 상태 확인 (간접 지표)
    starlink_low = summary_df[summary_df['starlink_normal_pct'] < 0.1]
    if len(starlink_low) > 0:
        print("\n⚠️ Starlink 심각한 불량 세션:")
        for _, row in starlink_low.iterrows():
            print(f"   {row['label']}: Starlink 정상률 {row['starlink_normal_pct']:.2f}%")

def generate_comparison_charts(summary_df, lte_df):
    """비교 차트 생성"""

    print("\n" + "="*60)
    print("📊 비교 차트 생성")
    print("="*60)

    output_dir = Path(__file__).parent

    # 차트 1: 세션별 통신 품질 정상률 비교 (3-Panel)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('세션별 통신 품질 정상률 비교', fontsize=16, fontweight='bold', y=1.02)

    # Panel 1: RF/LTE/Starlink 정상률
    ax1 = axes[0]
    x = np.arange(len(summary_df))
    width = 0.25

    ax1.bar(x - width, summary_df['rf_normal_pct'], width, label='RF/GPS', color='#2EBD85', alpha=0.8)
    ax1.bar(x, summary_df['lte_normal_pct'], width, label='LTE', color='#F6465D', alpha=0.8)
    ax1.bar(x + width, summary_df['starlink_normal_pct'], width, label='Starlink', color='#FFA500', alpha=0.8)

    ax1.set_xlabel('세션', fontsize=12)
    ax1.set_ylabel('정상률 (%)', fontsize=12)
    ax1.set_title('RF / LTE / Starlink 정상률', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(summary_df['label'], rotation=0)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_ylim(0, 110)

    # Panel 2: 3-Layer 색상 분포
    ax2 = axes[1]
    colors_data = summary_df[['green_pct', 'yellow_pct', 'orange_pct', 'red_pct']].values

    bottom = np.zeros(len(summary_df))
    color_map = ['#2EBD85', '#F6B817', '#FFA500', '#F6465D']
    labels = ['초록 (3/3)', '노랑 (2/3)', '오렌지 (1/3)', '레드 (0/3)']

    for i in range(4):
        ax2.bar(summary_df['label'], colors_data[:, i], bottom=bottom,
                label=labels[i], color=color_map[i], alpha=0.8)
        bottom += colors_data[:, i]

    ax2.set_xlabel('세션', fontsize=12)
    ax2.set_ylabel('비율 (%)', fontsize=12)
    ax2.set_title('3-Layer 통합 품질 분포', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_ylim(0, 110)

    # Panel 3: LTE SINR Poor 비율
    if lte_df is not None:
        ax3 = axes[2]
        sinr_data = lte_df[lte_df['metric'] == 'SINR'].sort_values('session')

        sessions = sinr_data['session'].values
        poor_pct = sinr_data['poor_pct'].values

        # NaN 처리
        valid_mask = ~pd.isna(poor_pct)
        sessions_valid = sessions[valid_mask]
        poor_pct_valid = poor_pct[valid_mask]

        colors = ['#2EBD85' if p < 20 else '#F6B817' if p < 40 else '#F6465D' for p in poor_pct_valid]

        ax3.bar(sessions_valid, poor_pct_valid, color=colors, alpha=0.8)
        ax3.axhline(y=40, color='red', linestyle='--', linewidth=2, label='문제 기준선 (40%)')

        ax3.set_xlabel('세션', fontsize=12)
        ax3.set_ylabel('Poor 비율 (%)', fontsize=12)
        ax3.set_title('LTE SINR Poor (<0 dB) 비율', fontsize=14, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.set_ylim(0, 110)

    plt.tight_layout()
    chart_file = output_dir / 'cross_session_comparison.png'
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   ✅ {chart_file}")

    # 차트 2: 시간대별 변화 추이 (라인 차트)
    fig, ax = plt.subplots(figsize=(12, 6))

    x_pos = range(len(summary_df))

    ax.plot(x_pos, summary_df['lte_normal_pct'], marker='o', linewidth=2,
            label='LTE 정상률', color='#F6465D', markersize=8)
    ax.plot(x_pos, summary_df['starlink_normal_pct'], marker='s', linewidth=2,
            label='Starlink 정상률', color='#FFA500', markersize=8)
    ax.plot(x_pos, summary_df['yellow_pct'], marker='^', linewidth=2,
            label='3-Layer 노랑(2/3)', color='#F6B817', markersize=8)

    ax.set_xlabel('세션 (시간 순서)', fontsize=12)
    ax.set_ylabel('비율 (%)', fontsize=12)
    ax.set_title('시간대별 통신 품질 변화 추이', fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(summary_df['label'], rotation=0)
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(-5, 105)

    plt.tight_layout()
    trend_file = output_dir / 'cross_session_trends.png'
    plt.savefig(trend_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"   ✅ {trend_file}")

def save_cross_session_summary(summary_df, lte_df):
    """Cross-session 요약 데이터 저장"""

    print("\n" + "="*60)
    print("💾 Cross-Session 요약 데이터 저장")
    print("="*60)

    output_dir = Path(__file__).parent

    # 1. 세션별 요약
    summary_df.to_csv(output_dir / 'cross_session_summary.csv', index=False)
    print(f"   ✅ cross_session_summary.csv")

    # 2. LTE 통계 비교
    if lte_df is not None:
        lte_df.to_csv(output_dir / 'cross_session_lte_comparison.csv', index=False)
        print(f"   ✅ cross_session_lte_comparison.csv")

    # 3. 종합 분석 결과
    analysis_results = {
        'total_sessions': len(summary_df),
        'total_data_points': summary_df['total_points'].sum(),
        'avg_rf_normal': summary_df['rf_normal_pct'].mean(),
        'avg_lte_normal': summary_df['lte_normal_pct'].mean(),
        'avg_starlink_normal': summary_df['starlink_normal_pct'].mean(),
        'avg_green': summary_df['green_pct'].mean(),
        'avg_yellow': summary_df['yellow_pct'].mean(),
        'avg_orange': summary_df['orange_pct'].mean(),
        'max_lte_normal': summary_df['lte_normal_pct'].max(),
        'min_lte_normal': summary_df['lte_normal_pct'].min(),
        'sessions_with_zero_green': (summary_df['green_pct'] == 0).sum(),
        'sessions_with_lte_issues': (summary_df['lte_normal_pct'] < 20).sum()
    }

    analysis_df = pd.DataFrame([analysis_results])
    analysis_df.to_csv(output_dir / 'cross_session_analysis_results.csv', index=False)
    print(f"   ✅ cross_session_analysis_results.csv")

    print("\n" + "="*60)
    print("📊 종합 분석 결과 요약")
    print("="*60)
    print(f"   총 세션 수: {analysis_results['total_sessions']}개")
    print(f"   총 데이터 포인트: {analysis_results['total_data_points']:,}개")
    print(f"   평균 RF 정상률: {analysis_results['avg_rf_normal']:.1f}%")
    print(f"   평균 LTE 정상률: {analysis_results['avg_lte_normal']:.1f}%")
    print(f"   평균 Starlink 정상률: {analysis_results['avg_starlink_normal']:.1f}%")
    print(f"   평균 3-Layer 초록: {analysis_results['avg_green']:.1f}%")
    print(f"   평균 3-Layer 노랑: {analysis_results['avg_yellow']:.1f}%")
    print(f"   평균 3-Layer 오렌지: {analysis_results['avg_orange']:.1f}%")
    print(f"   초록 0% 세션 수: {analysis_results['sessions_with_zero_green']}개")
    print(f"   LTE 문제 세션 수: {analysis_results['sessions_with_lte_issues']}개")

def main():
    """메인 실행 함수"""

    print("="*60)
    print("Cross-Session 비교 분석 시작")
    print("="*60)

    # 데이터 로드
    summary_df = load_session_summaries()
    lte_df = load_lte_statistics()

    if summary_df is None:
        print("❌ 세션 요약 데이터를 로드할 수 없습니다.")
        return

    # 분석 수행
    summary_df = analyze_temporal_trends(summary_df)
    analyze_common_patterns(summary_df, lte_df)
    analyze_data_quality_issues(summary_df)

    # 차트 생성
    generate_comparison_charts(summary_df, lte_df)

    # 요약 데이터 저장
    save_cross_session_summary(summary_df, lte_df)

    print("\n" + "="*60)
    print("✅ Cross-Session 비교 분석 완료")
    print("="*60)

if __name__ == '__main__':
    main()
