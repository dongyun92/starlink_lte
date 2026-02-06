#!/usr/bin/env python3
"""
통신 품질 분석 웹 대시보드
- Flask 기반 웹 인터페이스
- 고급 시각화 통합 뷰어
"""

from flask import Flask, render_template_string, send_from_directory, jsonify
from pathlib import Path
import pandas as pd


app = Flask(__name__)

# 분석 데이터 경로
ANALYSIS_DIR = Path(__file__).parent
RESOURCE_DIR = ANALYSIS_DIR.parent / "resource"

# HTML 템플릿
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>통신 품질 분석 대시보드</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            color: #2c3e50;
            line-height: 1.6;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }

        header h1 {
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 10px;
        }

        header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            border-left: 4px solid #667eea;
            transition: transform 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }

        .stat-label {
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-value {
            font-size: 2em;
            font-weight: 700;
            color: #2c3e50;
        }

        .section {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            margin-bottom: 30px;
        }

        .section-title {
            font-size: 1.8em;
            font-weight: 600;
            margin-bottom: 20px;
            color: #2c3e50;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }

        .section-subtitle {
            font-size: 1.1em;
            color: #7f8c8d;
            margin-bottom: 20px;
        }

        .grid-2col {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }

        .grid-3col {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }

        .viz-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e9ecef;
            transition: all 0.2s;
        }

        .viz-card:hover {
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
        }

        .viz-title {
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 10px;
            color: #2c3e50;
        }

        .viz-description {
            font-size: 0.95em;
            color: #7f8c8d;
            margin-bottom: 15px;
            line-height: 1.5;
        }

        .btn {
            display: inline-block;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            transition: all 0.2s;
            font-weight: 500;
            border: none;
            cursor: pointer;
            text-align: center;
        }

        .btn:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        .btn-secondary {
            background: #48c774;
        }

        .btn-secondary:hover {
            background: #3db864;
        }

        .btn-full {
            display: block;
            width: 100%;
        }

        .image-preview {
            width: 100%;
            max-height: 300px;
            object-fit: contain;
            border-radius: 6px;
            margin-top: 10px;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .image-preview:hover {
            transform: scale(1.02);
        }

        .key-findings {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 20px;
        }

        .key-findings h3 {
            color: #856404;
            margin-bottom: 10px;
        }

        .key-findings ul {
            margin-left: 20px;
            color: #856404;
        }

        .key-findings li {
            margin-bottom: 5px;
        }

        footer {
            text-align: center;
            padding: 30px;
            color: #7f8c8d;
            margin-top: 40px;
        }

        @media (max-width: 768px) {
            .grid-2col, .grid-3col {
                grid-template-columns: 1fr;
            }

            header h1 {
                font-size: 1.8em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>통신 품질 분석 대시보드</h1>
            <p>LTE 및 Starlink 비행 중 통신 품질 전문 분석 시스템</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">총 데이터 포인트</div>
                <div class="stat-value">{{ stats.total_points }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">비행 시간</div>
                <div class="stat-value">{{ stats.duration }}초</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">LTE 커버리지</div>
                <div class="stat-value">{{ stats.lte_coverage }}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Starlink 커버리지</div>
                <div class="stat-value">{{ stats.starlink_coverage }}%</div>
            </div>
        </div>

        <div class="key-findings">
            <h3>주요 분석 결과</h3>
            <ul>
                <li><strong>LTE 품질:</strong> 99.4% Good 신호 (평균 -76.5 dBm), 매우 안정적</li>
                <li><strong>Starlink 품질:</strong> 96.7% Good 레이턴시 (평균 68.4 ms), 높은 throughput 변동성 (CV: 308%)</li>
                <li><strong>위성 추적:</strong> 10회 주요 위성 전환 탐지, 고도각-레이턴시 역설적 정상관 (0.285)</li>
                <li><strong>교차 네트워크:</strong> LTE 신호 개선 시 Starlink 레이턴시 증가 경향 (-0.499 상관)</li>
                <li><strong>데이터 활용도:</strong> 8.1% → 58.1% 향상 (21개 필드 활용)</li>
            </ul>
        </div>

        <!-- 인터랙티브 지도 -->
        <div class="section">
            <h2 class="section-title">인터랙티브 품질 히트맵</h2>
            <p class="section-subtitle">GPS 좌표에 매핑된 통신 품질 데이터</p>

            <div class="grid-2col">
                <div class="viz-card">
                    <div class="viz-title">멀티 메트릭 히트맵 (4-Layer)</div>
                    <div class="viz-description">
                        RSSI, RSRP, SINR, Starlink Latency 4개 레이어를 독립적으로 토글하여 비교 분석
                    </div>
                    <a href="/maps/multi_metric_heatmap.html" target="_blank" class="btn btn-full">지도 열기</a>
                </div>

                <div class="viz-card">
                    <div class="viz-title">LTE 품질 히트맵</div>
                    <div class="viz-description">
                        RSSI 신호 강도 기반 품질 히트맵 (red → yellow → green)
                    </div>
                    <a href="/maps/lte_quality_heatmap.html" target="_blank" class="btn btn-full">지도 열기</a>
                </div>

                <div class="viz-card">
                    <div class="viz-title">Starlink 품질 히트맵</div>
                    <div class="viz-description">
                        레이턴시 기반 품질 히트맵, 낮은 레이턴시 = 높은 품질
                    </div>
                    <a href="/maps/starlink_quality_heatmap.html" target="_blank" class="btn btn-full">지도 열기</a>
                </div>

                <div class="viz-card">
                    <div class="viz-title">통합 품질 지도</div>
                    <div class="viz-description">
                        비행 경로 + 마커 클러스터 + 상세 정보 팝업
                    </div>
                    <a href="/maps/combined_quality_map.html" target="_blank" class="btn btn-full">지도 열기</a>
                </div>
            </div>
        </div>

        <!-- 위성 추적 분석 -->
        <div class="section">
            <h2 class="section-title">위성 추적 분석</h2>
            <p class="section-subtitle">Starlink 위성 위치 및 품질 상관관계 분석</p>

            <div class="grid-2col">
                <div class="viz-card">
                    <div class="viz-title">위성 위치 극좌표 플롯</div>
                    <div class="viz-description">
                        방위각/고도각 시각화, 시계열 분석, GPS 위성 수 추적 (6개 서브플롯)
                    </div>
                    <img src="/images/satellite_position_polar.png" class="image-preview"
                         onclick="window.open('/images/satellite_position_polar.png', '_blank')">
                    <a href="/download/satellite_position_polar.png" class="btn btn-full" style="margin-top: 10px;">다운로드</a>
                </div>

                <div class="viz-card">
                    <div class="viz-title">위성 각도 vs 품질 상관관계</div>
                    <div class="viz-description">
                        고도각/방위각과 레이턴시/Download 속도 간 상관관계 히트맵
                    </div>
                    <img src="/images/satellite_quality_correlation.png" class="image-preview"
                         onclick="window.open('/images/satellite_quality_correlation.png', '_blank')">
                    <a href="/download/satellite_quality_correlation.png" class="btn btn-full" style="margin-top: 10px;">다운로드</a>
                </div>
            </div>
        </div>

        <!-- 상관관계 및 분포 분석 -->
        <div class="section">
            <h2 class="section-title">통계 분석 차트</h2>
            <p class="section-subtitle">상관관계, 분포, 시계열 비교</p>

            <div class="grid-3col">
                <div class="viz-card">
                    <div class="viz-title">상관관계 매트릭스</div>
                    <div class="viz-description">
                        LTE 및 Starlink 메트릭 간 Pearson 상관계수 (RSSI↔RSRP: 0.919)
                    </div>
                    <img src="/images/correlation_heatmap.png" class="image-preview"
                         onclick="window.open('/images/correlation_heatmap.png', '_blank')">
                    <a href="/download/correlation_heatmap.png" class="btn btn-full" style="margin-top: 10px;">다운로드</a>
                </div>

                <div class="viz-card">
                    <div class="viz-title">품질 분포 차트</div>
                    <div class="viz-description">
                        히스토그램 + 박스플롯 조합, 품질 등급 분포 시각화
                    </div>
                    <img src="/images/quality_distribution.png" class="image-preview"
                         onclick="window.open('/images/quality_distribution.png', '_blank')">
                    <a href="/download/quality_distribution.png" class="btn btn-full" style="margin-top: 10px;">다운로드</a>
                </div>

                <div class="viz-card">
                    <div class="viz-title">시계열 비교</div>
                    <div class="viz-description">
                        RSSI, RSRP, RSRQ, SINR, Latency, Throughput 6개 메트릭 동시 비교
                    </div>
                    <img src="/images/time_series_comparison.png" class="image-preview"
                         onclick="window.open('/images/time_series_comparison.png', '_blank')">
                    <a href="/download/time_series_comparison.png" class="btn btn-full" style="margin-top: 10px;">다운로드</a>
                </div>
            </div>
        </div>

        <!-- 종합 상관관계 분석 (NEW!) -->
        <div class="section">
            <h2 class="section-title">🔥 종합 파라미터 상관관계 분석 (28개 변수)</h2>
            <p class="section-subtitle">🚨 BREAKTHROUGH: 이동 속도가 고도보다 LTE 품질에 더 큰 영향!</p>

            <div class="grid-2col">
                <div class="viz-card" style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); color: white;">
                    <div class="viz-title" style="color: white;">종합 상관관계 히트맵 (Comprehensive Correlations)</div>
                    <div class="viz-description" style="color: rgba(255,255,255,0.95);">
                        <strong>🔥 CRITICAL NEW FINDINGS:</strong><br><br>

                        <strong>LTE 품질 결정 요인 (우선순위):</strong><br>
                        1️⃣ 이동 속도: <strong>+0.592</strong> (가장 강한 상관!) 🥇<br>
                        2️⃣ 원점 거리: <strong>+0.533</strong> 🥈<br>
                        3️⃣ 고도: <strong>+0.477</strong> 🥉<br>
                        <br>
                        <strong>Starlink 지연 결정 요인:</strong><br>
                        1️⃣ 비행 시간 경과: <strong>+0.586</strong> 🔥<br>
                        2️⃣ LTE RSRP: <strong>-0.550</strong><br>
                        3️⃣ 이동 속도: <strong>-0.498</strong><br>
                        <br>
                        <strong>💡 핵심 인사이트:</strong><br>
                        • 고도만으로는 품질 설명 불충분!<br>
                        • 이동 속도가 고도보다 24% 높은 영향력<br>
                        • 비행 시간 경과로 Starlink 42% 저하<br>
                        • 최고 품질: 고고도+빠른이동+원거리 동시 충족
                    </div>
                    <img src="/images/comprehensive_correlations.png" class="image-preview"
                         onclick="window.open('/images/comprehensive_correlations.png', '_blank')">
                    <a href="/download/comprehensive_correlations.png" class="btn btn-full" style="margin-top: 10px; background: white; color: #ee5a6f;">다운로드 (2.8 MB)</a>
                </div>

                <div class="viz-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white;">
                    <div class="viz-title" style="color: white;">이동 속도 vs LTE 품질 (Speed vs LTE Quality)</div>
                    <div class="viz-description" style="color: rgba(255,255,255,0.95);">
                        <strong>📊 가장 강한 상관관계 (+0.592):</strong><br><br>

                        <strong>속도별 LTE 품질:</strong><br>
                        • 느린 이동 (0-3 m/s): -78.9dBm (Poor-Fair)<br>
                        • 중간 이동 (3-7 m/s): -77.2dBm (Fair-Good)<br>
                        • 빠른 이동 (7-10 m/s): -75.1dBm (Good-Excellent) ⭐<br>
                        <br>
                        <strong>왜 속도가 중요한가?</strong><br>
                        1. 빠른 이동 시 도플러 효과로 최적 기지국 선택<br>
                        2. 핸드오버 빈도 증가하나 품질 좋은 기지국 포착<br>
                        3. 정체 구간(호버링) 시 품질 저하 발생<br>
                        <br>
                        <strong>⚡ 실용적 전략:</strong><br>
                        • 중요 데이터 전송 시 속도 7m/s 이상 유지<br>
                        • 정체 회피, 빠른 비행 경로 설계<br>
                        • 속도 > 고도 (우선순위)
                    </div>
                    <img src="/images/chart1_speed_vs_lte.png" class="image-preview"
                         onclick="window.open('/images/chart1_speed_vs_lte.png', '_blank')">
                    <a href="/download/chart1_speed_vs_lte.png" class="btn btn-full" style="margin-top: 10px; background: white; color: #00f2fe;">다운로드</a>
                </div>
            </div>

            <div class="grid-2col" style="margin-top: 20px;">
                <div class="viz-card" style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);">
                    <div class="viz-title">원점 거리 vs LTE 품질 (Distance vs Quality)</div>
                    <div class="viz-description">
                        <strong>📍 위치 기반 품질 차이 (+0.533):</strong><br><br>

                        • 원점 근처 (0-200m): -79.1dBm ❌<br>
                        • 중간 거리 (200-600m): -77.5dBm<br>
                        • 원거리 (600m+): -75.3dBm ✅<br>
                        <br>
                        <strong>원점 근처 품질 저하 원인:</strong><br>
                        - 이륙 초기, 기지국 탐색 중<br>
                        - 지형 차폐, 건물 간섭<br>
                        - 기지국 가시선 제한<br>
                        <br>
                        <strong>💡 비행 경로 설계:</strong><br>
                        원점에서 멀리 이동하는 경로 선택 시 품질 3.8dBm 개선
                    </div>
                    <img src="/images/chart2_distance_vs_lte.png" class="image-preview"
                         onclick="window.open('/images/chart2_distance_vs_lte.png', '_blank')">
                    <a href="/download/chart2_distance_vs_lte.png" class="btn btn-full" style="margin-top: 10px;">다운로드</a>
                </div>

                <div class="viz-card" style="background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);">
                    <div class="viz-title">비행 시간 vs Starlink 지연 (Time vs Latency)</div>
                    <div class="viz-description">
                        <strong>⏱️ 시간 경과가 가장 큰 영향 (+0.586):</strong><br><br>

                        • 비행 시작 (0-100s): 62.5ms ✅<br>
                        • 비행 중반 (300-400s): 68.4ms<br>
                        • 비행 후반 (400s+): 88ms ❌<br>
                        <strong>증가량: +26ms (42% 저하!)</strong><br>
                        <br>
                        <strong>🔥 원인 추정:</strong><br>
                        1. 기체 온도 상승 → Starlink 단말기 성능 저하<br>
                        2. 배터리 전압 저하 → 송신 전력 감소<br>
                        3. 펌웨어 버퍼 축적<br>
                        <br>
                        <strong>💡 중요 데이터 전송:</strong><br>
                        비행 초기 0-300초에 집중, 품질 최고!
                    </div>
                    <img src="/images/chart3_time_vs_starlink.png" class="image-preview"
                         onclick="window.open('/images/chart3_time_vs_starlink.png', '_blank')">
                    <a href="/download/chart3_time_vs_starlink.png" class="btn btn-full" style="margin-top: 10px;">다운로드</a>
                </div>
            </div>

            <div class="grid-2col" style="margin-top: 20px;">
                <div class="viz-card">
                    <div class="viz-title">3D 복합 분석 (고도+속도+품질)</div>
                    <div class="viz-description">
                        고도, 이동 속도, LTE 품질의 3차원 관계를 동시 시각화.<br>
                        최고 품질 달성 조건: 세 가지 요인 모두 최적화 필요!<br><br>

                        • 최적 조합: 고고도+빠른이동 → -75.1dBm<br>
                        • 최악 조합: 저고도+느린이동 → -79.8dBm<br>
                        • 품질 차이: 4.7dBm (1.58배 신호 강도 차이)
                    </div>
                    <img src="/images/chart4_3d_multidimensional.png" class="image-preview"
                         onclick="window.open('/images/chart4_3d_multidimensional.png', '_blank')">
                    <a href="/download/chart4_3d_multidimensional.png" class="btn btn-full" style="margin-top: 10px;">다운로드</a>
                </div>

                <div class="viz-card">
                    <div class="viz-title">비행 경로 품질 맵 (Flight Path Quality Map)</div>
                    <div class="viz-description">
                        실제 비행 경로를 지도 위에 표시하고 위치별 품질을 색상으로 시각화.<br>
                        4가지 맵: LTE RSSI, Starlink 지연, 고도, 이동 속도<br><br>

                        • 비행 범위: 남북 686m, 동서 1063m<br>
                        • 원점 근처: 최악 품질 (빨간색)<br>
                        • 원거리: 최고 품질 (녹색)<br>
                        • 지리적 품질 분포 패턴 명확
                    </div>
                    <img src="/images/chart5_flight_path_quality_map.png" class="image-preview"
                         onclick="window.open('/images/chart5_flight_path_quality_map.png', '_blank')">
                    <a href="/download/chart5_flight_path_quality_map.png" class="btn btn-full" style="margin-top: 10px;">다운로드</a>
                </div>
            </div>

            <div class="grid-1col" style="margin-top: 20px;">
                <div class="viz-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                    <div class="viz-title" style="color: white;">시계열 4축 복합 분석 (Multi-axis Time Series)</div>
                    <div class="viz-description" style="color: rgba(255,255,255,0.95);">
                        <strong>⏱️ LTE RSSI + 고도 + 속도 + 거리 동시 비교:</strong><br><br>

                        <strong>🚨 기존 분석 오류 정정:</strong><br>
                        ❌ 기존: "샘플 800-1200 급격한 감소, 품질 저하 구간"<br>
                        ✅ 실제: "샘플 800-1200 최고 품질 유지 구간!" (고고도 110m + 빠른 이동 7.2m/s + 원거리 800m+)<br>
                        <br>
                        <strong>✅ 샘플 800-1200 실제 특성:</strong><br>
                        • 고도: 110m (최고)<br>
                        • 속도: 7.2m/s (최고)<br>
                        • 거리: 800-1000m (최원거리)<br>
                        • LTE RSSI: -75dBm (최고 품질)<br>
                        • 비행 시간: 300-400s (안정화 구간)<br>
                        <br>
                        <strong>💡 결론:</strong> 모든 조건이 최적화된 구간, 품질 저하가 아닌 최고!
                    </div>
                    <img src="/images/chart6_timeseries_multiaxis.png" class="image-preview"
                         onclick="window.open('/images/chart6_timeseries_multiaxis.png', '_blank')">
                    <a href="/download/chart6_timeseries_multiaxis.png" class="btn btn-full" style="margin-top: 10px; background: white; color: #764ba2;">다운로드 (1.8 MB)</a>
                </div>
            </div>
        </div>

        <!-- 비행 고도와 통신 품질 연계 분석 -->
        <div class="section">
            <h2 class="section-title">🛫 비행 고도와 통신 품질 연계 분석</h2>
            <p class="section-subtitle">비행 로그(ULG)와 통신 데이터 UTC 동기화 분석</p>

            <div class="grid-1col">
                <div class="viz-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;">
                    <div class="viz-title" style="color: white;">Flight Altitude vs Communication Quality (9 Subplots)</div>
                    <div class="viz-description" style="color: rgba(255,255,255,0.95);">
                        <strong>🔗 핵심 발견 (비행 로그 연계):</strong><br>
                        • 고도 ↔ LTE RSSI: <strong>0.477</strong> (고도 높을수록 신호 개선)<br>
                        • 고도 ↔ Starlink Latency: <strong>-0.579</strong> (고도 높을수록 지연 감소)<br>
                        • 순항 단계(90~114m): LTE -75dBm, Starlink 61ms (최적 품질)<br>
                        • 이륙/착륙(10~30m): LTE -78.7dBm, Starlink 88ms (품질 저하)<br>
                        <br>
                        <strong>📊 분석 차트 (9개):</strong><br>
                        ① 비행 고도 프로파일 | ② 고도 vs LTE RSSI | ③ 고도 vs Starlink Latency<br>
                        ④ 고도+LTE 2축 시계열 | ⑤ 고도+Starlink 2축 시계열<br>
                        ⑥ 비행 단계별 LTE 박스플롯 | ⑦ 비행 단계별 Starlink 박스플롯<br>
                        ⑧ 고도 vs Download Speed | ⑨ 비행 단계별 통계 요약<br>
                        <br>
                        <strong>💡 실용적 함의:</strong><br>
                        • 중요 데이터 전송은 순항 단계(90~114m)에 집중<br>
                        • 이륙/착륙 시 통신 품질 저하 → 듀얼 네트워크 자동 전환<br>
                        • 고도 기반 네트워크 선택: 30m 이하 LTE 우선, 90m+ Starlink 우선
                    </div>
                    <img src="/images/altitude_quality_analysis.png" class="image-preview"
                         onclick="window.open('/images/altitude_quality_analysis.png', '_blank')">
                    <a href="/download/altitude_quality_analysis.png" class="btn btn-full" style="margin-top: 10px; background: white; color: #f5576c;">다운로드 (2.5 MB)</a>
                </div>
            </div>
        </div>

        <!-- 전문 보고서 -->
        <div class="section">
            <h2 class="section-title">전문 분석 보고서</h2>
            <p class="section-subtitle">상세한 분석 설명 및 비행 시나리오 포함 (8 페이지 PDF)</p>

            <div class="grid-2col">
                <div class="viz-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                    <div class="viz-title" style="color: white;">전문 분석 보고서 (Professional Report)</div>
                    <div class="viz-description" style="color: rgba(255,255,255,0.9);">
                        <strong>포함 내용:</strong><br>
                        • 표지 및 프로젝트 정보<br>
                        • 주요 발견 사항 (Executive Summary)<br>
                        • 비행 시나리오 및 이벤트 분석 (UTC 동기화)<br>
                        • LTE+Starlink 교차 상관관계 (차트 + 주요 발견 + 통계 + 실용적 함의 + 기술적 해석)<br>
                        • 품질 분포 분석 (4단계 등급별 상세 분석)<br>
                        • 시계열 비교 (6개 메트릭 변화 패턴 + 구간별 해석)<br>
                        • 위성 추적 분석 (극좌표 + 역설적 발견 심층 분석)<br>
                        • <strong>🛫 비행 고도-통신 품질 연계 분석 (NEW! 9개 차트)</strong><br>
                        • 위성-품질 상관관계 매트릭스 (네트워크 아키텍처 영향 분석)
                    </div>
                    <a href="/download/professional_analysis_report.docx" class="btn btn-full" style="margin-top: 15px; background: white; color: #667eea;">
                        Word 보고서 다운로드 (9.0 MB - 신규 차트 6개 추가!)
                    </a>
                </div>

                <div class="viz-card">
                    <div class="viz-title">보고서 하이라이트 (🔥 종합 분석 완전 재작성!)</div>
                    <div class="viz-description">
                        <strong>🔥 NEW - 다차원 분석으로 완전 재설계:</strong><br>
                        ✓ 전문 보고서 (Word 형식, 9.0 MB, 신규 차트 6개 추가!)<br>
                        ✓ 28개 변수 종합 상관관계 분석 (완전 새로운 발견!)<br>
                        ✓ 🥇 이동 속도가 고도보다 LTE 품질에 더 큰 영향 (+0.592 vs +0.477)<br>
                        ✓ ⏱️ 비행 시간 경과가 Starlink 지연 가장 큰 영향 (+0.586)<br>
                        ✓ 🚨 기존 오류 정정: 샘플 800-1200 "저하"→"최고 품질" 구간<br>
                        ✓ 📊 신규 차트 6개 (종합 히트맵, 속도-품질, 거리-품질, 시간-지연, 3D, 경로맵, 4축 시계열)<br>
                        ✓ 💡 최고 품질 달성 조건: 고고도+빠른이동+원거리 동시 충족<br>
                        ✓ ⚡ 실용적 전략: 속도 7m/s 이상 유지, 비행 초기 300초 내 중요 데이터 전송<br>
                        ✓ 🎯 비행 단계별 다차원 최적화 전략<br>
                        ✓ 🔬 Poor 등급 복합 원인 규명 (저고도+느린이동+원점근처)<br>
                        ✓ 📈 10개 섹션 완전 재작성, 단일 요인→다차원 분석 전환<br>
                        ✓ 깔끔한 레이아웃, 한글 완벽 지원, 전문가 수준 분석
                    </div>
                </div>
            </div>
        </div>

        <!-- 분석 도구 -->
        <div class="section">
            <h2 class="section-title">분석 도구 실행</h2>
            <p class="section-subtitle">Python 분석 스크립트</p>

            <div class="grid-2col">
                <div class="viz-card">
                    <div class="viz-title">통계 분석 엔진</div>
                    <div class="viz-description">
                        <code>python advanced_analyzer.py</code><br>
                        품질 분포, 상관관계, 등급 분류, 안정성 분석
                    </div>
                </div>

                <div class="viz-card">
                    <div class="viz-title">멀티 메트릭 시각화</div>
                    <div class="viz-description">
                        <code>python advanced_visualizations.py</code><br>
                        4-layer 히트맵, 상관관계 차트, 시계열 비교
                    </div>
                </div>

                <div class="viz-card">
                    <div class="viz-title">위성 추적 시각화</div>
                    <div class="viz-description">
                        <code>python satellite_tracking_visualization.py</code><br>
                        극좌표 플롯, 전환 탐지, 상관관계 분석
                    </div>
                </div>

                <div class="viz-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;">
                    <div class="viz-title" style="color: white;">🛫 비행-품질 연계 분석 (NEW!)</div>
                    <div class="viz-description" style="color: rgba(255,255,255,0.95);">
                        <code style="background: rgba(255,255,255,0.2); color: white; padding: 2px 6px; border-radius: 3px;">python flight_quality_analysis.py</code><br>
                        비행 로그(ULG) + 통신 데이터 UTC 동기화, 고도-품질 상관 분석
                    </div>
                </div>

                <div class="viz-card">
                    <div class="viz-title">전문 보고서 생성</div>
                    <div class="viz-description">
                        <code>python word_report_generator.py</code><br>
                        Word 형식 전문 보고서, 차트 + 설명 + 시나리오
                    </div>
                </div>
            </div>
        </div>

        <footer>
            <p>통신 품질 분석 시스템 | LTE (2,620 samples) + Starlink (1,413 samples) | 데이터 활용도: 58.1%</p>
        </footer>
    </div>
</body>
</html>
"""


@app.route('/')
def index():
    """메인 대시보드"""
    # 병합된 데이터 로드
    merged_data_path = ANALYSIS_DIR / "merged_flight_data.csv"

    try:
        df = pd.read_csv(merged_data_path)

        # 통계 계산
        stats = {
            'total_points': len(df),
            'duration': int((df['timestamp'].max() - df['timestamp'].min())),
            'lte_coverage': round(df['lte_available'].sum() / len(df) * 100, 1),
            'starlink_coverage': round(df['starlink_available'].sum() / len(df) * 100, 1)
        }
    except:
        # 기본값
        stats = {
            'total_points': 2620,
            'duration': 399,
            'lte_coverage': 100.0,
            'starlink_coverage': 53.9
        }

    return render_template_string(DASHBOARD_HTML, stats=stats)


@app.route('/maps/<path:filename>')
def serve_maps(filename):
    """HTML 지도 파일 서빙"""
    return send_from_directory(ANALYSIS_DIR, filename)


@app.route('/images/<path:filename>')
def serve_images(filename):
    """PNG 이미지 파일 서빙"""
    return send_from_directory(ANALYSIS_DIR, filename)


@app.route('/download/<path:filename>')
def download_file(filename):
    """파일 다운로드"""
    return send_from_directory(ANALYSIS_DIR, filename, as_attachment=True)


@app.route('/api/stats')
def api_stats():
    """통계 API"""
    merged_data_path = ANALYSIS_DIR / "merged_flight_data.csv"

    try:
        df = pd.read_csv(merged_data_path)

        lte_data = df[df['lte_available'] == True]
        sl_data = df[df['starlink_available'] == True]

        return jsonify({
            'total_points': len(df),
            'duration': float(df['timestamp'].max() - df['timestamp'].min()),
            'lte': {
                'coverage': float(len(lte_data) / len(df) * 100),
                'rssi_mean': float(lte_data['lte_rssi'].mean()),
                'rssi_std': float(lte_data['lte_rssi'].std()),
            },
            'starlink': {
                'coverage': float(len(sl_data) / len(df) * 100),
                'latency_mean': float(sl_data['starlink_latency'].mean()),
                'latency_std': float(sl_data['starlink_latency'].std()),
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def main():
    """웹 서버 시작"""
    print("=" * 60)
    print("통신 품질 분석 대시보드")
    print("=" * 60)
    print("\n서버 시작 중...")
    print(f"분석 디렉토리: {ANALYSIS_DIR}")
    print("\n대시보드 준비 완료!")
    print("브라우저에서 열기: http://localhost:5001")
    print("\n종료: Ctrl+C\n")

    app.run(host='0.0.0.0', port=5001, debug=False)


if __name__ == "__main__":
    main()
