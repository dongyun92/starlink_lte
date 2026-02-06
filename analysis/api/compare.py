"""
세션 비교 API
"""
from flask import Blueprint, jsonify, request
from pathlib import Path
import json
from models import Session

compare_bp = Blueprint('compare', __name__)

@compare_bp.route('/api/compare', methods=['GET'])
def compare_sessions():
    """
    여러 세션 비교

    Query Parameters:
        sessions: 세션 ID들 (쉼표로 구분)

    Response:
        {
            "sessions": [세션 정보들],
            "comparison": {
                "quality_metrics": {...},
                "file_counts": {...},
                "analysis_times": {...}
            }
        }
    """
    session_ids = request.args.get('sessions', '').split(',')

    if len(session_ids) < 2:
        return jsonify({'error': '최소 2개의 세션이 필요합니다'}), 400

    if len(session_ids) > 5:
        return jsonify({'error': '최대 5개까지 비교할 수 있습니다'}), 400

    # 세션 정보 가져오기
    sessions_data = []
    for session_id in session_ids:
        session = Session.get_by_id(session_id.strip())
        if session:
            sessions_data.append({
                'id': session.id,
                'name': session.name,
                'status': session.status,
                'created_at': session.created_at,
                'progress': session.progress,
                'file_paths': session.file_paths
            })

    if len(sessions_data) < 2:
        return jsonify({'error': '유효한 세션을 찾을 수 없습니다'}), 404

    # 비교 데이터 생성
    comparison = {
        'quality_metrics': {},
        'file_counts': {},
        'analysis_times': {},
        'status_summary': {}
    }

    # 파일 개수 비교
    for session in sessions_data:
        session_name = session['name'] or session['id'][:8]

        if session['file_paths'] and 'file_counts' in session['file_paths']:
            counts = session['file_paths']['file_counts']
            comparison['file_counts'][session_name] = {
                'flight_logs': counts.get('flight_logs', 0),
                'lte_data': counts.get('lte_data', 0),
                'starlink_data': counts.get('starlink_data', 0)
            }

        # 상태 요약
        comparison['status_summary'][session_name] = {
            'status': session['status'],
            'progress': session.get('progress', 0)
        }

        # 분석 결과 JSON 로드 (있는 경우)
        results_path = Path('results') / session['id'] / 'analysis_results.json'
        if results_path.exists():
            with open(results_path, 'r', encoding='utf-8') as f:
                results = json.load(f)

            # 품질 메트릭 추출
            if 'analysis_results' in results and 'quality' in results['analysis_results']:
                quality = results['analysis_results']['quality']
                comparison['quality_metrics'][session_name] = quality

            # 분석 시간
            if 'start_time' in results and 'end_time' in results:
                from datetime import datetime
                start = datetime.fromisoformat(results['start_time'])
                end = datetime.fromisoformat(results['end_time'])
                duration = (end - start).total_seconds()
                comparison['analysis_times'][session_name] = f"{duration:.1f}초"

    return jsonify({
        'sessions': sessions_data,
        'comparison': comparison
    })
