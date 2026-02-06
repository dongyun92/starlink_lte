"""
파일 업로드 API
"""
from flask import Blueprint, request, jsonify
from pathlib import Path
from werkzeug.utils import secure_filename
import config
from models import Session
import threading
import sys

# 분석 파이프라인 임포트
sys.path.append(str(Path(__file__).parent.parent))
from analysis_pipeline import AnalysisPipeline

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/api/upload', methods=['POST'])
def upload_files():
    """
    파일 업로드 엔드포인트

    Request:
        - flight_log: ULG 파일
        - lte_data: LTE CSV 파일
        - starlink_data: Starlink CSV 파일
        - metadata: JSON (name, date, location 등)

    Response:
        {
            "session_id": "uuid",
            "status": "processing",
            "message": "분석이 시작되었습니다"
        }
    """
    # 여러 파일 받기 (getlist 사용)
    flight_logs = request.files.getlist('flight_log')
    lte_data_files = request.files.getlist('lte_data')
    starlink_data_files = request.files.getlist('starlink_data')

    # 파일 검증 - 비행 로그는 필수, LTE/Starlink는 선택
    if not flight_logs:
        return jsonify({'error': 'flight_log 파일이 필요합니다'}), 400

    # 파일 이름 검증
    for flight_log in flight_logs:
        if not flight_log.filename or not config.allowed_file(flight_log.filename, 'ulg'):
            return jsonify({'error': f'{flight_log.filename}은(는) .ulg 파일이 아닙니다'}), 400

    # LTE 데이터 파일 검증 (있는 경우에만)
    if lte_data_files:
        for lte_data in lte_data_files:
            if not lte_data.filename or not config.allowed_file(lte_data.filename, 'csv'):
                return jsonify({'error': f'{lte_data.filename}은(는) .csv 파일이 아닙니다'}), 400

    # Starlink 데이터 파일 검증 (있는 경우에만)
    if starlink_data_files:
        for starlink_data in starlink_data_files:
            if not starlink_data.filename or not config.allowed_file(starlink_data.filename, 'csv'):
                return jsonify({'error': f'{starlink_data.filename}은(는) .csv 파일이 아닙니다'}), 400

    # 메타데이터 파싱
    metadata = {}
    if 'metadata' in request.form:
        import json
        try:
            metadata = json.loads(request.form['metadata'])
        except:
            metadata = {}

    # 세션 생성
    session = Session(
        name=metadata.get('name', None),
        status='pending',
        metadata=metadata
    )

    # 세션별 디렉토리 생성
    session_dir = config.UPLOAD_FOLDER / session.id
    session_dir.mkdir(exist_ok=True)

    # 서브디렉토리 생성
    (session_dir / 'flight_logs').mkdir(exist_ok=True)
    (session_dir / 'lte_data').mkdir(exist_ok=True)
    (session_dir / 'starlink_data').mkdir(exist_ok=True)

    # 여러 파일 저장
    flight_log_paths = []
    for flight_log in flight_logs:
        filename = secure_filename(flight_log.filename)
        path = session_dir / 'flight_logs' / filename
        flight_log.save(str(path))
        flight_log_paths.append(str(path))

    lte_data_paths = []
    for lte_data in lte_data_files:
        filename = secure_filename(lte_data.filename)
        path = session_dir / 'lte_data' / filename
        lte_data.save(str(path))
        lte_data_paths.append(str(path))

    starlink_data_paths = []
    for starlink_data in starlink_data_files:
        filename = secure_filename(starlink_data.filename)
        path = session_dir / 'starlink_data' / filename
        starlink_data.save(str(path))
        starlink_data_paths.append(str(path))

    # 파일 경로 저장
    session.file_paths = {
        'flight_logs': flight_log_paths,
        'lte_data': lte_data_paths,
        'starlink_data': starlink_data_paths,
        'file_counts': {
            'flight_logs': len(flight_log_paths),
            'lte_data': len(lte_data_paths),
            'starlink_data': len(starlink_data_paths)
        }
    }

    session.save()

    # 분석 파이프라인 백그라운드 실행
    def run_analysis_in_background():
        """백그라운드에서 분석 실행"""
        try:
            # 상태 업데이트: 분석 시작
            session.update_status('processing', progress=10, current_step='분석 시작')

            # 분석 파이프라인 생성
            upload_folder = config.UPLOAD_FOLDER / session.id
            results_folder = config.RESULTS_FOLDER / session.id
            pipeline = AnalysisPipeline(session.id, upload_folder, results_folder)

            # 진행 상황 콜백
            def progress_callback(step, total_steps, message):
                progress = int((step / total_steps) * 90) + 10  # 10-100% 범위
                session.update_status('processing', progress=progress, current_step=message)
                print(f"[Session {session.id}] [{step}/{total_steps}] {message}")

            # 전체 분석 실행
            results = pipeline.run_full_analysis(progress_callback)

            # 결과에 따라 상태 업데이트
            if results['overall_status'] == 'success':
                session.update_status('completed', progress=100, current_step='분석 완료')
                print(f"[Session {session.id}] 분석 완료!")
            else:
                failed_step = results.get('failed_at_step', '?')
                session.update_status('failed', progress=results['steps'][failed_step-1].get('step_number', 0) * 15,
                                    current_step=f'Step {failed_step}에서 실패')
                print(f"[Session {session.id}] 분석 실패: Step {failed_step}")

        except Exception as e:
            print(f"[Session {session.id}] 분석 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            session.update_status('failed', progress=0, current_step=f'오류: {str(e)}')

    # 백그라운드 스레드 시작
    analysis_thread = threading.Thread(target=run_analysis_in_background, daemon=True)
    analysis_thread.start()

    # 업로드 완료 응답
    session.update_status('uploaded', progress=5, current_step='파일 업로드 완료, 분석 대기 중')

    return jsonify({
        'session_id': session.id,
        'status': 'uploaded',
        'created_at': session.created_at,
        'message': '파일 업로드가 완료되었습니다. 분석이 백그라운드에서 진행 중입니다.'
    }), 201


@upload_bp.route('/api/retry/<session_id>', methods=['POST'])
def retry_analysis(session_id):
    """
    실패한 세션 재분석

    Path Parameters:
        session_id: 세션 ID

    Response:
        {
            "session_id": "uuid",
            "status": "processing",
            "message": "재분석이 시작되었습니다"
        }
    """
    # 세션 조회
    session = Session.get_by_id(session_id)
    if not session:
        return jsonify({'error': '세션을 찾을 수 없습니다'}), 404

    # 이미 처리 중인 세션은 재분석 불가
    if session.status == 'processing':
        return jsonify({'error': '이미 분석 중입니다'}), 400

    # 파일 경로 확인
    if not session.file_paths:
        return jsonify({'error': '파일 경로가 없습니다'}), 400

    # 분석 파이프라인 백그라운드 재실행
    def run_analysis_in_background():
        """백그라운드에서 분석 실행"""
        try:
            # 상태 업데이트: 분석 시작
            session.update_status('processing', progress=10, current_step='재분석 시작')

            # 분석 파이프라인 생성
            upload_folder = config.UPLOAD_FOLDER / session.id
            results_folder = config.RESULTS_FOLDER / session.id
            pipeline = AnalysisPipeline(session.id, upload_folder, results_folder)

            # 진행 상황 콜백
            def progress_callback(step, total_steps, message):
                progress = int((step / total_steps) * 90) + 10  # 10-100% 범위
                session.update_status('processing', progress=progress, current_step=message)
                print(f"[Session {session.id}] [{step}/{total_steps}] {message}")

            # 전체 분석 실행
            results = pipeline.run_full_analysis(progress_callback)

            # 결과에 따라 상태 업데이트
            if results['overall_status'] == 'success':
                session.update_status('completed', progress=100, current_step='분석 완료')
                print(f"[Session {session.id}] 재분석 완료!")
            else:
                failed_step = results.get('failed_at_step', '?')
                session.update_status('failed', progress=results['steps'][failed_step-1].get('step_number', 0) * 15,
                                    current_step=f'Step {failed_step}에서 실패')
                print(f"[Session {session.id}] 재분석 실패: Step {failed_step}")

        except Exception as e:
            print(f"[Session {session.id}] 재분석 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            session.update_status('failed', progress=0, current_step=f'오류: {str(e)}')

    # 백그라운드 스레드 시작
    analysis_thread = threading.Thread(target=run_analysis_in_background, daemon=True)
    analysis_thread.start()

    return jsonify({
        'session_id': session.id,
        'status': 'processing',
        'message': '재분석이 시작되었습니다.'
    }), 200
