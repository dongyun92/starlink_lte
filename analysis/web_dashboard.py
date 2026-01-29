#!/usr/bin/env python3
"""
통신 품질 분석 웹 대시보드
- Flask 기반 웹 인터페이스
- 히트맵 및 보고서 통합 뷰어
- 실시간 분석 결과 확인
"""

from flask import Flask, render_template_string, send_from_directory, jsonify
from pathlib import Path
import pandas as pd
import os


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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }

        h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            font-size: 1.1em;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-5px);
        }

        .stat-label {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }

        .content-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .content-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .content-card h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.5em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }

        .content-card p {
            color: #666;
            line-height: 1.6;
            margin-bottom: 15px;
        }

        .btn {
            display: inline-block;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s ease;
            margin: 5px;
            font-weight: 500;
        }

        .btn:hover {
            background: #764ba2;
        }

        .btn-secondary {
            background: #4CAF50;
        }

        .btn-secondary:hover {
            background: #45a049;
        }

        .btn-danger {
            background: #f44336;
        }

        .btn-danger:hover {
            background: #da190b;
        }

        .file-list {
            list-style: none;
            margin-top: 15px;
        }

        .file-list li {
            padding: 10px;
            background: #f5f5f5;
            margin-bottom: 5px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .file-icon {
            margin-right: 10px;
            font-size: 1.2em;
        }

        footer {
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 20px;
        }

        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }

        .success-message {
            background: #4CAF50;
            color: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }

        .quality-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 5px;
        }

        .quality-excellent { background: #4CAF50; }
        .quality-good { background: #FFC107; }
        .quality-fair { background: #FF9800; }
        .quality-poor { background: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛰️ 통신 품질 분석 대시보드</h1>
            <p class="subtitle">Flight Data Analysis & Communication Quality Reporting System</p>
        </header>

        <div class="success-message" id="successMessage">
            ✅ 분석이 성공적으로 완료되었습니다!
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">📍 총 데이터 포인트</div>
                <div class="stat-value" id="totalPoints">{{ stats.total_points }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">⏱️ 비행 시간</div>
                <div class="stat-value">{{ stats.duration }}초</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">📡 LTE 커버리지</div>
                <div class="stat-value">
                    <span class="quality-indicator quality-{{ 'excellent' if stats.lte_coverage > 95 else 'good' if stats.lte_coverage > 80 else 'fair' }}"></span>
                    {{ stats.lte_coverage }}%
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🛰️ Starlink 커버리지</div>
                <div class="stat-value">
                    <span class="quality-indicator quality-{{ 'excellent' if stats.starlink_coverage > 95 else 'good' if stats.starlink_coverage > 50 else 'fair' }}"></span>
                    {{ stats.starlink_coverage }}%
                </div>
            </div>
        </div>

        <div class="content-grid">
            <div class="content-card">
                <h2>📊 인터랙티브 히트맵</h2>
                <p>GPS 좌표에 매핑된 통신 품질 데이터를 인터랙티브 지도로 확인하세요.</p>
                <a href="/maps/lte_quality_heatmap.html" target="_blank" class="btn">
                    📡 LTE 품질 히트맵
                </a>
                <a href="/maps/starlink_quality_heatmap.html" target="_blank" class="btn btn-secondary">
                    🛰️ Starlink 품질 히트맵
                </a>
                <a href="/maps/combined_quality_map.html" target="_blank" class="btn">
                    🗺️ 통합 지도 보기
                </a>
            </div>

            <div class="content-card">
                <h2>📄 품질 보고서</h2>
                <p>전문적인 PDF 보고서로 상세한 통계 분석과 차트를 확인하세요.</p>
                <a href="/download/communication_quality_report.pdf" class="btn">
                    📥 PDF 보고서 다운로드
                </a>
                <div style="margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px;">
                    <small>
                        <strong>포함 내용:</strong><br>
                        • LTE/Starlink 품질 통계<br>
                        • 시계열 분석 차트<br>
                        • 품질 등급 분포<br>
                        • 종합 권장사항
                    </small>
                </div>
            </div>
        </div>

        <div class="content-card">
            <h2>📁 생성된 파일 목록</h2>
            <ul class="file-list">
                <li>
                    <span><span class="file-icon">📊</span>merged_flight_data.csv</span>
                    <a href="/download/merged_flight_data.csv" class="btn" style="padding: 5px 15px; font-size: 0.9em;">다운로드</a>
                </li>
                <li>
                    <span><span class="file-icon">🗺️</span>lte_quality_heatmap.html</span>
                    <a href="/maps/lte_quality_heatmap.html" target="_blank" class="btn" style="padding: 5px 15px; font-size: 0.9em;">보기</a>
                </li>
                <li>
                    <span><span class="file-icon">🛰️</span>starlink_quality_heatmap.html</span>
                    <a href="/maps/starlink_quality_heatmap.html" target="_blank" class="btn" style="padding: 5px 15px; font-size: 0.9em;">보기</a>
                </li>
                <li>
                    <span><span class="file-icon">🌍</span>combined_quality_map.html</span>
                    <a href="/maps/combined_quality_map.html" target="_blank" class="btn" style="padding: 5px 15px; font-size: 0.9em;">보기</a>
                </li>
                <li>
                    <span><span class="file-icon">📄</span>communication_quality_report.pdf</span>
                    <a href="/download/communication_quality_report.pdf" class="btn" style="padding: 5px 15px; font-size: 0.9em;">다운로드</a>
                </li>
            </ul>
        </div>

        <div class="content-card">
            <h2>🔄 새로운 분석 실행</h2>
            <p>다른 비행 로그 파일로 분석을 실행하려면 아래 명령어를 사용하세요.</p>
            <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto;">
# 분석 실행
python analysis/flight_data_analyzer.py

# 히트맵 생성
python analysis/quality_heatmap.py

# 보고서 생성
python analysis/quality_report_generator.py

# 웹 대시보드 시작
python analysis/web_dashboard.py
            </pre>
        </div>

        <footer>
            <p>© 2026 Flight Data Analysis System | Powered by Python, Folium, Matplotlib</p>
        </footer>
    </div>

    <script>
        // 페이지 로드 시 성공 메시지 표시
        window.addEventListener('load', function() {
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('success') === 'true') {
                document.getElementById('successMessage').style.display = 'block';
                setTimeout(() => {
                    document.getElementById('successMessage').style.display = 'none';
                }, 5000);
            }
        });
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """메인 대시보드"""
    # 병합된 데이터 로드
    merged_data_path = ANALYSIS_DIR / "merged_flight_data.csv"

    if not merged_data_path.exists():
        return """
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>⚠️ 데이터가 아직 생성되지 않았습니다</h1>
            <p>먼저 분석을 실행해주세요:</p>
            <pre>python analysis/flight_data_analyzer.py</pre>
        </body>
        </html>
        """

    df = pd.read_csv(merged_data_path)

    # 통계 계산
    stats = {
        'total_points': len(df),
        'duration': int(df['timestamp'].max() - df['timestamp'].min()),
        'lte_coverage': round(df['lte_available'].sum() / len(df) * 100, 1),
        'starlink_coverage': round(df['starlink_available'].sum() / len(df) * 100, 1),
    }

    return render_template_string(DASHBOARD_HTML, stats=stats)


@app.route('/maps/<path:filename>')
def serve_maps(filename):
    """히트맵 HTML 파일 제공"""
    return send_from_directory(ANALYSIS_DIR, filename)


@app.route('/download/<path:filename>')
def download_file(filename):
    """파일 다운로드"""
    return send_from_directory(ANALYSIS_DIR, filename, as_attachment=True)


@app.route('/api/stats')
def get_stats():
    """API: 통계 데이터"""
    merged_data_path = ANALYSIS_DIR / "merged_flight_data.csv"

    if not merged_data_path.exists():
        return jsonify({'error': 'Data not found'}), 404

    df = pd.read_csv(merged_data_path)
    lte_data = df[df['lte_available'] == True]
    sl_data = df[df['starlink_available'] == True]

    return jsonify({
        'total_points': len(df),
        'duration': int(df['timestamp'].max() - df['timestamp'].min()),
        'lte': {
            'coverage': round(len(lte_data) / len(df) * 100, 1),
            'rssi_mean': round(lte_data['lte_rssi'].mean(), 1) if len(lte_data) > 0 else 0,
            'rsrp_mean': round(lte_data['lte_rsrp'].mean(), 1) if len(lte_data) > 0 else 0,
            'sinr_mean': round(lte_data['lte_sinr'].mean(), 1) if len(lte_data) > 0 else 0,
        },
        'starlink': {
            'coverage': round(len(sl_data) / len(df) * 100, 1),
            'latency_mean': round(sl_data['starlink_latency'].mean(), 1) if len(sl_data) > 0 else 0,
            'download_mean': round(sl_data['starlink_download'].mean(), 1) if len(sl_data) > 0 else 0,
            'upload_mean': round(sl_data['starlink_upload'].mean(), 1) if len(sl_data) > 0 else 0,
        }
    })


def main():
    """웹 서버 시작"""
    print("=" * 60)
    print("COMMUNICATION QUALITY ANALYSIS DASHBOARD")
    print("=" * 60)
    print("\n🌐 Starting web server...")
    print(f"📊 Analysis directory: {ANALYSIS_DIR}")
    print(f"📁 Resource directory: {RESOURCE_DIR}")
    print("\n✅ Server ready!")
    print("🔗 Open your browser and go to: http://localhost:5001")
    print("\nPress Ctrl+C to stop the server\n")

    app.run(host='0.0.0.0', port=5001, debug=False)


if __name__ == "__main__":
    main()
