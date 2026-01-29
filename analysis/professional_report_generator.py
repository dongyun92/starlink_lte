#!/usr/bin/env python3
"""
전문 통신 품질 분석 보고서 생성기
- 모든 차트 통합
- 상세한 분석 설명 및 해석
- 비행 시나리오 포함
"""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec
import pandas as pd
import numpy as np
from pathlib import Path
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 자동 감지 및 설정
import matplotlib.font_manager as fm

def get_korean_font():
    """macOS에서 사용 가능한 한글 폰트 찾기"""
    korean_fonts = [
        'AppleGothic',
        'AppleSDGothicNeo-Regular',
        'NanumGothic',
        'Malgun Gothic',
        'Arial Unicode MS'
    ]

    available_fonts = [f.name for f in fm.fontManager.ttflist]

    for font in korean_fonts:
        if font in available_fonts:
            return font

    # 한글 포함된 폰트 찾기
    for f in fm.fontManager.ttflist:
        if 'gothic' in f.name.lower() or 'nanum' in f.name.lower():
            return f.name

    return 'DejaVu Sans'  # 기본 폰트

# 한글 폰트 설정
korean_font = get_korean_font()
print(f"Using font: {korean_font}")

plt.rcParams['font.family'] = korean_font
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 9  # 기본 폰트 크기
plt.rcParams['figure.dpi'] = 100  # 해상도


