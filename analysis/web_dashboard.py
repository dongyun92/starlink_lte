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
                        • 비행 시나리오 및 이벤트 분석<br>
                        • 상관관계 분석 (차트 + 상세 해석)<br>
                        • 품질 분포 분석 (차트 + 통계)<br>
                        • 시계열 비교 (6개 메트릭)<br>
                        • 위성 추적 분석 (극좌표 플롯 + 해석)<br>
                        • 위성-품질 상관관계 (역설적 발견 포함)
                    </div>
                    <a href="/download/professional_analysis_report.pdf" class="btn btn-full" style="margin-top: 15px; background: white; color: #667eea;">
                        PDF 보고서 다운로드 (384 KB)
                    </a>
                </div>

                <div class="viz-card">
                    <div class="viz-title">보고서 하이라이트</div>
                    <div class="viz-description">
                        <strong>주요 특징:</strong><br>
                        ✓ 8 페이지 전문 보고서<br>
                        ✓ 5개 차트 + 상세 설명<br>
                        ✓ 비행 시나리오 단계별 분석<br>
                        ✓ 주요 이벤트 타임라인<br>
                        ✓ 역설적 발견 해석 (위성 고도각 vs 레이턴시)<br>
                        ✓ 실용적 권장사항<br>
                        ✓ 네트워크 전환 전략<br>
                        ✓ A4 크기, 인쇄 최적화
                    </div>
                </div>
            </div>
        </div>

        <!-- 분석 도구 -->
        <div class="section">
            <h2 class="section-title">분석 도구 실행</h2>
            <p class="section-subtitle">Python 분석 스크립트</p>

            <div class="grid-3col">
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

                <div class="viz-card">
                    <div class="viz-title">전문 보고서 생성</div>
                    <div class="viz-description">
                        <code>python professional_report_generator.py</code><br>
                        8페이지 PDF 보고서, 차트 + 설명 + 시나리오
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
