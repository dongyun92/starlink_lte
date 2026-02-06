"""
분석 결과 API
"""
from flask import Blueprint, jsonify, send_file
from pathlib import Path
import config
from models import Session, AnalysisResult

results_bp = Blueprint('results', __name__)

@results_bp.route('/api/session/<session_id>/results', methods=['GET'])
def get_results(session_id: str):
    """
    분석 결과 조회

    Response:
        {
            "session_id": "uuid",
            "metadata": {...},
            "key_findings": [...],
            "statistics": {...},
            "charts": [...],
            "downloads": {...}
        }
    """
    session = Session.get_by_id(session_id)
    if not session:
        return jsonify({'error': '세션을 찾을 수 없습니다'}), 404

    if session.status != 'completed':
        return jsonify({'error': '분석이 아직 완료되지 않았습니다'}), 400

    # 분석 결과 조회
    result = AnalysisResult.get_by_session_id(session_id)

    # analysis_results.json 파일에서 직접 읽기
    analysis_results = {}
    results_json_path = config.RESULTS_FOLDER / session_id / 'analysis_results.json'
    if results_json_path.exists():
        import json
        import math
        with open(results_json_path, 'r', encoding='utf-8') as f:
            full_results = json.load(f)
            analysis_results = full_results.get('analysis_results', {})

            # NaN 값을 null로 변환하는 재귀 함수
            def replace_nan(obj):
                if isinstance(obj, dict):
                    return {k: replace_nan(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [replace_nan(item) for item in obj]
                elif isinstance(obj, float) and math.isnan(obj):
                    return None
                else:
                    return obj

            analysis_results = replace_nan(analysis_results)

    # 차트 파일 목록
    charts_dir = config.RESULTS_FOLDER / session_id / 'charts'
    charts = []

    if charts_dir.exists():
        chart_files = {
            # 기본 차트
            'statistics_summary': '📊 통계 요약',
            'quality_over_time': '📈 시간대별 통신 품질',
            'comprehensive_correlations': '🔬 종합 상관관계 분석 (28개 변수)',
            'correlation_matrix': '🔗 상관관계 매트릭스',
            'correlation_heatmap': '🗺️ 상관관계 히트맵',
            'altitude_quality': '✈️ 고도별 통신 품질',
            'quality_distribution': '📦 품질 등급 분포',
            # Starlink 위성 분석 차트
            'satellite_position_polar': '🛰️ Starlink 위성 위치 추적 (극좌표)',
            'satellite_quality_correlation': '📡 위성 각도-품질 상관관계',
            # Starlink 심층 분석 (비행 데이터 연동)
            'starlink_altitude_analysis': '🛰️ Starlink 품질 vs 고도 (4개 지표)',
            'starlink_speed_analysis': '🚁 Starlink 품질 vs 이동 속도',
            'starlink_distance_analysis': '📍 Starlink 품질 vs 원점 거리',
            'starlink_throughput_timeseries': '⏱️ Starlink 처리량 시계열',
            'starlink_3d_altitude_speed': '🎲 3D: 고도-속도-Starlink 지연',
            # 고급 차트
            'chart1_speed_vs_lte': '🚀 이동 속도 vs LTE 품질',
            'chart2_distance_vs_lte': '📍 원점 거리 vs LTE 품질',
            'chart3_time_vs_starlink': '⏱️ 비행 시간 vs Starlink 지연',
            'chart4_3d_multidimensional': '🎲 3D 복합 분석',
            'chart5_flight_path_quality_map': '🗺️ 비행 경로 품질 맵',
            'chart6_timeseries_multiaxis': '📉 시계열 4축 복합 분석'
        }

        for chart_name, chart_title in chart_files.items():
            chart_path = charts_dir / f'{chart_name}.png'
            if chart_path.exists():
                charts.append({
                    'name': chart_name,
                    'title': chart_title,
                    'url': f'/api/session/{session_id}/chart/{chart_name}.png'
                })

    return jsonify({
        'session_id': session.id,
        'metadata': session.metadata,
        'key_findings': result.key_findings if result else [],
        'statistics': result.statistics if result else {},
        'analysis_results': analysis_results,
        'charts': charts,
        'downloads': {
            'report': f'/api/session/{session_id}/download/report',
            'charts_zip': f'/api/session/{session_id}/download/charts',
            'map_data': f'/api/session/{session_id}/map-data'
        }
    })

@results_bp.route('/api/session/<session_id>/download/report', methods=['GET'])
def download_report(session_id: str):
    """Word 보고서 다운로드"""
    session = Session.get_by_id(session_id)
    if not session:
        return jsonify({'error': '세션을 찾을 수 없습니다'}), 404

    report_path = config.RESULTS_FOLDER / session_id / 'analysis_report.docx'

    if not report_path.exists():
        return jsonify({'error': '보고서 파일을 찾을 수 없습니다'}), 404

    return send_file(
        report_path,
        as_attachment=True,
        download_name=f'flight_analysis_report_{session_id[:8]}.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@results_bp.route('/api/session/<session_id>/download/charts', methods=['GET'])
def download_charts(session_id: str):
    """차트 ZIP 다운로드"""
    import zipfile
    import io

    session = Session.get_by_id(session_id)
    if not session:
        return jsonify({'error': '세션을 찾을 수 없습니다'}), 404

    charts_dir = config.RESULTS_FOLDER / session_id / 'charts'

    if not charts_dir.exists():
        return jsonify({'error': '차트 파일을 찾을 수 없습니다'}), 404

    # 메모리에 ZIP 생성
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for chart_file in charts_dir.glob('*.png'):
            zf.write(chart_file, arcname=chart_file.name)

    memory_file.seek(0)

    return send_file(
        memory_file,
        as_attachment=True,
        download_name=f'charts_{session_id[:8]}.zip',
        mimetype='application/zip'
    )

@results_bp.route('/api/session/<session_id>/chart/<chart_name>', methods=['GET'])
def get_chart(session_id: str, chart_name: str):
    """개별 차트 이미지 조회"""
    session = Session.get_by_id(session_id)
    if not session:
        return jsonify({'error': '세션을 찾을 수 없습니다'}), 404

    chart_path = config.RESULTS_FOLDER / session_id / 'charts' / chart_name

    if not chart_path.exists():
        return jsonify({'error': '차트 파일을 찾을 수 없습니다'}), 404

    return send_file(chart_path, mimetype='image/png')

@results_bp.route('/api/session/<session_id>/map-data', methods=['GET'])
def get_map_data(session_id: str):
    """지도 데이터 (GeoJSON) 조회"""
    session = Session.get_by_id(session_id)
    if not session:
        return jsonify({'error': '세션을 찾을 수 없습니다'}), 404

    geojson_path = config.RESULTS_FOLDER / session_id / 'map_data.geojson'

    if not geojson_path.exists():
        return jsonify({'error': '지도 데이터를 찾을 수 없습니다'}), 404

    import json
    with open(geojson_path, 'r') as f:
        geojson_data = json.load(f)

    return jsonify(geojson_data)