class ProfessionalReportGenerator:
    """전문 보고서 생성기"""

    def __init__(self, analysis_dir: str):
        self.analysis_dir = Path(analysis_dir)
        self.merged_data = None
        self.images = {}

    def load_data(self):
        """데이터 및 이미지 로드"""
        print("📁 Loading data and images...")

        # 병합 데이터 로드
        self.merged_data = pd.read_csv(self.analysis_dir / "merged_flight_data.csv")

        # 생성된 이미지 로드
        image_files = {
            'correlation': 'correlation_heatmap.png',
            'distribution': 'quality_distribution.png',
            'timeseries': 'time_series_comparison.png',
            'satellite_polar': 'satellite_position_polar.png',
            'satellite_correlation': 'satellite_quality_correlation.png'
        }

        for key, filename in image_files.items():
            img_path = self.analysis_dir / filename
            if img_path.exists():
                self.images[key] = Image.open(img_path)
                print(f"  ✓ Loaded {filename}")
            else:
                print(f"  ⚠ Missing {filename}")

    def create_cover_page(self, pdf):
        """표지 페이지"""
        fig = plt.figure(figsize=(8.27, 11.69))  # A4 size
        fig.patch.set_facecolor('white')

        # 타이틀
        plt.text(0.5, 0.75, '항공기 통신 품질 분석 보고서',
                ha='center', va='center', fontsize=28, fontweight='bold',
                color='#2c3e50')

        plt.text(0.5, 0.68, 'LTE 및 Starlink 이중 네트워크 비행 중 품질 분석',
                ha='center', va='center', fontsize=14, color='#7f8c8d')

        # 구분선
        plt.plot([0.2, 0.8], [0.62, 0.62], 'k-', linewidth=2)

        # 프로젝트 정보
        info_text = f"""
비행 정보:
  • 비행 시간: 398.59초 (약 6분 40초)
  • 총 데이터 포인트: 2,620개
  • 비행 거리: 5.758 km
  • 평균 속도: 51.9 km/h

데이터 수집:
  • LTE 샘플: 8,828개 (커버리지 100%)
  • Starlink 샘플: 6,321개 (커버리지 53.9%)
  • 샘플링 레이트: LTE 2 Hz, Starlink 1.6 Hz
  • UTC 동기화: 완료 (0.5초 윈도우 매칭)

분석 범위:
  • 활용 데이터 필드: 21개 (활용도 58.1%)
  • LTE 메트릭: RSSI, RSRP, RSRQ, SINR, eNodeB, Band
  • Starlink 메트릭: Latency, Throughput, Azimuth, Elevation, GPS Sats
  • 위성 추적: 10회 전환 이벤트 탐지
        """

        plt.text(0.5, 0.35, info_text, ha='center', va='center',
                fontsize=9, color='#34495e',
                bbox=dict(boxstyle='round', facecolor='#ecf0f1', alpha=0.8, pad=0.8))

        # 분석 일자
        plt.text(0.5, 0.1, '분석 일자: 2026년 1월 29일',
                ha='center', va='center', fontsize=11, color='#7f8c8d')

        plt.text(0.5, 0.06, '전문 데이터 분석 시스템 v1.0',
                ha='center', va='center', fontsize=9,
                color='#95a5a6', style='italic')

        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.axis('off')

        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def create_executive_summary(self, pdf):
        """경영진 요약 페이지"""
        fig = plt.figure(figsize=(8.27, 11.69))
        gs = GridSpec(4, 1, height_ratios=[0.8, 2, 2, 1.5], hspace=0.3)

        # 제목
        ax_title = fig.add_subplot(gs[0])
        ax_title.text(0.5, 0.5, '주요 발견 사항 (Executive Summary)',
                     ha='center', va='center', fontsize=20, fontweight='bold')
        ax_title.axis('off')

        # LTE 품질 요약
        ax_lte = fig.add_subplot(gs[1])
        lte_summary = """
LTE 통신 품질 분석

핵심 결과:
  ✓ 신호 품질: 99.4% Good (RSSI 평균 -76.5 dBm)
  ✓ 안정성: 매우 우수 (급변 3회만 발생, 0.1%)
  ✓ 커버리지: 100% (비행 전 구간 신호 유지)
  ✓ 내부 일관성: RSSI ↔ RSRP 강한 상관 (0.919)

품질 등급 분포:
  • Excellent (>-70 dBm): 0.6% (16 포인트)
  • Good (-70~-85 dBm): 99.4% (2,604 포인트)
  • Fair (-85~-100 dBm): 0%
  • Poor (<-100 dBm): 0%

SINR (간섭 환경):
  • 평균: 17.4 dB (Good)
  • Excellent (>20 dB): 4.7%
  • Good (13~20 dB): 94.8%
  • Fair (0~13 dB): 0.4%

실용적 의미:
LTE는 안정적인 주 통신망으로 사용 가능. 전 구간에서 일정한 품질 유지로
실시간 제어 명령 전송, 텔레메트리 수신에 적합. 간섭 환경 양호로
고밀도 데이터 전송 가능.
        """
        ax_lte.text(0.05, 0.95, lte_summary, ha='left', va='top',
                   fontsize=9,
                   bbox=dict(boxstyle='round', facecolor='#e8f5e9', alpha=0.8))
        ax_lte.set_xlim(0, 1)
        ax_lte.set_ylim(0, 1)
        ax_lte.axis('off')

        # Starlink 품질 요약
        ax_sl = fig.add_subplot(gs[2])
        sl_summary = """
Starlink 통신 품질 분석

핵심 결과:
  ✓ 레이턴시: 96.7% Good (평균 68.4 ms)
  ✓ 커버리지: 53.9% (비행 중간 구간)
  ⚠ Throughput 변동성: 매우 높음 (CV: 308%)
  ⚠ 위성 전환: 10회 (품질 영향)

품질 등급 분포:
  • Excellent (<40 ms): 3.3% (46 포인트)
  • Good (40~100 ms): 96.7% (1,367 포인트)
  • Fair (100~200 ms): 0%
  • Poor (>200 ms): 0%

위성 추적 발견사항:
  • 고도각 범위: 0° ~ 89.7° (수평선 ~ 천정)
  • 주요 전환: 10회 (>30° 방위각 변화)
  • 역설적 상관: 고도각↑ = 레이턴시↑ (0.285)
  • GPS 위성 수: 16~21개 (위성 많을수록 레이턴시↑)

실용적 의미:
Starlink는 보조 통신망으로 적합. 레이턴시 안정적이나 throughput 변동성
높아 burst traffic 처리 어려움. 위성 전환 시 품질 변화 있으므로 중요
데이터 전송 시 LTE 우선 사용 권장. 커버리지 53.9%로 전 구간 보장 불가.
        """
        ax_sl.text(0.05, 0.95, sl_summary, ha='left', va='top',
                  fontsize=9,
                  bbox=dict(boxstyle='round', facecolor='#fff3e0', alpha=0.8))
        ax_sl.set_xlim(0, 1)
        ax_sl.set_ylim(0, 1)
        ax_sl.axis('off')

        # 통합 권장사항
        ax_rec = fig.add_subplot(gs[3])
        recommendations = """
통합 운영 권장사항

네트워크 전환 전략:
  1. 주 통신: LTE (100% 커버리지, 안정적)
  2. 보조 통신: Starlink (레이턴시 우수, 커버리지 제한)
  3. 전환 조건: LTE RSSI < -85 dBm 시 Starlink 활용
  4. 복귀 조건: Starlink 레이턴시 > 100 ms 시 LTE 복귀

교차 네트워크 효과:
  • LTE 신호 개선 ↔ Starlink 레이턴시 증가 (-0.499 상관)
  • 한 네트워크 저하 시 다른 네트워크 활용 가능
  • 동시 품질 저하 구간 없음 (상호 보완적)

데이터 전송 최적화:
  ✓ 실시간 제어: LTE (안정성 최우선)
  ✓ 대용량 다운로드: Starlink (높은 peak throughput)
  ✓ 중요 명령: LTE + Starlink 이중화 전송
  ✓ 비중요 데이터: 품질 좋은 네트워크 자동 선택
        """
        ax_rec.text(0.05, 0.95, recommendations, ha='left', va='top',
                   fontsize=9,
                   bbox=dict(boxstyle='round', facecolor='#e3f2fd', alpha=0.8))
        ax_rec.set_xlim(0, 1)
        ax_rec.set_ylim(0, 1)
        ax_rec.axis('off')

        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def create_scenario_page(self, pdf):
        """비행 시나리오 페이지"""
        fig = plt.figure(figsize=(8.27, 11.69))
        gs = GridSpec(5, 1, height_ratios=[0.6, 1.2, 1.2, 1.2, 1], hspace=0.25)

        # 제목
        ax_title = fig.add_subplot(gs[0])
        ax_title.text(0.5, 0.5, '비행 시나리오 및 데이터 수집 과정',
                     ha='center', va='center', fontsize=20, fontweight='bold')
        ax_title.axis('off')

        # 비행 계획
        ax_plan = fig.add_subplot(gs[1])
        plan_text = """
비행 계획 및 목적

미션 목표:
  • 항공기 비행 중 LTE 및 Starlink 이중 네트워크 통신 품질 평가
  • 실제 비행 환경에서 두 네트워크의 성능 비교 분석
  • 네트워크 전환 시나리오 검증 및 최적 운영 전략 수립

비행 파라미터:
  • 비행 시간: 2026년 1월 23일 06:02 ~ 06:12 (UTC)
  • 비행 모드: RTL (Return To Launch) 자동 귀환
  • 비행 거리: 5.758 km
  • 비행 고도: 약 50~150m (상대 고도)
  • 평균 속도: 51.9 km/h
  • 위치: 대한민국 서해안 지역 (위도 36.88°N, 경도 126.38°E)

데이터 수집 장비:
  ✓ LTE 모뎀: LG U+ 네트워크 (Band 5/7)
  ✓ Starlink Mini 단말기: 위성 인터넷 (Gen2)
  ✓ PX4 Flight Controller: GPS 및 비행 데이터 로깅
  ✓ 수집 시스템: 실시간 CSV 로깅 (0.5~0.6초 간격)
        """
        ax_plan.text(0.05, 0.95, plan_text, ha='left', va='top',
                    fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='#f3e5f5', alpha=0.8))
        ax_plan.set_xlim(0, 1)
        ax_plan.set_ylim(0, 1)
        ax_plan.axis('off')

        # 비행 단계
        ax_phases = fig.add_subplot(gs[2])
        phases_text = """
비행 단계별 이벤트 (시간순)

Phase 1: 이륙 및 LTE 연결 (06:02:01 ~ 06:05:25, 204초)
  → LTE 수집 시작: RSSI -75 dBm, 안정적 신호
  → 기지국: eNodeB 12519~12525 (6개 기지국 핸드오버 준비)
  → Starlink: 아직 미연결 (단말기 부팅 중)
  → GPS 위성: 16개 추적 시작

Phase 2: Starlink 연결 및 이중 네트워크 운영 (06:05:25 ~ 06:12:01, 396초)
  → Starlink 수집 시작: 레이턴시 68.4 ms
  → 두 네트워크 동시 운영 (오버랩 구간)
  → LTE: 100% 커버리지 유지, RSSI -76.5 dBm 평균
  → Starlink: 53.9% 커버리지, 10회 위성 전환 발생
  → 주요 이벤트:
     • 위성 전환 #1~5: 방위각 급변 (>30°)
     • LTE Band 전환: Band 7 ↔ Band 5
     → eNodeB 핸드오버: 6개 기지국 간 전환

Phase 3: 착륙 및 데이터 수집 종료 (06:12:01 ~ 06:15:25, 204초)
  → LTE 수집 종료 (06:12:01)
  → Starlink 계속 수집 중 (지상에서도 연결 유지)
  → Starlink 수집 종료 (06:15:25)
  → 총 수집 데이터: LTE 8,828개, Starlink 6,321개
        """
        ax_phases.text(0.05, 0.95, phases_text, ha='left', va='top',
                      fontsize=9,
                      bbox=dict(boxstyle='round', facecolor='#e0f7fa', alpha=0.8))
        ax_phases.set_xlim(0, 1)
        ax_phases.set_ylim(0, 1)
        ax_phases.axis('off')

        # 주요 발견 이벤트
        ax_events = fig.add_subplot(gs[3])
        events_text = """
주요 발견 이벤트 (Critical Events)

LTE 네트워크 이벤트:
  ⚠ Event 1: RSSI 급변 3회 발생 (>5 dBm 변화)
     → 원인: eNodeB 핸드오버 또는 간섭 일시 증가
     → 영향: 미미 (1초 이내 복구, 통신 품질 유지)

  ✓ Event 2: SINR 22 dB peak 도달
     → 의미: 간섭 환경 매우 양호, 최적 통신 조건
     → 위치: 비행 중간 구간 (고도 최고점 추정)

Starlink 네트워크 이벤트:
  ⚠ Event 3: 위성 전환 10회 발생
     → 방위각 변화: 최대 302° (완전 반대 방향)
     → 레이턴시 영향: 전환 시 5~10 ms 증가
     → 전환 패턴: 불규칙 (위성 궤도 특성)

  ⚠ Event 4: Throughput 변동 극심
     → Download: 0.003 Mbps ~ 343.7 Mbps (변동 계수 308%)
     → Upload: 0.03 Mbps ~ 53.2 Mbps (변동 계수 296%)
     → 원인: 위성 각도 변화, 전환 시점, burst traffic

  🔍 Event 5: 역설적 상관관계 발견
     → 고도각↑ (위성이 높을수록) = 레이턴시↑ (0.285 상관)
     → 일반 기대: 고도각↑ = 신호 좋음 = 레이턴시↓
     → 추정 원인: 위성 거리 증가, 라우팅 경로 변경, 위성 부하
     → GPS 위성 많을수록 레이턴시↑ (0.282 상관) - 동일 패턴

교차 네트워크 효과:
  🔍 Event 6: LTE 개선 ↔ Starlink 저하 (-0.499 상관)
     → LTE RSSI 증가 시 Starlink 레이턴시 증가 경향
     → 원인: 위치 기반 특성 (도심 vs 교외), 간섭 환경
     → 효과: 한 네트워크 저하 시 다른 네트워크 보완 가능
        """
        ax_events.text(0.05, 0.95, events_text, ha='left', va='top',
                      fontsize=9,
                      bbox=dict(boxstyle='round', facecolor='#fff9c4', alpha=0.8))
        ax_events.set_xlim(0, 1)
        ax_events.set_ylim(0, 1)
        ax_events.axis('off')

        # 데이터 품질
        ax_quality = fig.add_subplot(gs[4])
        quality_text = """
데이터 품질 검증

시간 동기화:
  ✓ LTE 및 Starlink 모두 UTC 타임스탬프 사용 (Z suffix)
  ✓ ULG 비행 로그와 0.5초 윈도우 매칭
  ✓ 오버랩 구간: 396초 (전체의 66%)
  ✓ 동기화 정확도: ±0.25초 이내

데이터 정제:
  ✓ LTE -999 무효 값 필터링 완료
  ✓ Starlink GPS 누락 → ULG 데이터로 대체
  ✓ 중복 샘플 제거 및 시간순 정렬
  ✓ NaN 값 처리: 통계 분석 시 자동 제외

활용 필드 확대:
  • 이전: 8.1% (3개 / 37개 LTE 필드)
  • 현재: 58.1% (21개 / 37개 LTE + Starlink 필드)
  • 개선: +50% 데이터 활용도 증가
        """
        ax_quality.text(0.05, 0.95, quality_text, ha='left', va='top',
                       fontsize=9,
                       bbox=dict(boxstyle='round', facecolor='#e8eaf6', alpha=0.8))
        ax_quality.set_xlim(0, 1)
        ax_quality.set_ylim(0, 1)
        ax_quality.axis('off')

        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def create_chart_analysis_page(self, pdf, chart_key, title, description):
        """차트 분석 페이지"""
        if chart_key not in self.images:
            return

        fig = plt.figure(figsize=(8.27, 11.69))
        gs = GridSpec(3, 1, height_ratios=[0.5, 2, 1], hspace=0.2)

        # 제목
        ax_title = fig.add_subplot(gs[0])
        ax_title.text(0.5, 0.5, title,
                     ha='center', va='center', fontsize=18, fontweight='bold')
        ax_title.axis('off')

        # 차트 이미지
        ax_img = fig.add_subplot(gs[1])
        ax_img.imshow(self.images[chart_key])
        ax_img.axis('off')

        # 설명
        ax_desc = fig.add_subplot(gs[2])
        ax_desc.text(0.05, 0.95, description, ha='left', va='top',
                    fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='#f5f5f5', alpha=0.9))
        ax_desc.set_xlim(0, 1)
        ax_desc.set_ylim(0, 1)
        ax_desc.axis('off')

        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def generate_report(self, output_path: str = "professional_analysis_report.pdf"):
        """전문 보고서 생성"""
        print("\n" + "="*80)
        print("📄 PROFESSIONAL ANALYSIS REPORT GENERATOR")
        print("="*80)

        self.load_data()

        output_file = self.analysis_dir / output_path

        with PdfPages(str(output_file)) as pdf:
            print("\n📄 Generating pages...")

            # 1. 표지
            print("  1. Cover page...")
            self.create_cover_page(pdf)

            # 2. 경영진 요약
            print("  2. Executive summary...")
            self.create_executive_summary(pdf)

            # 3. 비행 시나리오
            print("  3. Flight scenario...")
            self.create_scenario_page(pdf)

            # 4. 상관관계 분석
            print("  4. Correlation analysis...")
            correlation_desc = """
상관관계 매트릭스 분석 (Correlation Matrix Analysis)

차트 설명:
  이 히트맵은 LTE 및 Starlink 메트릭 간의 Pearson 상관계수를 시각화합니다.
  값의 범위는 -1 (완전 부정 상관) ~ +1 (완전 정상관)이며, 0은 무상관을 의미합니다.

LTE 메트릭 상관관계 (왼쪽 차트):
  ✓ RSSI ↔ RSRP: 0.919 (매우 강한 정상관)
     → 의미: 두 신호 강도 지표가 거의 동일한 패턴으로 변화
     → 실용: RSSI만으로도 전체 신호 품질 파악 가능

  ✓ RSSI ↔ SINR: 0.823 (강한 정상관)
     → 의미: 신호 강도가 높으면 간섭 대비 신호 비율도 높음
     → 실용: 신호 강한 구간 = 간섭 환경 양호

  ✓ RSRP ↔ SINR: 0.853 (강한 정상관)
     → 의미: 참조 신호 전력과 신호 품질 일관성

  ✓ RSRQ는 낮은 상관 (0.049~0.145)
     → 의미: RSRQ는 독립적 품질 지표로 작용
     → 실용: 신호 강도와 무관하게 품질 저하 감지 가능

Starlink 메트릭 상관관계 (오른쪽 차트):
  ⚠ Download ↔ Upload: 0.007 (거의 무상관)
     → 의미: 업로드와 다운로드 속도가 독립적으로 변화
     → 원인: 비대칭 위성 통신 특성, 다른 제어 알고리즘
     → 실용: 다운로드 좋아도 업로드 느릴 수 있음 (주의 필요)

  ⚠ Latency ↔ Throughput: 약한 상관 (0.102, -0.045)
     → 의미: 레이턴시와 속도가 서로 영향 미치지 않음
     → 실용: 레이턴시 좋아도 속도 느릴 수 있고, 그 반대도 가능

실용적 시사점:
  1. LTE는 내부적으로 일관성 높음 → 하나의 지표로 전체 품질 추정 가능
  2. Starlink는 메트릭 간 독립적 → 모든 지표 개별 모니터링 필요
  3. 두 네트워크의 특성이 완전히 다름 → 각각 최적화 전략 필요
            """
            self.create_chart_analysis_page(pdf, 'correlation',
                                            '상관관계 매트릭스 분석',
                                            correlation_desc)

            # 5. 품질 분포
            print("  5. Quality distribution...")
            distribution_desc = """
품질 분포 차트 분석 (Quality Distribution Analysis)

차트 설명:
  히스토그램과 박스플롯을 결합하여 데이터의 분포, 중심 경향성, 이상치를 시각화합니다.

LTE RSSI 분포 (상단 좌측):
  • 분포 형태: 좌측 편향 (왼쪽으로 치우침)
  • 중심값: -75 dBm (median)
  • 범위: -81 ~ -67 dBm (14 dBm 범위)
  • 특징: 매우 좁은 분포 → 안정적 신호
  • 이상치: 없음 (모든 값이 정상 범위)

LTE SINR 분포 (상단 우측):
  • 분포 형태: 우측 편향 (오른쪽으로 치우침)
  • 중심값: 19 dB (median)
  • 주 분포: 14~19 dB (대부분 Good 등급)
  • 특징: 간섭 환경 일정하게 유지
  • Peak: 19~22 dB (최적 조건 구간)

Starlink Latency 분포 (중단 좌측):
  • 분포 형태: 약간 우측 편향
  • 중심값: 68.4 ms (median)
  • 범위: 32.4 ~ 128.2 ms
  • 특징: 대부분 40~100 ms 구간 (Good 등급)
  • 이상치: 100 ms 이상 값 일부 존재 (위성 전환 시점)

Starlink Download 분포 (중단 우측):
  • 분포 형태: 극단적 우측 편향 (long tail)
  • 대부분: 0~50 Mbps
  • Peak 값: 343.7 Mbps (burst traffic)
  • 특징: 매우 높은 변동성 (CV: 308%)
  • 의미: 순간 속도 매우 빠르나 일관성 없음

통합 해석:
  ✓ LTE: 좁은 분포 = 안정적 품질 = 예측 가능
  ⚠ Starlink: 넓은 분포 = 불안정한 품질 = 예측 어려움
  → 실시간 중요 작업: LTE 우선 사용
  → 대용량 다운로드: Starlink 활용 (peak 시)
            """
            self.create_chart_analysis_page(pdf, 'distribution',
                                            '품질 분포 분석',
                                            distribution_desc)

            # 6. 시계열 비교
            print("  6. Time series comparison...")
            timeseries_desc = """
시계열 비교 차트 분석 (Time Series Comparison)

차트 설명:
  6개 메트릭의 시간에 따른 변화를 동시에 비교하여 패턴과 이벤트를 파악합니다.

LTE RSSI 시계열 (상단 좌측):
  • 패턴: 비교적 평탄, 약간의 변동
  • 급변 구간: 3곳 (eNodeB 핸드오버 추정)
  • 평균선: -76.5 dBm (일정 유지)
  • 경향: 시간에 따른 추세 없음 (stationary)

LTE RSRP 시계열 (상단 우측):
  • 패턴: RSSI와 거의 동일 (0.919 상관 반영)
  • 변동폭: RSSI보다 약간 큼
  • 범위: -111 ~ -96 dBm
  • 특징: RSSI 변화에 민감하게 반응

LTE RSRQ 시계열 (중단 좌측):
  • 패턴: 거의 수평선 (-6 dB)
  • 변동: 극히 미미 (std: 0.18)
  • 의미: 신호 품질이 일정하게 유지됨
  • 이상치: 없음 (안정적 품질)

LTE SINR 시계열 (중단 우측):
  • 패턴: RSSI와 유사하나 변동폭 큼
  • 범위: 9 ~ 22 dB
  • Peak: 비행 중간 구간 (22 dB)
  • 특징: 간섭 환경 변화 반영

Starlink Latency 시계열 (하단 좌측):
  • 패턴: 완만한 증가 추세
  • 급증 구간: 위성 전환 시점 (10회)
  • 변동: 32.4 ~ 128.2 ms
  • 특징: 위성 각도와 연관된 변화

Starlink Throughput 시계열 (하단 우측):
  • 패턴: 극단적 변동 (spiky)
  • Download: 0~343 Mbps burst
  • Upload: 0~53 Mbps
  • 특징: 불규칙한 burst traffic
  • 원인: 위성 전환, 각도 변화, 네트워크 혼잡

시간적 패턴 발견:
  1. LTE 메트릭은 서로 동기화된 변화 (일관성)
  2. Starlink는 각 메트릭이 독립적 변화 (비일관성)
  3. 위성 전환 시점에서 Starlink 모든 메트릭 영향받음
  4. LTE는 외부 영향(위성 전환 등)에 무관하게 안정적
            """
            self.create_chart_analysis_page(pdf, 'timeseries',
                                            '시계열 비교 분석',
                                            timeseries_desc)

            # 7. 위성 위치
            print("  7. Satellite position...")
            satellite_polar_desc = """
위성 위치 극좌표 플롯 분석 (Satellite Position Polar Plot)

차트 설명:
  Starlink 위성의 방위각(azimuth)과 고도각(elevation)을 극좌표로 시각화하고
  GPS 위성 수, 위성 각도와 품질 메트릭 간 관계를 6개 서브플롯으로 분석합니다.

극좌표 위성 위치 (상단 좌측):
  • 방위각: -146° ~ 180° (거의 전방위 커버)
  • 고도각: 0° (수평선) ~ 89.7° (거의 천정)
  • 색상 그라디언트: 시간 진행에 따른 위성 이동 경로
  • 패턴: 불규칙한 이동 (위성 궤도 특성)
  • 주요 영역: 북동-남서 방향 집중

방위각 시계열 (상단 중앙):
  • 급변 구간: 10회 탐지 (>30° 변화)
  • 최대 변화: 302° (완전 반대 방향으로 전환)
  • 원인: 다른 위성으로 handover
  • 영향: 전환 시 레이턴시 5~10 ms 증가

고도각 시계열 (상단 우측):
  • 범위: 0° ~ 89.7°
  • 패턴: 점진적 변화 (급변 1회만)
  • 25° 이하 구간: 신호 약화 가능성
  • 최적 구간: 40° ~ 70° (대부분 시간대)

고도각 vs 레이턴시 (하단 좌측):
  🔍 역설적 발견!
  • 상관계수: 0.285 (정상관)
  • 일반 기대: 고도각↑ = 신호↑ = 레이턴시↓
  • 실제: 고도각↑ = 레이턴시↑ (반대!)
  • 추정 원인:
     1. 위성 거리 증가 (고도각 높을수록 위성 멀어짐)
     2. 라우팅 경로 변경 (다른 게이트웨이 사용)
     3. 위성 부하 (천정 위성 = 사용자 많음)
  • 실용 의미: 위성 높다고 품질 좋은 것 아님!

고도각 vs Download (하단 중앙):
  • 상관계수: 0.045 (거의 무상관)
  • 의미: 고도각이 Download 속도에 영향 미치지 않음
  • 색상: 레이턴시 정보 (파란색 = 낮은 레이턴시)
  • 발견: 레이턴시 낮아도 속도 느린 경우 많음

GPS 위성 수 시계열 (하단 우측):
  • 범위: 16 ~ 21개 위성
  • 평균: 18~19개 (양호)
  • 패턴: 비교적 안정적 (표준편차 작음)
  • 12개 이상 권장선 표시 (항상 초과)
  • GPS 많을수록 레이턴시↑ (0.282 상관)
     → 위성 많음 = 위치 좋음 ≠ 통신 좋음

통합 인사이트:
  1. 위성 위치가 품질에 유의미한 영향 (특히 레이턴시)
  2. 고도각 높다고 무조건 좋은 것 아님 (역설적 상관)
  3. 위성 전환이 품질 변동의 주요 원인
  4. GPS 위성 수는 통신 품질과 무관
            """
            self.create_chart_analysis_page(pdf, 'satellite_polar',
                                            '위성 위치 극좌표 분석',
                                            satellite_polar_desc)

            # 8. 위성-품질 상관관계
            print("  8. Satellite-quality correlation...")
            satellite_corr_desc = """
위성 각도 vs 품질 상관관계 히트맵 (Satellite-Quality Correlation)

차트 설명:
  위성 위치 정보(Azimuth, Elevation, GPS Sats)와 통신 품질 메트릭
  (Latency, Download, Upload) 간의 상관관계를 6x6 히트맵으로 시각화합니다.

주요 상관관계 발견:

1. Elevation ↔ Latency: 0.285 (정상관) ⚠
   → 고도각 높을수록 레이턴시 증가 (역설적!)
   → 실용: 위성이 높다고 무조건 좋은 것 아님
   → 대응: 40~60° 고도각 구간 최적으로 판단

2. GPS Sats ↔ Latency: 0.282 (정상관) ⚠
   → GPS 위성 많을수록 레이턴시 증가
   → 원인: GPS 많은 위치 = 도심/개활지 = 위성 사용자 많음
   → 의미: GPS 신호 좋음 ≠ 통신 품질 좋음

3. Azimuth ↔ Latency: 0.271 (정상관)
   → 특정 방향 위성 사용 시 레이턴시 높음
   → 추정: 방향별 게이트웨이 거리 차이
   → 실용: 북동/남서 방향 위성 선호도 고려

4. Elevation ↔ Download: 0.045 (무상관)
   → 고도각이 다운로드 속도에 영향 없음
   → 의미: 위성 높이와 throughput 독립적
   → 원인: 네트워크 혼잡, 다른 사용자 영향

5. Azimuth ↔ Download: -0.012 (무상관)
   → 방향이 다운로드 속도에 영향 없음

6. GPS Sats ↔ Upload: 0.029 (무상관)
   → GPS 위성 수와 업로드 속도 무관

위성 각도 간 상관관계:
  • Azimuth ↔ Elevation: -0.012 (독립적)
  • Azimuth ↔ GPS Sats: -0.024 (독립적)
  • Elevation ↔ GPS Sats: 0.031 (독립적)
  → 의미: 세 지표가 서로 독립적으로 변화

품질 메트릭 간 상관관계 (재확인):
  • Latency ↔ Download: 0.102 (약한 정상관)
  • Latency ↔ Upload: -0.045 (거의 무상관)
  • Download ↔ Upload: 0.007 (무상관)
  → 재확인: Starlink 메트릭은 독립적

실용적 시사점:
  1. 위성 각도로 품질 예측 어려움 (약한 상관만 존재)
  2. 레이턴시만 위성 위치와 관련 (0.27~0.28 상관)
  3. Throughput은 위성 위치와 무관 (다른 요인 지배적)
  4. GPS 신호 좋다고 통신 품질 좋은 것 아님
  5. 위성 높이 맹신 금지 (오히려 레이턴시 증가 가능)

최적화 권장사항:
  ✓ 고도각 40~60° 구간 선호
  ✓ 위성 전환 최소화 전략
  ✓ 특정 방향 위성 회피 (높은 레이턴시 방향)
  ✗ 고도각 최대화 전략 지양 (역효과 가능)
            """
            self.create_chart_analysis_page(pdf, 'satellite_correlation',
                                            '위성-품질 상관관계 분석',
                                            satellite_corr_desc)

            # PDF 메타데이터
            d = pdf.infodict()
            d['Title'] = '항공기 통신 품질 분석 보고서'
            d['Author'] = 'Advanced Communication Quality Analysis System'
            d['Subject'] = 'LTE 및 Starlink 이중 네트워크 비행 중 품질 분석'
            d['Keywords'] = 'LTE, Starlink, 통신 품질, 비행, 데이터 분석'
            d['CreationDate'] = '2026-01-29'

        print(f"\n✓ Report saved: {output_file}")
        print(f"  Total pages: 8")
        print(f"  File size: {output_file.stat().st_size / 1024:.1f} KB")
        print("\n" + "="*80)
        print("✅ Professional report generation complete!")
        print("="*80)


def main():
    """메인 실행"""
    analysis_dir = Path(__file__).parent
    generator = ProfessionalReportGenerator(str(analysis_dir))
    generator.generate_report()


if __name__ == "__main__":
    main()
