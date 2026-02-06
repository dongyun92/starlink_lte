# 동적 비행 통신 분석 플랫폼 설계

## 📋 프로젝트 목표

기존 하드코딩된 단일 데이터셋 대시보드를 **동적 다중 데이터셋 분석 플랫폼**으로 전환

## 🎯 핵심 요구사항

1. **파일 업로드 인터페이스**
   - 비행 로그 파일 (ULG 형식)
   - LTE 통신 데이터 (CSV)
   - Starlink 통신 데이터 (CSV)

2. **자동 분석 파이프라인**
   - UTC 타임스탬프 동기화
   - 28개 변수 종합 상관관계 분석
   - 6개 신규 차트 생성
   - Word 보고서 자동 생성

3. **결과 시각화**
   - 인터랙티브 지도 (비행 경로 + 품질 오버레이)
   - 실시간 차트 표시
   - Word 보고서 다운로드

4. **다중 데이터셋 관리**
   - 여러 비행 세션 저장
   - 세션별 결과 비교
   - 히스토리 관리

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (HTML + JS)                  │
├─────────────────────────────────────────────────────────┤
│  • 파일 업로드 UI (드래그앤드롭)                          │
│  • 분석 진행 상황 표시 (프로그레스 바)                    │
│  • 인터랙티브 지도 (Leaflet.js)                          │
│  • 차트 갤러리                                           │
│  • 세션 선택 드롭다운                                     │
└─────────────────────────────────────────────────────────┘
                           ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────┐
│               Backend (Flask + Celery)                  │
├─────────────────────────────────────────────────────────┤
│  Routes:                                                │
│  • POST /api/upload - 파일 업로드                        │
│  • GET  /api/sessions - 세션 목록 조회                   │
│  • GET  /api/session/<id>/status - 분석 진행 상황        │
│  • GET  /api/session/<id>/results - 결과 조회            │
│  • GET  /api/session/<id>/download - Word 다운로드       │
│  • GET  /api/session/<id>/map-data - 지도 데이터         │
└─────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────┐
│              Analysis Pipeline (Celery Tasks)           │
├─────────────────────────────────────────────────────────┤
│  1. File Parsing:                                       │
│     - ULG 파싱 (pyulog)                                 │
│     - CSV 검증 및 로드                                   │
│     - UTC 타임스탬프 정규화                              │
│                                                         │
│  2. Data Merging:                                       │
│     - UTC 기준 동기화                                    │
│     - 파생 변수 생성 (13개)                              │
│     - 누락 데이터 처리                                   │
│                                                         │
│  3. Analysis:                                           │
│     - 28x28 상관관계 매트릭스                            │
│     - 품질 등급 분류                                     │
│     - 비행 단계 분류                                     │
│                                                         │
│  4. Visualization:                                      │
│     - 6개 신규 차트 생성                                 │
│     - 기존 9개 차트 생성                                 │
│     - GeoJSON 변환 (지도용)                              │
│                                                         │
│  5. Report Generation:                                  │
│     - Word 보고서 생성 (9.0 MB)                          │
│     - 차트 임베딩                                        │
│     - 분석 텍스트 삽입                                   │
└─────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────┐
│                 Data Storage                            │
├─────────────────────────────────────────────────────────┤
│  uploads/                                               │
│  ├── <session_id>/                                      │
│  │   ├── flight_log.ulg                                │
│  │   ├── lte_data.csv                                  │
│  │   └── starlink_data.csv                             │
│                                                         │
│  results/                                               │
│  ├── <session_id>/                                      │
│  │   ├── charts/                                       │
│  │   │   ├── comprehensive_correlations.png            │
│  │   │   ├── chart1_speed_vs_lte.png                   │
│  │   │   └── ... (15개 차트)                           │
│  │   ├── report.docx                                   │
│  │   ├── analysis_summary.json                         │
│  │   └── map_data.geojson                              │
│                                                         │
│  sessions.db (SQLite)                                   │
│  ├── sessions 테이블                                    │
│  │   - id, created_at, status, metadata                │
│  └── analysis_results 테이블                            │
│      - session_id, correlation_matrix, statistics      │
└─────────────────────────────────────────────────────────┘
```

## 📊 데이터 플로우

```
1. 사용자 파일 업로드
   └─> POST /api/upload (ULG + 2 CSVs)
       └─> 세션 생성 (UUID)
           └─> 파일 저장 (uploads/<session_id>/)
               └─> Celery 분석 작업 시작
                   └─> 백그라운드 분석 실행
                       ├─> ULG 파싱 → 고도, GPS 추출
                       ├─> CSV 로드 → LTE, Starlink
                       ├─> UTC 동기화 → 병합
                       ├─> 파생 변수 생성
                       ├─> 상관관계 분석
                       ├─> 차트 생성 (15개)
                       ├─> GeoJSON 생성
                       └─> Word 보고서 생성

