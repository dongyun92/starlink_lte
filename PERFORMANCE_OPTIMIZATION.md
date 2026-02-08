# 성능 최적화 분석 및 개선 방안

## 현재 성능 지표 (2026-02-08)

### API 응답 시간 측정
| API 엔드포인트 | 응답 시간 | 데이터 크기 | 상태 |
|----------------|-----------|-------------|------|
| CZML 비행 경로 (dual) | **3.24초** | 1.93 MB | 🔴 매우 느림 |
| LTE 포인트 히트맵 | 0.31초 | 667 KB | 🟡 보통 |
| LTE 복셀 히트맵 | 1.28초 | 29 KB | 🟡 보통 |

### 데이터 규모
- **데이터 포인트**: 8,101개 (merged_data.csv)
- **원본 CSV 크기**: 8.1 MB
- **비행 수**: 2개 (RTL: 2,620 pts, 일반: 5,481 pts)

## 🔴 주요 병목 지점

### 1. CZML 생성 속도 (가장 심각)
**문제**: 3.2초 응답 시간
- 8,000+ 데이터 포인트를 모두 처리
- 샘플링 로직 버그 (`sample_rate` 무시됨)
- 듀얼 경로 생성 시 세그먼트 분할 오버헤드

**영향**:
- 세션 선택 시 3초 대기
- 비행 시나리오 전환 시 3초 대기
- 사용자 경험 저하

### 2. 포인트 히트맵 렌더링
**문제**: 667 KB, 3,000+ 엔티티
- Cesium이 각 포인트를 별도 엔티티로 렌더링
- GPU 부하 증가
- 브라우저 메모리 사용량 증가

### 3. 복셀 히트맵 계산
**문제**: 1.28초 계산 시간
- 3D 공간 분할 (50x50x15m 그리드)
- 각 복셀마다 평균 품질 계산
- NumPy 연산 최적화 필요

## ✅ 최적화 방안

### 우선순위 1: 샘플링 수정 (즉각 효과)

#### 백엔드 수정
**파일**: `analysis/api/threed/czml_generator.py:65`

```python
# 현재 (잘못된 로직)
sample_interval = max(1, int(len(df) / (len(df) * sample_rate)))  # 항상 1

# 수정 (올바른 로직)
if sample_rate > 0:
    # sample_rate가 0.5면 2초마다 1개 포인트 (간격 2)
    # sample_rate가 0.1면 10초마다 1개 포인트 (간격 10)
    sample_interval = max(1, int(1 / sample_rate))
    df = df.iloc[::sample_interval].copy()
    print(f"🎯 Sampling: {len(df)} points (interval={sample_interval})")
```

#### 프론트엔드 수정
**파일**: `frontend/src/services/api.ts`

```typescript
// 현재
const czmlData = await getCZMLData(selectedSessionId, {
  sample_rate: 1,  // 모든 포인트
  color_by: 'dual',
});

// 최적화 (0.5초마다 1개 포인트)
const czmlData = await getCZMLData(selectedSessionId, {
  sample_rate: 0.5,  // 2배 샘플링 = 4,000 → 2,000 포인트
  color_by: 'dual',
});
```

**예상 효과**:
- `sample_rate: 0.5` → 응답 시간 **1.6초** (50% 감소)
- `sample_rate: 0.2` → 응답 시간 **0.6초** (80% 감소)
- 데이터 크기 비례 감소

### 우선순위 2: 응답 캐싱 (중간 효과)

#### Redis 캐싱 추가
**파일**: `analysis/api/threed/routes.py`

```python
import redis
import hashlib
import json

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

@api_3d_bp.route('/czml/<session_id>', methods=['GET'])
def get_czml_data(session_id):
    sample_rate = request.args.get('sample_rate', 1, type=int)
    color_by = request.args.get('color_by', 'altitude', type=str)
    flight_id = request.args.get('flight_id', None, type=int)

    # 캐시 키 생성
    cache_key = f"czml:{session_id}:{color_by}:{sample_rate}:{flight_id}"

    # 캐시 확인
    cached = redis_client.get(cache_key)
    if cached:
        print(f"✅ Cache HIT: {cache_key}")
        return jsonify(json.loads(cached)), 200

    # 생성
    generator = CZMLGenerator(session_id)
    czml_data = generator.generate(sample_rate=sample_rate, color_by=color_by, flight_id=flight_id)

    # 캐시 저장 (5분)
    redis_client.setex(cache_key, 300, json.dumps(czml_data))
    print(f"💾 Cache MISS: {cache_key} saved")

    return jsonify(czml_data), 200
```

**예상 효과**:
- 첫 로드: 3.2초 (변화 없음)
- 재로드: **<0.1초** (캐시 히트)
- 동일 세션 반복 접근 시 극적 개선

### 우선순위 3: 프론트엔드 메모이제이션 (단기 효과)

#### React 최적화
**파일**: `frontend/src/components/CesiumViewer.tsx`

```typescript
import { useMemo, useCallback } from 'react';

// API 호출 메모이제이션
const loadFlightData = useCallback(async () => {
  // ... existing code
}, [selectedSessionId, selectedFlightId]);

// CZML 데이터 소스 메모이제이션
const czmlDataSource = useMemo(() => {
  if (!czmlData) return null;
  return Cesium.CzmlDataSource.load(czmlData);
}, [czmlData]);
```

