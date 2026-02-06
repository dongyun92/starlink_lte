"""
Flask 앱 설정
"""
import os
from pathlib import Path

# 기본 경로
BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
RESULTS_FOLDER = BASE_DIR / 'results'
DATABASE_PATH = BASE_DIR / 'sessions.db'

# Flask 설정
SECRET_KEY = 'your-secret-key-change-this-in-production'
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB 최대 업로드 크기

# 허용된 파일 확장자
ALLOWED_EXTENSIONS = {'ulg', 'csv'}

# Celery 설정 (추후 사용)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# 분석 설정
ANALYSIS_TIMEOUT = 600  # 10분

# 디렉토리 생성
UPLOAD_FOLDER.mkdir(exist_ok=True)
RESULTS_FOLDER.mkdir(exist_ok=True)

def allowed_file(filename: str, extension: str = None) -> bool:
    """파일 확장자 검증"""
    if '.' not in filename:
        return False

    file_ext = filename.rsplit('.', 1)[1].lower()

    if extension:
        return file_ext == extension.lower()

    return file_ext in ALLOWED_EXTENSIONS