2. 프론트엔드 폴링
   └─> GET /api/session/<id>/status
       └─> {"status": "processing", "progress": 45}
           └─> 프로그레스 바 업데이트

3. 분석 완료
   └─> 상태 업데이트: "completed"
       └─> GET /api/session/<id>/results
           └─> 차트 URL, 통계, 주요 발견 반환
               └─> 프론트엔드 렌더링

4. 결과 다운로드
   └─> GET /api/session/<id>/download
       └─> report.docx 스트리밍

5. 지도 표시
   └─> GET /api/session/<id>/map-data
       └─> GeoJSON 반환
           └─> Leaflet.js 렌더링
```

## 🎨 UI/UX 설계

### 메인 페이지 레이아웃

```
┌──────────────────────────────────────────────────────┐
│  🛰️ 비행 통신 품질 분석 플랫폼                         │
├──────────────────────────────────────────────────────┤
│                                                      │
│  📁 새 분석 시작                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  비행 로그 (ULG):  [파일 선택] 또는 드래그      │ │
│  │  LTE 데이터 (CSV): [파일 선택] 또는 드래그      │ │
│  │  Starlink (CSV):   [파일 선택] 또는 드래그      │ │
│  │                                                │ │
│  │  [분석 시작 버튼]                               │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  📊 이전 분석 결과                                    │
│  ┌────────────────────────────────────────────────┐ │
│  │  • 2026-01-29 14:30 - 한울드론 비행 #1  [보기] │ │
│  │  • 2026-01-28 10:15 - 테스트 비행       [보기] │ │
│  │  • 2026-01-27 16:45 - 장거리 비행       [보기] │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 분석 진행 중 화면

```
┌──────────────────────────────────────────────────────┐
│  ⏳ 분석 진행 중...                                   │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░  45%           │
│                                                      │
│  현재 단계: 상관관계 분석 중 (28개 변수)              │
│                                                      │
│  ✓ 파일 파싱 완료                                    │
│  ✓ UTC 동기화 완료                                   │
│  ⏳ 상관관계 분석 중... (28x28 매트릭스)             │
│  ⏱️ 차트 생성 대기 중                                │
│  ⏱️ Word 보고서 생성 대기 중                         │
│                                                      │
│  예상 소요 시간: 약 2분                              │
└──────────────────────────────────────────────────────┘
```

### 결과 화면

```
┌──────────────────────────────────────────────────────┐
│  ✅ 분석 완료 - 한울드론 비행 #1                      │
├──────────────────────────────────────────────────────┤
│  [탭: 요약] [탭: 지도] [탭: 차트] [탭: 보고서]       │
│                                                      │
│  🎯 주요 발견사항:                                    │
│  • 이동 속도 +0.592 (LTE 품질 최대 영향 요인)        │
│  • 비행 시간 경과 +0.586 (Starlink 지연 증가)        │
│  • 최고 품질 구간: 샘플 800-1200 (110m+7.2m/s)      │
│                                                      │
│  📊 통계:                                            │
│  • 총 샘플: 2,620개 (LTE 100%, Starlink 54%)        │
│  • 비행 시간: 1,310초 (21분 50초)                    │
│  • 최대 고도: 114m                                   │
│  • 비행 거리: 1,063m                                 │
│                                                      │
│  [Word 보고서 다운로드 (9.0 MB)]                     │
│  [모든 차트 ZIP 다운로드]                            │
└──────────────────────────────────────────────────────┘
```

