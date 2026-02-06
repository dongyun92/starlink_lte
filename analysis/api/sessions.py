"""
세션 관리 API
"""
from flask import Blueprint, jsonify
from models import Session

sessions_bp = Blueprint('sessions', __name__)

@sessions_bp.route('/api/sessions', methods=['GET'])
def get_sessions():
    """
    모든 세션 목록 조회

    Response:
        {
            "sessions": [
                {
                    "id": "uuid",
                    "name": "Flight Analysis",
                    "created_at": "2026-01-29T14:30:00",
                    "status": "completed",
                    "metadata": {...}
                },
                ...
            ]
        }
    """
    sessions = Session.get_all()
    return jsonify({
        'sessions': [s.to_dict() for s in sessions]
    })

@sessions_bp.route('/api/session/<session_id>/status', methods=['GET'])
def get_session_status(session_id: str):
    """
    세션 상태 조회

    Response:
        {
            "session_id": "uuid",
            "status": "processing",
            "progress": 45,
            "current_step": "상관관계 분석 중",
            "steps_completed": [...],
            "steps_remaining": [...]
        }
    """
    session = Session.get_by_id(session_id)

    if not session:
        return jsonify({'error': '세션을 찾을 수 없습니다'}), 404

    # 단계 정의
    all_steps = [
        '파일 파싱',
        'UTC 동기화',
        '파생 변수 생성',
        '상관관계 분석',
        '차트 생성',
        '지도 데이터 생성',
        'Word 보고서 생성'
    ]

    # 진행 상황에 따라 완료/남은 단계 계산
    progress = session.progress
    num_steps = len(all_steps)
    completed_count = int((progress / 100) * num_steps)

    steps_completed = all_steps[:completed_count]
    steps_remaining = all_steps[completed_count:]

    return jsonify({
        'session_id': session.id,
        'status': session.status,
        'progress': session.progress,
        'current_step': session.current_step or '대기 중',
        'steps_completed': steps_completed,
        'steps_remaining': steps_remaining,
        'estimated_time_remaining': max(0, int((100 - progress) * 6))  # 대략 600초 / 100
    })

@sessions_bp.route('/api/session/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """세션 삭제"""
    session = Session.get_by_id(session_id)

    if not session:
        return jsonify({'error': '세션을 찾을 수 없습니다'}), 404

    # 파일 삭제
    import shutil
    from pathlib import Path
    import config

    session_upload_dir = config.UPLOAD_FOLDER / session_id
    session_results_dir = config.RESULTS_FOLDER / session_id

    if session_upload_dir.exists():
        shutil.rmtree(session_upload_dir)
    if session_results_dir.exists():
        shutil.rmtree(session_results_dir)

    # DB에서 삭제
    session.delete()

    return jsonify({'message': '세션이 삭제되었습니다'}), 200
