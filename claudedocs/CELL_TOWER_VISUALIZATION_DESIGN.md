# 📡 LTE 기지국 시각화 설계 (OpenCellID 통합)

## 📋 프로젝트 개요

**목표**: 비행 경로와 LTE 기지국 위치를 3D 지도에 함께 시각화하여 신호 품질과 지리적 관계 분석

**데이터 소스**: OpenCellID (https://opencellid.org/)
- 한국 데이터: 886,966개 셀 (LTE 787,107개)
- API 제한: 무료 1일 1,000회
- 크라우드소싱 기반 (도심 데이터 양호)

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React + Cesium)             │
├─────────────────────────────────────────────────────────┤
│  📍 CesiumViewer                                        │
│  ├─ 비행 경로 (기존)                                     │
│  ├─ 히트맵 (기존)                                        │
│  └─ 기지국 마커 (NEW)                                    │
│      ├─ 3D 타워 아이콘                                   │
│      ├─ 커버리지 반경 (반투명 원)                        │
│      └─ 기지국 정보 팝업 (클릭 시)                       │
│                                                          │
│  🎛️ UnifiedControlPanel                                │
│  └─ Cell Towers 섹션 (NEW)                             │
│      ├─ Show Cell Towers (체크박스)                     │
│      ├─ Show Coverage (체크박스)                        │
│      └─ Coverage Radius (슬라이더: 100m ~ 5km)          │
└─────────────────────────────────────────────────────────┘
                            ↓↑ HTTP/REST
┌─────────────────────────────────────────────────────────┐
│              Backend (Flask API)                        │
├─────────────────────────────────────────────────────────┤
│  🔌 New API Endpoint                                    │
│  └─ GET /api/3d/cell-towers/<session_id>               │
│      ├─ Query OpenCellID API                           │
│      ├─ Filter by flight path bounding box             │
│      ├─ Cache results (Redis, TTL 1 day)               │
│      └─ Return GeoJSON format                          │
└─────────────────────────────────────────────────────────┘
                            ↓↑ HTTP
┌─────────────────────────────────────────────────────────┐
│              OpenCellID API                             │
├─────────────────────────────────────────────────────────┤
│  📡 Endpoint                                            │
│  └─ GET https://opencellid.org/cell/getInArea          │
│      ├─ Parameters: lat, lon, radius (max 100km)       │
│      ├─ Response: JSON array of cell towers            │
│      └─ Rate Limit: 1,000 requests/day (free tier)     │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 데이터 모델

### OpenCellID API Response

```json
{
  "cells": [
    {
      "radio": "LTE",           // 기술: LTE, UMTS, GSM, NR
      "mcc": 450,               // Mobile Country Code (한국: 450)
      "mnc": 5,                 // Mobile Network Code (SK: 5, KT: 8, LGU+: 6)
      "lac": 30721,             // Location Area Code
      "cid": 8888888,           // Cell ID
      "lon": 126.9784,          // 경도
      "lat": 37.5665,           // 위도
      "range": 1000,            // 커버리지 반경 (미터)
      "samples": 150,           // 측정 샘플 수
      "changeable": 1,          // 위치 변경 가능성
      "created": 1609459200,    // 생성 타임스탬프
      "updated": 1643673600,    // 업데이트 타임스탬프
      "averageSignal": -75      // 평균 신호 강도 (dBm)
    }
  ]
}
```

### Backend Response Format (GeoJSON)

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [126.9784, 37.5665, 0]  // [lon, lat, altitude]
      },
      "properties": {
        "id": "450-5-30721-8888888",
        "radio": "LTE",
        "operator": "SK Telecom",
        "range": 1000,
        "samples": 150,
        "signal": -75,
        "updated": "2022-02-01"
      }
    }
  ]
}
```

---

## 🔧 구현 계획

### Phase 1: Backend API (우선순위 높음)

#### 1.1 OpenCellID 클라이언트 구현

**파일**: `analysis/api/threed/opencellid_client.py`

```python
"""
OpenCellID API Client
"""
import requests
from typing import List, Dict, Optional
import os

