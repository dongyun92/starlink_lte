"""
비행 통신 품질 분석 플랫폼 - Flask 메인 앱
"""
from flask import Flask, render_template, send_file, Response
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path
import config

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
from models import init_db
from api import upload_bp, sessions_bp, results_bp, compare_bp, convert_csv_bp
from api.threed import api_3d_bp
from api.threed.kpi import kpi_bp
from api.threed.signal_loss import signal_loss_bp
from pathlib import Path

# Flask 앱 생성
app = Flask(__name__)
app.config.from_object(config)

# CORS 설정 (프론트엔드와 별도 포트 사용 시)
CORS(app)

# 블루프린트 등록
app.register_blueprint(upload_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(results_bp)
app.register_blueprint(compare_bp)
app.register_blueprint(convert_csv_bp)
app.register_blueprint(api_3d_bp)
app.register_blueprint(kpi_bp)
app.register_blueprint(signal_loss_bp)

# 데이터베이스 초기화
with app.app_context():
    init_db()

# 셀 타워 캐시 워밍업 (백그라운드)
try:
    from api.threed.routes import redis_client
    from api.threed.opencellid_client import OpenCellIDClient
    from api.threed.cache_warmup import warmup_cell_tower_cache

    # Get OpenCellID client
    opencellid_client = None
    try:
        opencellid_client = OpenCellIDClient()
    except ValueError:
        pass  # API key not configured, skip warmup

    # Start warmup if both Redis and OpenCellID are available
    if redis_client and opencellid_client:
        warmup_cell_tower_cache(redis_client, opencellid_client)
    else:
        print("⚠️ Cell tower cache warmup skipped (Redis or OpenCellID not available)")
except Exception as e:
    print(f"⚠️ Cache warmup initialization failed: {e}")

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/session/<session_id>')
def session_view(session_id):
    """세션 결과 페이지"""
    return render_template('results.html', session_id=session_id)

@app.route('/compare')
def compare_view():
    """세션 비교 페이지"""
    return render_template('compare.html')

@app.route('/results/<session_id>/<filename>')
def serve_heatmap(session_id, filename):
    """히트맵 HTML 파일 제공 (캐시 무효화)"""
    try:
        heatmap_path = config.RESULTS_FOLDER / session_id / filename
        if heatmap_path.exists() and filename.endswith('.html'):
            from flask import Response
            with open(heatmap_path, 'r', encoding='utf-8') as f:
                content = f.read()

            response = Response(content, mimetype='text/html')
            # 캐시 완전 무효화 헤더
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            return {'error': 'Heatmap file not found'}, 404
    except Exception as e:
        return {'error': str(e)}, 500

@app.errorhandler(404)
def not_found(error):
    return {'error': 'Not found'}, 404

@app.errorhandler(500)
def internal_error(error):
    return {'error': 'Internal server error'}, 500

if __name__ == '__main__':
    print("🚀 비행 통신 품질 분석 플랫폼 시작")
    print(f"📁 업로드 디렉토리: {config.UPLOAD_FOLDER}")
    print(f"📁 결과 디렉토리: {config.RESULTS_FOLDER}")
    print(f"💾 데이터베이스: {config.DATABASE_PATH}")
    print("\n✅ 서버 실행 중: http://localhost:5002")

    app.run(host='0.0.0.0', port=5002, debug=False, use_reloader=False)
