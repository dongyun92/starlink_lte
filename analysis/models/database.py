"""
SQLite 데이터베이스 연결 및 초기화
"""
import sqlite3
from pathlib import Path
from typing import Optional
import config

def get_db() -> sqlite3.Connection:
    """데이터베이스 연결 반환"""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
    return conn

def init_db():
    """데이터베이스 초기화 및 테이블 생성"""
    conn = get_db()
    cursor = conn.cursor()

    # sessions 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            current_step TEXT,
            metadata TEXT,
            file_paths TEXT
        )
    ''')

    # analysis_results 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            session_id TEXT PRIMARY KEY,
            correlation_matrix TEXT,
            key_findings TEXT,
            statistics TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    ''')

    # charts 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            chart_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

    print(f"✅ Database initialized at {config.DATABASE_PATH}")

if __name__ == '__main__':
    init_db()