class OpenCellIDClient:
    """OpenCellID API wrapper"""

    BASE_URL = "https://opencellid.org/cell/getInArea"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenCellID client

        Args:
            api_key: OpenCellID API key (or use OPENCELLID_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENCELLID_API_KEY')
        if not self.api_key:
            raise ValueError("OpenCellID API key required")

    def get_cell_towers_in_area(
        self,
        lat: float,
        lon: float,
        radius: int = 10000,  # 10km default
        radio: str = 'LTE',
        limit: int = 500
    ) -> List[Dict]:
        """
        Get cell towers within radius of a point

        Args:
            lat: Latitude center point
            lon: Longitude center point
            radius: Search radius in meters (max 100,000)
            radio: Radio type filter (LTE, UMTS, GSM, NR, or all)
            limit: Max number of results (default 500)

        Returns:
            List of cell tower dicts
        """
        params = {
            'key': self.api_key,
            'lat': lat,
            'lon': lon,
            'radius': min(radius, 100000),  # Max 100km
            'format': 'json',
            'limit': limit
        }

        if radio and radio != 'all':
            params['radio'] = radio

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('cells', [])
        except requests.exceptions.RequestException as e:
            print(f"❌ OpenCellID API error: {e}")
            return []

    def get_cell_towers_in_bounding_box(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        radio: str = 'LTE'
    ) -> List[Dict]:
        """
        Get cell towers within a bounding box

        Strategy: Query center point with radius covering entire box

        Args:
            min_lat: Minimum latitude
            max_lat: Maximum latitude
            min_lon: Minimum longitude
            max_lon: Maximum longitude
            radio: Radio type filter

        Returns:
            List of cell tower dicts
        """
        # Calculate center point
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        # Calculate radius to cover entire bounding box
        # Use Haversine distance approximation
        lat_diff = max_lat - min_lat
        lon_diff = max_lon - min_lon

        # Rough approximation: 111km per degree latitude
        # Longitude varies by latitude, but use conservative estimate
        radius_km = max(lat_diff, lon_diff) * 111 * 0.7  # 70% of diagonal
        radius_m = int(radius_km * 1000)

        # Query with calculated radius
        towers = self.get_cell_towers_in_area(
            center_lat, center_lon, radius_m, radio
        )

        # Filter results to actual bounding box
        filtered = [
            tower for tower in towers
            if (min_lat <= tower['lat'] <= max_lat and
                min_lon <= tower['lon'] <= max_lon)
        ]

        return filtered
```

#### 1.2 기지국 데이터 API 엔드포인트

**파일**: `analysis/api/threed/routes.py` (기존 파일에 추가)

```python
from .opencellid_client import OpenCellIDClient
import redis
import json
import hashlib

# Redis client (기존 코드와 공유)
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# OpenCellID client (싱글톤)
opencellid_client = None

def get_opencellid_client():
    """Get or create OpenCellID client"""
    global opencellid_client
    if opencellid_client is None:
        try:
            opencellid_client = OpenCellIDClient()
        except ValueError as e:
            print(f"⚠️ OpenCellID client not available: {e}")
            return None
    return opencellid_client

@api_3d_bp.route('/cell-towers/<session_id>', methods=['GET'])
def get_cell_towers(session_id):
    """
    Get cell tower data for visualization

    Query Parameters:
        - radio: Radio type filter (LTE, UMTS, GSM, NR, all) [default: LTE]
        - use_cache: Use cached data if available (true/false) [default: true]

    Response:
        GeoJSON FeatureCollection with cell tower locations
    """
    try:
        # Get query parameters
        radio = request.args.get('radio', 'LTE', type=str)
        use_cache = request.args.get('use_cache', 'true', type=str) == 'true'

        # Check if OpenCellID is configured
        client = get_opencellid_client()
        if client is None:
            return jsonify({
                'error': 'OpenCellID API key not configured',
                'message': 'Set OPENCELLID_API_KEY environment variable'
            }), 503

        # Cache key
        cache_key = f"cell_towers:{session_id}:{radio}"

        # Check cache (24 hour TTL)
        if use_cache:
            cached = redis_client.get(cache_key)
            if cached:
                print(f"✅ Cell towers cache HIT: {cache_key}")
                return jsonify(json.loads(cached)), 200

        # Load session data to get bounding box
        session = SessionData(session_id)
        df = session.load_merged_data()

        if df.empty:
            return jsonify({'error': 'No flight data available'}), 404

        # Calculate bounding box with margin
        MARGIN = 0.05  # ~5km margin
        min_lat = df['latitude'].min() - MARGIN
        max_lat = df['latitude'].max() + MARGIN
        min_lon = df['longitude'].min() - MARGIN
        max_lon = df['longitude'].max() + MARGIN

        print(f"📡 Querying cell towers: {radio}, bbox=[{min_lat:.4f}, {max_lat:.4f}, {min_lon:.4f}, {max_lon:.4f}]")

        # Query OpenCellID
        towers = client.get_cell_towers_in_bounding_box(
            min_lat, max_lat, min_lon, max_lon, radio
        )

        print(f"   Found {len(towers)} towers")

        # Convert to GeoJSON
        geojson = _convert_towers_to_geojson(towers)

        # Cache result (24 hours)
        redis_client.setex(cache_key, 86400, json.dumps(geojson))
        print(f"💾 Cell towers cached: {cache_key}")

        return jsonify(geojson), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to fetch cell towers: {str(e)}'}), 500


def _convert_towers_to_geojson(towers: List[Dict]) -> Dict:
    """
    Convert OpenCellID tower list to GeoJSON FeatureCollection

    Args:
        towers: List of tower dicts from OpenCellID

    Returns:
        GeoJSON FeatureCollection
    """
    # Operator mapping (MCC 450 = Korea)
    OPERATORS = {
        5: 'SK Telecom',
        6: 'LG U+',
        8: 'KT'
    }

    features = []

    for tower in towers:
        # Skip towers without coordinates
        if not tower.get('lat') or not tower.get('lon'):
            continue

        # Create feature
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [
                    float(tower['lon']),
                    float(tower['lat']),
                    0  # Ground level
                ]
            },
            'properties': {
                'id': f"{tower.get('mcc', 'unknown')}-{tower.get('mnc', 'unknown')}-{tower.get('lac', 'unknown')}-{tower.get('cid', 'unknown')}",
                'radio': tower.get('radio', 'unknown'),
                'operator': OPERATORS.get(tower.get('mnc'), 'Unknown'),
                'mcc': tower.get('mcc'),
                'mnc': tower.get('mnc'),
                'lac': tower.get('lac'),
                'cid': tower.get('cid'),
                'range': tower.get('range', 1000),  # Default 1km
                'samples': tower.get('samples', 0),
                'signal': tower.get('averageSignal'),
                'updated': tower.get('updated')
            }
        }

        features.append(feature)

    return {
        'type': 'FeatureCollection',
        'features': features
    }