### 지도 탭

```
┌──────────────────────────────────────────────────────┐
│  🗺️ 비행 경로 및 통신 품질 맵                         │
├──────────────────────────────────────────────────────┤
│  레이어 선택:                                         │
│  [✓] LTE RSSI  [✓] Starlink 지연  [ ] 고도  [ ] 속도 │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │                                                │ │
│  │         인터랙티브 지도 (Leaflet.js)            │ │
│  │                                                │ │
│  │  • 시작점 (녹색 마커)                          │ │
│  │  • 비행 경로 (색상 = 품질)                     │ │
│  │    - 녹색: 우수                                │ │
│  │    - 노란색: 양호                              │ │
│  │    - 빨간색: 불량                              │ │
│  │  • 종료점 (빨간 마커)                          │ │
│  │                                                │ │
│  │  클릭 시 세부 정보:                            │ │
│  │  - 시간: 06:08:32                             │ │
│  │  - 고도: 110m                                 │ │
│  │  - LTE RSSI: -75dBm                           │ │
│  │  - Starlink 지연: 62ms                        │ │
│  │                                                │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

## 🔧 기술 스택

### Backend
- **Flask** 2.3+: 웹 서버
- **Celery** 5.3+: 백그라운드 작업 큐
- **Redis**: Celery 브로커
- **SQLite**: 세션 및 메타데이터 저장
- **pyulog**: ULG 파일 파싱
- **pandas**: CSV 처리
- **numpy**: 수치 계산
- **matplotlib/seaborn**: 차트 생성
- **python-docx**: Word 보고서 생성

### Frontend
- **HTML5 + CSS3**: 기본 구조
- **Vanilla JavaScript**: 파일 업로드, AJAX
- **Leaflet.js**: 인터랙티브 지도
- **Chart.js** (선택): 인터랙티브 차트 (이미지 대신)

### Storage
- `uploads/<session_id>/`: 업로드 파일
- `results/<session_id>/`: 분석 결과
- `sessions.db`: SQLite (메타데이터)

## 📁 디렉토리 구조

```
/Users/dykim/dev/starlink/analysis/
├── app.py                          # Flask 메인 앱
├── celery_worker.py                # Celery 워커
├── config.py                       # 설정 파일
├── requirements.txt                # Python 의존성
│
├── api/                            # API 엔드포인트
│   ├── __init__.py
│   ├── upload.py                   # 파일 업로드
│   ├── sessions.py                 # 세션 관리
│   └── results.py                  # 결과 조회
│
├── tasks/                          # Celery 작업
│   ├── __init__.py
│   ├── analysis_pipeline.py        # 분석 파이프라인
│   ├── file_parser.py              # 파일 파싱
│   ├── data_merger.py              # 데이터 병합
│   ├── chart_generator.py          # 차트 생성
│   └── report_generator.py         # 보고서 생성
│
├── models/                         # 데이터 모델
│   ├── __init__.py
│   ├── session.py                  # 세션 모델
│   └── database.py                 # DB 연결
│
├── utils/                          # 유틸리티
│   ├── __init__.py
│   ├── ulg_parser.py               # ULG 파싱 (기존 재사용)
│   ├── correlation_analysis.py     # 상관관계 (기존 재사용)
│   └── geojson_converter.py        # GeoJSON 변환
│
├── templates/                      # HTML 템플릿
│   ├── index.html                  # 메인 페이지
│   ├── upload.html                 # 업로드 페이지
│   └── results.html                # 결과 페이지
│
├── static/                         # 정적 파일
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── upload.js               # 파일 업로드 로직
│   │   ├── map.js                  # 지도 렌더링
│   │   └── results.js              # 결과 표시
│   └── images/
│
├── uploads/                        # 업로드 파일 저장
│   └── <session_id>/
│
├── results/                        # 분석 결과 저장
│   └── <session_id>/
│       ├── charts/
│       ├── report.docx
│       ├── analysis_summary.json
│       └── map_data.geojson
│
└── sessions.db                     # SQLite 데이터베이스
```

## 🔄 API 엔드포인트 명세

### 1. 파일 업로드
```
POST /api/upload
Content-Type: multipart/form-data