**예상 효과**:
- 불필요한 리렌더링 방지
- 메모리 사용량 감소

### 우선순위 4: 히트맵 최적화 (장기 개선)

#### 복셀 계산 병렬화
**파일**: `analysis/api/threed/czml_generator.py`

```python
from multiprocessing import Pool
import numpy as np

def _calculate_voxel_quality(args):
    """병렬 처리를 위한 복셀 품질 계산"""
    voxel_data, mode, lte_column, starlink_column = args
    # ... 품질 계산 로직
    return avg_quality, center_pos

def _create_voxel_heatmap_entities(self, df, mode: str) -> list:
    # ... existing setup

    # 병렬 처리
    with Pool(processes=4) as pool:
        voxel_args = [(voxel_data, mode, lte_col, sl_col)
                      for voxel_data in voxel_chunks]
        results = pool.map(_calculate_voxel_quality, voxel_args)

    # 결과 조립
    entities = [create_box_entity(result) for result in results]
```

**예상 효과**:
- 복셀 계산 시간: **1.28초 → 0.4초** (3배 빠름)

#### 포인트 히트맵 간소화
**옵션 1**: 클러스터링
```python
from sklearn.cluster import KMeans

# 3000개 포인트를 500개 클러스터로 축소
kmeans = KMeans(n_clusters=500)
clusters = kmeans.fit_predict(df[['latitude', 'longitude', 'altitude']])
```

**옵션 2**: LOD (Level of Detail)
- 줌 레벨에 따라 포인트 밀도 조정
- 멀리 있을 때: 샘플링 0.1 (10%)
- 가까이 있을 때: 샘플링 1.0 (100%)

### 우선순위 5: 데이터 압축 (네트워크 최적화)

#### gzip 압축 활성화
**파일**: `analysis/app.py`

```python
from flask import Flask
from flask_compress import Compress

app = Flask(__name__)
Compress(app)  # 자동 gzip 압축

# 또는 수동 압축
import gzip
import json

@api_3d_bp.route('/czml/<session_id>', methods=['GET'])
def get_czml_data(session_id):
    czml_data = generator.generate(...)

    # gzip 압축
    compressed = gzip.compress(json.dumps(czml_data).encode('utf-8'))

    response = make_response(compressed)
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Type'] = 'application/json'
    return response
```

**예상 효과**:
- 1.93 MB → **~400 KB** (80% 감소)
- 네트워크 전송 시간 대폭 감소

## 📊 예상 성능 개선

| 최적화 단계 | CZML 응답 | 데이터 크기 | 사용자 체감 |
|-------------|-----------|-------------|-------------|
| **현재** | 3.24초 | 1.93 MB | 🔴 느림 |
| + 샘플링 (0.5) | 1.6초 | 965 KB | 🟡 보통 |
| + 샘플링 (0.2) | 0.6초 | 386 KB | 🟢 빠름 |
| + Redis 캐시 | <0.1초 | 386 KB | 🟢 매우 빠름 |
| + gzip 압축 | <0.1초 | 77 KB | 🟢 매우 빠름 |

## 🚀 즉시 적용 가능한 수정

### 1단계: 샘플링 수정 (5분 작업)
```bash
# 백엔드 수정
vim analysis/api/threed/czml_generator.py  # Line 65

# 프론트엔드 수정
vim frontend/src/components/CesiumViewer.tsx  # Line 157

# 재시작
pkill -f flask && cd analysis && nohup flask run --port=5002 &
```

### 2단계: 샘플레이트 조정 (1분 작업)
```typescript
// CesiumViewer.tsx
const czmlData = await getCZMLData(selectedSessionId, {
  sample_rate: 0.2,  // 80% 빠름
  color_by: 'dual',
  flight_id: selectedFlightId !== null ? selectedFlightId : undefined,
});
```

**즉시 효과**:
- 3.2초 → 0.6초 (**5배 빠름**)
- 사용자가 바로 체감 가능

## 📝 추가 고려사항

### 모바일 최적화
- 샘플링 더 공격적 적용 (`sample_rate: 0.1`)
- 히트맵 기본값을 복셀로 변경
- 자동 LOD 적용

### 서버 스펙 개선
- Redis 설치 및 캐싱 활성화
- NumPy/Pandas 최적화 빌드
- CPU 코어 증가 (병렬 처리)

### 프론트엔드 최적화
- React.memo() 적용
- useCallback/useMemo 활용
- Virtual DOM 최적화
- Web Worker로 CZML 파싱 이동

## 결론

**가장 효과적인 단기 해결책**:
1. ✅ 샘플링 로직 수정 (5분, 5배 개선)
2. ✅ Redis 캐싱 추가 (30분, 30배 개선)
3. ✅ gzip 압축 활성화 (10분, 80% 크기 감소)

**총 예상 개선**:
- 초기 로드: 3.2초 → **0.6초** (5배 빠름)
- 재로드: 3.2초 → **<0.1초** (30배 빠름)
- 데이터 크기: 1.93 MB → **77 KB** (96% 감소)

---
생성일: 2026-02-08
작성: Performance Analysis