```

#### 1.3 환경 변수 설정

**파일**: `analysis/.env` (추가)

```bash
# OpenCellID API Key
# Get free key from: https://opencellid.org/register.php
OPENCELLID_API_KEY=your_api_key_here
```

---

### Phase 2: Frontend UI Controls (우선순위 높음)

#### 2.1 UnifiedControlPanel에 Cell Towers 섹션 추가

**파일**: `frontend/src/components/UnifiedControlPanel.tsx`

```typescript
interface UnifiedControlPanelProps {
  // ... 기존 props

  // Cell tower controls (NEW)
  showCellTowers: boolean;
  showCoverage: boolean;
  coverageRadius: number;  // 100 ~ 5000 (meters)
  onCellTowersToggle: (enabled: boolean) => void;
  onCoverageToggle: (enabled: boolean) => void;
  onCoverageRadiusChange: (radius: number) => void;
}

// UI 추가 (Quality Heatmaps 섹션 아래)
{/* Cell Towers */}
<div className="space-y-2">
  <div className="text-xs font-bold text-gray-700 mb-2">📡 Cell Towers</div>

  <label className="flex items-center gap-2 cursor-pointer">
    <input
      type="checkbox"
      checked={showCellTowers}
      onChange={(e) => onCellTowersToggle(e.target.checked)}
      className="w-3 h-3"
    />
    <span className="text-xs">Show LTE Towers</span>
  </label>

  <label className="flex items-center gap-2 cursor-pointer">
    <input
      type="checkbox"
      checked={showCoverage}
      onChange={(e) => onCoverageToggle(e.target.checked)}
      disabled={!showCellTowers}
      className="w-3 h-3"
    />
    <span className="text-xs">Show Coverage Radius</span>
  </label>

  {showCellTowers && (
    <div className="pl-2">
      <label className="block">
        <span className="text-xs text-gray-600 mb-1 block">
          Coverage Radius: {(coverageRadius / 1000).toFixed(1)} km
        </span>
        <input
          type="range"
          min="100"
          max="5000"
          step="100"
          value={coverageRadius}
          onChange={(e) => onCoverageRadiusChange(parseInt(e.target.value))}
          className="w-full h-1 bg-gray-300 rounded-lg appearance-none cursor-pointer"
        />
      </label>
    </div>
  )}