Request:
{
  "flight_log": <ULG file>,
  "lte_data": <CSV file>,
  "starlink_data": <CSV file>,
  "metadata": {
    "name": "한울드론 비행 #1",
    "date": "2026-01-29",
    "location": "테스트 필드"
  }
}

Response:
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "created_at": "2026-01-29T14:30:00Z",
  "message": "분석이 시작되었습니다"
}
```

### 2. 세션 목록 조회
```
GET /api/sessions

Response:
{
  "sessions": [
    {
      "id": "a1b2c3d4...",
      "name": "한울드론 비행 #1",
      "created_at": "2026-01-29T14:30:00Z",
      "status": "completed",
      "metadata": {...}
    },
    ...
  ]
}
```

### 3. 분석 진행 상황
```
GET /api/session/<session_id>/status

Response:
{
  "session_id": "a1b2c3d4...",
  "status": "processing",  // processing, completed, failed
  "progress": 45,          // 0-100
  "current_step": "상관관계 분석 중",
  "steps_completed": [
    "파일 파싱",
    "UTC 동기화"
  ],
  "steps_remaining": [
    "차트 생성",
    "보고서 생성"
  ],
  "estimated_time_remaining": 120  // seconds
}
```

### 4. 결과 조회
```
GET /api/session/<session_id>/results

Response:
{
  "session_id": "a1b2c3d4...",
  "metadata": {...},
  "key_findings": [
    {
      "title": "이동 속도가 고도보다 LTE 품질에 더 큰 영향",
      "value": "+0.592",
      "description": "..."
    },
    ...
  ],
  "statistics": {
    "total_samples": 2620,
    "flight_duration": 1310,
    "max_altitude": 114,
    "flight_distance": 1063
  },
  "charts": [
    {
      "name": "comprehensive_correlations",
      "title": "종합 상관관계 히트맵",
      "url": "/results/a1b2c3d4.../charts/comprehensive_correlations.png"
    },
    ...
  ],
  "downloads": {
    "report": "/api/session/a1b2c3d4.../download",
    "charts_zip": "/api/session/a1b2c3d4.../charts-zip"
  }
}
```

### 5. Word 보고서 다운로드
```
GET /api/session/<session_id>/download

Response:
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="flight_analysis_report.docx"

<binary data>
```

### 6. 지도 데이터
```
GET /api/session/<session_id>/map-data

Response:
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [127.12345, 37.54321]
      },
      "properties": {
        "timestamp": "2026-01-29T06:08:32Z",
        "altitude": 110,
        "lte_rssi": -75,
        "starlink_latency": 62,
        "speed": 7.2,
        "quality_grade": "Excellent"
      }
    },
    ...
  ]
}
```

## ⚙️ Celery 작업 정의

```python
# tasks/analysis_pipeline.py

