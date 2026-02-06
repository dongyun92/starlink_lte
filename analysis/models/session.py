"""
세션 및 분석 결과 모델
"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any
from .database import get_db

class Session:
    """분석 세션 모델"""

    def __init__(self, id: str = None, name: str = None, status: str = 'pending',
                 progress: int = 0, current_step: str = None,
                 metadata: Dict = None, file_paths: Dict = None):
        self.id = id or str(uuid.uuid4())
        self.name = name or f"Flight Analysis {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self.status = status
        self.progress = progress
        self.current_step = current_step
        self.metadata = metadata or {}
        self.file_paths = file_paths or {}
        self.created_at = None

    def save(self):
        """세션을 데이터베이스에 저장"""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO sessions (id, name, status, progress, current_step, metadata, file_paths)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.id,
            self.name,
            self.status,
            self.progress,
            self.current_step,
            json.dumps(self.metadata, ensure_ascii=False),
            json.dumps(self.file_paths, ensure_ascii=False)
        ))

        conn.commit()
        conn.close()

    @staticmethod
    def get_by_id(session_id: str) -> Optional['Session']:
        """ID로 세션 조회"""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Session(
                id=row['id'],
                name=row['name'],
                status=row['status'],
                progress=row['progress'],
                current_step=row['current_step'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {},
                file_paths=json.loads(row['file_paths']) if row['file_paths'] else {}
            )
        return None

    @staticmethod
    def get_all() -> List['Session']:
        """모든 세션 조회"""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM sessions ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for row in rows:
            session = Session(
                id=row['id'],
                name=row['name'],
                status=row['status'],
                progress=row['progress'],
                current_step=row['current_step'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {},
                file_paths=json.loads(row['file_paths']) if row['file_paths'] else {}
            )
            session.created_at = row['created_at']
            sessions.append(session)

        return sessions

    def update_status(self, status: str, progress: int = None, current_step: str = None):
        """상태 업데이트"""
        self.status = status
        if progress is not None:
            self.progress = progress
        if current_step is not None:
            self.current_step = current_step
        self.save()

    def delete(self):
        """세션 삭제"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE id = ?', (self.id,))
        conn.commit()
        conn.close()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status,
            'progress': self.progress,
            'current_step': self.current_step,
            'metadata': self.metadata,
            'file_paths': self.file_paths,
            'created_at': self.created_at
        }


class AnalysisResult:
    """분석 결과 모델"""

    def __init__(self, session_id: str, correlation_matrix: Dict = None,
                 key_findings: List[Dict] = None, statistics: Dict = None):
        self.session_id = session_id
        self.correlation_matrix = correlation_matrix or {}
        self.key_findings = key_findings or []
        self.statistics = statistics or {}

    def save(self):
        """분석 결과 저장"""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO analysis_results (session_id, correlation_matrix, key_findings, statistics)
            VALUES (?, ?, ?, ?)
        ''', (
            self.session_id,
            json.dumps(self.correlation_matrix, ensure_ascii=False),
            json.dumps(self.key_findings, ensure_ascii=False),
            json.dumps(self.statistics, ensure_ascii=False)
        ))

        conn.commit()
        conn.close()

    @staticmethod
    def get_by_session_id(session_id: str) -> Optional['AnalysisResult']:
        """세션 ID로 분석 결과 조회"""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM analysis_results WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return AnalysisResult(
                session_id=row['session_id'],
                correlation_matrix=json.loads(row['correlation_matrix']) if row['correlation_matrix'] else {},
                key_findings=json.loads(row['key_findings']) if row['key_findings'] else [],
                statistics=json.loads(row['statistics']) if row['statistics'] else {}
            )
        return None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'session_id': self.session_id,
            'correlation_matrix': self.correlation_matrix,
            'key_findings': self.key_findings,
            'statistics': self.statistics
        }