</div>
```

---

### Phase 3: Cesium 시각화 (우선순위 중간)

#### 3.1 기지국 데이터 로딩 및 표시

**파일**: `frontend/src/components/CesiumViewer.tsx`

```typescript
// State 추가
const [showCellTowers, setShowCellTowers] = useState(false);
const [showCoverage, setShowCoverage] = useState(false);
const [coverageRadius, setCoverageRadius] = useState(1000); // 1km default
const [cellTowerData, setCellTowerData] = useState<any>(null);

// Ref 추가
const cellTowerEntitiesRef = useRef<any[]>([]);

// 기지국 데이터 로드 useEffect
useEffect(() => {
  if (!selectedSessionId || !showCellTowers) {
    return;
  }

  const loadCellTowers = async () => {
    try {
      console.log('📡 Loading cell towers...');
      const response = await fetch(
        `http://localhost:5002/api/3d/cell-towers/${selectedSessionId}?radio=LTE`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setCellTowerData(data);
      console.log(`✅ Loaded ${data.features.length} cell towers`);
    } catch (error) {
      console.error('❌ Failed to load cell towers:', error);
    }
  };

  loadCellTowers();
}, [selectedSessionId, showCellTowers]);

// 기지국 시각화 useEffect
useEffect(() => {
  if (!cesiumViewerRef.current || !cellTowerData) {
    return;
  }

  const Cesium = window.Cesium;
  const viewer = cesiumViewerRef.current;

  // Clear existing entities
  cellTowerEntitiesRef.current.forEach(entity => {
    viewer.entities.remove(entity);
  });
  cellTowerEntitiesRef.current = [];

  if (!showCellTowers) {
    return;
  }

  // Add tower entities
  cellTowerData.features.forEach((feature: any) => {
    const coords = feature.geometry.coordinates;
    const props = feature.properties;

    // Tower marker (billboard icon)
    const towerEntity = viewer.entities.add({
      id: `tower_${props.id}`,
      name: `${props.operator} ${props.radio} Tower`,
      position: Cesium.Cartesian3.fromDegrees(coords[0], coords[1], 30), // 30m above ground
      billboard: {
        image: '/cell-tower-icon.png',  // 타워 아이콘 필요
        width: 24,
        height: 24,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND
      },
      description: `
        <table>
          <tr><th>Operator</th><td>${props.operator}</td></tr>
          <tr><th>Type</th><td>${props.radio}</td></tr>
          <tr><th>Range</th><td>${props.range}m</td></tr>
          <tr><th>Samples</th><td>${props.samples}</td></tr>
          <tr><th>Avg Signal</th><td>${props.signal} dBm</td></tr>
        </table>
      `
    });

    cellTowerEntitiesRef.current.push(towerEntity);

    // Coverage radius (circle)
    if (showCoverage) {
      const coverageEntity = viewer.entities.add({
        id: `coverage_${props.id}`,
        position: Cesium.Cartesian3.fromDegrees(coords[0], coords[1], 0),
        ellipse: {
          semiMinorAxis: coverageRadius,
          semiMajorAxis: coverageRadius,
          material: Cesium.Color.BLUE.withAlpha(0.2),
          outline: true,
          outlineColor: Cesium.Color.BLUE,
          outlineWidth: 2,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
        }
      });

      cellTowerEntitiesRef.current.push(coverageEntity);
    }
  });

  console.log(`✅ Rendered ${cellTowerEntitiesRef.current.length} cell tower entities`);

}, [cellTowerData, showCellTowers, showCoverage, coverageRadius]);
```

#### 3.2 타워 아이콘 리소스

**파일**: `frontend/public/cell-tower-icon.png`

옵션:
1. Font Awesome 아이콘 사용
2. SVG 직접 생성
3. 무료 아이콘 다운로드 (https://www.flaticon.com/free-icon/cell-tower)

**SVG 예시**:
```html
<svg width="24" height="24" viewBox="0 0 24 24" fill="#0066FF">
  <path d="M12 2L8 8h8l-4-6z"/>
  <rect x="10" y="8" width="4" height="14"/>
  <circle cx="12" cy="6" r="1" fill="white"/>
</svg>
```

---

### Phase 4: 성능 최적화 (우선순위 낮음)

#### 4.1 클러스터링 (많은 기지국 처리)

기지국이 500개 이상일 경우 성능 문제 가능성:
- **Option 1**: Cesium Entity Clustering 사용
- **Option 2**: 줌 레벨에 따라 LOD (Level of Detail) 적용
- **Option 3**: Viewport 내 기지국만 표시

```typescript
// Cesium Entity Clustering 예시
const dataSourcePromise = Cesium.GeoJsonDataSource.load(cellTowerData, {
  clampToGround: true
});

dataSourcePromise.then(dataSource => {
  viewer.dataSources.add(dataSource);

  // Enable clustering
  dataSource.clustering.enabled = true;
  dataSource.clustering.pixelRange = 50;
  dataSource.clustering.minimumClusterSize = 5;
});
```

#### 4.2 백엔드 필터링

비행 경로와 가까운 기지국만 반환:
- 비행 경로 중심점 기준 반경 검색
- 거리 계산 후 가까운 N개만 선택

---

## 🎨 UI/UX 디자인

### 컨트롤 패널 레이아웃

```
┌───────────────────────────┐
│ Controls                  │
├───────────────────────────┤
│ Session: [Dropdown]       │
│ Camera Mode: [Button]     │
│ Flight Scenario: [Drop]   │
│ Path Color Mode:          │
│   ○ Altitude              │
│   ○ LTE Signal            │
│   ○ Starlink              │
│   ○ Speed                 │
├───────────────────────────┤
│ 📡 Cell Towers            │
│ ☑ Show LTE Towers         │
│ ☑ Show Coverage Radius    │
│ Coverage: [====|--] 1.5km │
├───────────────────────────┤
│ Quality Heatmaps          │
│ ○ Points / ● Voxels       │
│ ☐ LTE Heatmap             │
│ ☐ Starlink Heatmap        │
│ ☐ Combined Heatmap        │
└───────────────────────────┘
```

### 색상 스키마

**기지국 마커**:
- SK Telecom: 파랑 (#0066FF)
- KT: 빨강 (#FF0000)
- LG U+: 자홍 (#D10869)

**커버리지 반경**:
- 색상: 반투명 파랑 (rgba(0, 102, 255, 0.2))
- 테두리: 파랑 (#0066FF), 2px

---

## 📝 구현 체크리스트

### Backend (2-3시간)
- [ ] `opencellid_client.py` 생성
  - [ ] `OpenCellIDClient` 클래스 구현
  - [ ] `get_cell_towers_in_area()` 메서드
  - [ ] `get_cell_towers_in_bounding_box()` 메서드
- [ ] `routes.py` 수정
  - [ ] `/api/3d/cell-towers/<session_id>` 엔드포인트 추가
  - [ ] GeoJSON 변환 함수 구현
  - [ ] Redis 캐싱 적용 (24시간 TTL)
- [ ] `.env` 파일 업데이트
  - [ ] `OPENCELLID_API_KEY` 환경 변수 추가
- [ ] API 키 발급
  - [ ] OpenCellID 가입 및 무료 API 키 발급
- [ ] 테스트
  - [ ] 서울 중심 기지국 조회 테스트
  - [ ] GeoJSON 포맷 검증

### Frontend (3-4시간)
- [ ] `UnifiedControlPanel.tsx` 수정
  - [ ] Cell Towers 섹션 UI 추가
  - [ ] Props 인터페이스 업데이트
- [ ] `CesiumViewer.tsx` 수정
  - [ ] 기지국 state/ref 추가
  - [ ] 기지국 데이터 로딩 useEffect
  - [ ] 기지국 시각화 useEffect
  - [ ] 커버리지 반경 표시 로직
- [ ] API 서비스 함수 추가
  - [ ] `frontend/src/services/api.ts`에 `getCellTowers()` 추가
- [ ] 타워 아이콘 리소스
  - [ ] SVG 아이콘 생성 또는 다운로드
  - [ ] `public/cell-tower-icon.png` 추가
- [ ] 테스트
  - [ ] 기지국 표시/숨김 토글
  - [ ] 커버리지 반경 조정
  - [ ] 기지국 클릭 시 정보 팝업

### Performance & Polish (1-2시간)
- [ ] 성능 최적화
  - [ ] 500개 이상 기지국 시 클러스터링 적용
  - [ ] Viewport 외부 기지국 필터링
- [ ] 에러 핸들링
  - [ ] OpenCellID API 실패 시 fallback UI
  - [ ] API 키 미설정 시 안내 메시지
- [ ] 문서화
  - [ ] README에 OpenCellID 설정 가이드 추가
  - [ ] 환경 변수 설정 문서화

---

## 🧪 테스트 시나리오

### 1. API 테스트

```bash
# 환경 변수 설정
export OPENCELLID_API_KEY="your_key_here"

# 백엔드 재시작
./server.sh backend-restart

# 기지국 데이터 조회
curl "http://localhost:5002/api/3d/cell-towers/260205?radio=LTE" | jq

# 예상 결과: GeoJSON FeatureCollection with ~100-500 towers
```

### 2. UI 테스트

1. **기지국 표시**
   - ☑ Show LTE Towers 체크
   - 지도에 파랑 타워 아이콘 표시 확인
   - 아이콘 수가 API 응답과 일치하는지 확인

2. **커버리지 반경**
   - ☑ Show Coverage Radius 체크
   - 각 타워 주변 반투명 원 표시 확인
   - 슬라이더로 반경 조정 (100m ~ 5km)

3. **기지국 정보 팝업**
   - 타워 아이콘 클릭
   - 팝업에 운영사, 타입, 반경, 샘플 수, 평균 신호 표시 확인

4. **성능 테스트**
   - 500개 기지국 표시 시 렌더링 성능 확인
   - 줌 인/아웃 시 부드러운 동작 확인

### 3. 통합 테스트

- 비행 경로 + 기지국 동시 표시
- 신호 강도 히트맵 + 기지국 오버레이
- 기지국 근처에서 신호 강도 높은지 시각적 확인

---

## 🚀 배포 가이드

### 1. OpenCellID API 키 발급

```bash
# 1. https://opencellid.org/register.php 가입
# 2. 무료 API 키 발급 (1일 1,000회 제한)
# 3. 환경 변수 설정

# macOS/Linux
export OPENCELLID_API_KEY="pk.xxxxxxxxxxxxxxxxxxxx"

# 또는 .env 파일에 추가
echo "OPENCELLID_API_KEY=pk.xxxxxxxxxxxxxxxxxxxx" >> analysis/.env
```

### 2. 백엔드 배포

```bash
cd /Users/dykim/dev/starlink/analysis

# 환경 변수 로드
source .env

# 서버 재시작
cd ..
./server.sh backend-restart
```

### 3. 프론트엔드 배포

```bash
# 자동 핫리로드 (개발 중)
# 코드 변경 후 자동 반영됨

# 또는 수동 재시작
./server.sh frontend-restart
```

---

## 📊 예상 성능 영향

### 데이터 크기
- **기지국 데이터**: 100개 ~ 500개 타워
- **GeoJSON 크기**: ~20KB ~ 100KB (gzip 압축)
- **Redis 캐시**: 24시간 TTL, API 호출 절약

### 렌더링 성능
- **100개 기지국**: 문제 없음
- **500개 기지국**: 클러스터링 없이 가능
- **1000개+ 기지국**: 클러스터링 권장

### API 사용량
- **초기 로드**: 1회 (24시간 캐시)
- **세션 변경**: 세션당 1회
- **일일 사용량**: ~10-50회 (1,000회 제한 충분)

---

## 🔮 향후 개선 사항

### Phase 5: 고급 분석 (선택사항)

1. **신호 품질 vs 기지국 거리 분석**
   - 각 비행 데이터 포인트에서 가장 가까운 기지국 찾기
   - 거리 vs RSRP 상관관계 그래프
   - 기지국 근처에서 신호 강도 높은지 검증

2. **기지국 핸드오버 시각화**
   - 비행 중 연결된 기지국 변경 추적
   - 핸드오버 지점 마커 표시
   - 핸드오버 빈도 분석

3. **3D 건물 데이터 추가** (데이터 있을 경우)
   - OSM Buildings 또는 Cesium 3D Tiles
   - 건물에 의한 신호 차폐 시각화

4. **다중 운영사 비교**
   - SK/KT/LGU+ 기지국 동시 표시
   - 운영사별 색상 구분
   - 커버리지 비교 분석

---

## 📚 참고 자료

### API 문서
- **OpenCellID API**: https://wiki.opencellid.org/wiki/API
- **OpenCellID 통계**: https://www.opencellid.org/stats.php
- **Cesium GeoJSON**: https://cesium.com/learn/cesiumjs/ref-doc/GeoJsonDataSource.html

### 관련 프로젝트
- **CellMapper**: https://www.cellmapper.net/ (크라우드소싱 기지국 지도)
- **Mozilla Location Service**: (종료됨, 아카이브 참고용)

### 한국 통신사
- **SK Telecom**: MNC 5
- **KT**: MNC 8
- **LG U+**: MNC 6

---

**작성일**: 2026-02-09
**작성자**: Claude + User
**버전**: 1.0
**상태**: 설계 완료, 구현 대기