@celery.task(bind=True)
def analyze_flight_data(self, session_id):
    """메인 분석 파이프라인"""

    # 1. 파일 파싱 (10%)
    self.update_state(state='PROGRESS', meta={'progress': 10, 'step': '파일 파싱 중'})
    flight_log = parse_ulg_file(f"uploads/{session_id}/flight_log.ulg")
    lte_data = pd.read_csv(f"uploads/{session_id}/lte_data.csv")
    starlink_data = pd.read_csv(f"uploads/{session_id}/starlink_data.csv")

    # 2. UTC 동기화 (25%)
    self.update_state(state='PROGRESS', meta={'progress': 25, 'step': 'UTC 동기화 중'})
    merged_data = merge_datasets_utc(flight_log, lte_data, starlink_data)

    # 3. 파생 변수 생성 (35%)
    self.update_state(state='PROGRESS', meta={'progress': 35, 'step': '파생 변수 생성 중'})
    merged_data = add_derived_variables(merged_data)

    # 4. 상관관계 분석 (50%)
    self.update_state(state='PROGRESS', meta={'progress': 50, 'step': '상관관계 분석 중'})
    correlation_matrix = compute_correlation_matrix(merged_data)

    # 5. 차트 생성 (75%)
    self.update_state(state='PROGRESS', meta={'progress': 75, 'step': '차트 생성 중'})
    generate_all_charts(merged_data, correlation_matrix, f"results/{session_id}/charts")

    # 6. GeoJSON 생성 (85%)
    self.update_state(state='PROGRESS', meta={'progress': 85, 'step': '지도 데이터 생성 중'})
    generate_geojson(merged_data, f"results/{session_id}/map_data.geojson")

    # 7. Word 보고서 생성 (95%)
    self.update_state(state='PROGRESS', meta={'progress': 95, 'step': 'Word 보고서 생성 중'})
    generate_word_report(merged_data, correlation_matrix, f"results/{session_id}/report.docx")

    # 8. 완료 (100%)
    self.update_state(state='SUCCESS', meta={'progress': 100, 'step': '분석 완료'})

    return {
        'session_id': session_id,
        'status': 'completed',
        'charts_count': 15,
        'report_size': os.path.getsize(f"results/{session_id}/report.docx")
    }
```

## 📊 데이터베이스 스키마

```sql
-- sessions.db

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,  -- UUID
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,  -- processing, completed, failed
    progress INTEGER DEFAULT 0,
    current_step TEXT,
    metadata JSON,  -- {date, location, aircraft, ...}
    file_paths JSON  -- {ulg, lte_csv, starlink_csv}
);

CREATE TABLE analysis_results (
    session_id TEXT PRIMARY KEY,
    correlation_matrix JSON,
    key_findings JSON,
    statistics JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE charts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    chart_name TEXT,
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

## 🚀 구현 단계

### Phase 1: 기본 인프라 (1-2일)
- [ ] Flask 앱 구조 생성
- [ ] SQLite 데이터베이스 설정
- [ ] 파일 업로드 API 구현
- [ ] 세션 관리 시스템
- [ ] 기본 UI (파일 업로드 페이지)

### Phase 2: 분석 파이프라인 (2-3일)
- [ ] Celery 설정 및 작업 정의
- [ ] 기존 분석 코드 모듈화
  - [ ] comprehensive_correlation_analysis.py → tasks/
  - [ ] multidimensional_charts.py → tasks/
  - [ ] word_report_generator.py → tasks/
- [ ] 파일 파싱 로직
- [ ] UTC 동기화 로직
- [ ] 진행 상황 추적

### Phase 3: 결과 표시 (2일)
- [ ] 결과 조회 API
- [ ] 차트 갤러리 UI
- [ ] Word 다운로드 엔드포인트
- [ ] 통계 요약 표시

### Phase 4: 지도 통합 (1-2일)
- [ ] GeoJSON 변환 유틸리티
- [ ] Leaflet.js 지도 컴포넌트
- [ ] 품질 오버레이 레이어
- [ ] 인터랙티브 팝업

### Phase 5: 다중 세션 관리 (1일)
- [ ] 세션 목록 페이지
- [ ] 세션 비교 기능
- [ ] 세션 삭제 기능
- [ ] 검색 및 필터링

### Phase 6: 테스트 및 최적화 (1일)
- [ ] 대용량 파일 처리 테스트
- [ ] 에러 처리 및 복구
- [ ] 성능 최적화
- [ ] UI/UX 개선

## 📝 다음 단계

1. **사용자 확인**: 설계 승인
2. **우선순위 결정**: 어떤 단계부터 시작할까?
3. **프로토타입 개발**: Phase 1 시작

---

**작성일**: 2026-01-29
**목적**: 동적 다중 데이터셋 비행 통신 분석 플랫폼
**예상 개발 기간**: 7-10일 (풀타임 기준)
