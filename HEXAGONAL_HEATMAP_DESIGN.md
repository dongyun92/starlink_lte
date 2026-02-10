# Hexagonal Heatmap 시각화 설계

## 🎯 목표
통신 품질 데이터를 H3 Hexagonal Grid로 집계하여 3D Cesium 지구본에 시각화

## 📚 참고 자료
- [H3 Hexagonal Grid System](https://h3geo.org/) - Uber의 계층적 육각형 그리드 시스템
- [Cesium CZML Polygon Specification](https://github.com/CesiumGS/cesium/blob/master/Apps/Sandcastle/gallery/CZML%20Polygon.html) - CZML 폴리곤 렌더링
- [H3 Python Library](https://uber.github.io/h3-py/) - Python H3 바인딩
- [통신 품질 시각화 Best Practices](https://towardsdatascience.com/constructing-hexagon-maps-with-h3-and-plotly-a-comprehensive-tutorial-8f37a91573bb/)

## 🔍 현재 시스템 분석

### 기존 히트맵 방식
1. **Point Style**: 각 GPS 포인트를 점으로 표시 (고밀도 데이터에 부적합)
2. **Voxel Style**: 3D 복셀 그리드 (직사각형, 공간 집계 비효율)

### Hexagonal의 장점
1. **균일한 거리 샘플링**: 육각형은 모든 이웃까지 거리가 동일
2. **시각적 부드러움**: 직사각형보다 자연스러운 커버리지
3. **통신 분야 표준**: 셀룰러 네트워크 커버리지 맵에서 널리 사용
4. **효율적인 공간 집계**: 계층적 구조로 다중 해상도 지원

---

## 🏗️ 시스템 설계

### 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │  UnifiedControlPanel                             │   │
│  │  ├─ Heatmap Style: [Point | Voxel | Hexagon]    │   │
│  │  ├─ H3 Resolution: [7 | 8 | 9 | 10]             │   │
│  │  └─ Aggregation: [Mean | Max | Min | Median]    │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │  CesiumViewer                                    │   │
│  │  └─ Load CZML → Render Hexagon Polygons         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓ HTTP GET
┌─────────────────────────────────────────────────────────┐
│                Backend (Flask + Python)                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │  /api/3d/heatmap/<session_id>                   │   │
│  │  ?mode=lte&style=hexagon&resolution=8           │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │  HexagonalHeatmapGenerator                       │   │
│  │  1. Load merged_data.csv (GPS + LTE/Starlink)   │   │
│  │  2. Convert GPS → H3 cells (h3.geo_to_h3)       │   │
│  │  3. Aggregate quality per cell (mean RSRP/SNR)  │   │
│  │  4. Get hexagon boundaries (h3.h3_to_geo_boundary)│  │
│  │  5. Generate CZML polygons with colors          │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 📐 H3 Resolution 선택

### Resolution vs Cell Size

| Resolution | Avg Hexagon Edge | Avg Hexagon Area | Use Case              |
|------------|------------------|------------------|-----------------------|
| 7          | 1.22 km          | 5.16 km²         | 도시 전체 커버리지    |
| **8**      | **461.35 m**     | **0.74 km²**     | **비행 경로 추천** ✅ |
| 9          | 174.38 m         | 0.10 km²         | 세밀한 품질 분석      |
| 10         | 65.91 m          | 0.015 km²        | 매우 정밀한 분석      |

**권장**: Resolution 8 (461m edge)
- 비행 고도 100-200m에서 적절한 샘플링
- 너무 세밀하지 않아 시각적으로 깔끔
- 성능과 정확도의 균형

---

## 🔧 구현 계획

### Phase 1: Backend - H3 CZML Generator

#### 1.1 Python 라이브러리 설치
```bash
pip install h3
```

#### 1.2 새 파일 생성: `analysis/api/threed/hexagonal_heatmap.py`

```python
import h3
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class HexagonalHeatmapGenerator:
    def __init__(self, resolution: int = 8):
        """
        H3 Hexagonal Heatmap Generator

        Args:
            resolution: H3 resolution (7-10 권장)
        """
        self.resolution = resolution

    def generate_czml(
        self,
        df: pd.DataFrame,
        mode: str,
        aggregation: str = 'mean'
    ) -> List[Dict]:
        """
        Generate CZML with hexagonal polygons

        Args:
            df: DataFrame with lat, lon, quality columns
            mode: 'lte', 'starlink', 'combined'
            aggregation: 'mean', 'max', 'min', 'median'

        Returns:
            CZML document
        """
        # 1. Convert GPS to H3 cells
        df['h3_cell'] = df.apply(
            lambda row: h3.geo_to_h3(row['latitude'], row['longitude'], self.resolution),
            axis=1
        )

        # 2. Aggregate quality per cell
        quality_col = self._get_quality_column(mode)
        grouped = df.groupby('h3_cell')[quality_col].agg(aggregation).reset_index()

        # 3. Generate CZML polygons
        czml = [self._create_document_packet()]

        for _, row in grouped.iterrows():
            h3_cell = row['h3_cell']
            quality_value = row[quality_col]

            # Get hexagon boundary
            boundary = h3.h3_to_geo_boundary(h3_cell, geo_json=True)

            # Convert to CZML polygon
            czml_polygon = self._create_hexagon_polygon(
                h3_cell, boundary, quality_value, mode
            )
            czml.append(czml_polygon)

        return czml

    def _create_hexagon_polygon(
        self,
        h3_cell: str,
        boundary: List[Tuple[float, float]],
        quality_value: float,
        mode: str
    ) -> Dict:
        """
        Create CZML polygon packet for hexagon

        Args:
            h3_cell: H3 cell ID
            boundary: List of (lon, lat) coordinates
            quality_value: Aggregated quality value
            mode: 'lte', 'starlink', 'combined'

        Returns:
            CZML polygon packet
        """
        # Flatten boundary for CZML (lon, lat, height sequence)
        positions = []
        for lon, lat in boundary:
            positions.extend([lon, lat, 0])  # Height = 0 (ground level)

        # Map quality to color
        color = self._quality_to_color(quality_value, mode)

        return {
            "id": f"hexagon_{h3_cell}",
            "polygon": {
                "positions": {
                    "cartographicDegrees": positions
                },
                "material": {
                    "solidColor": {
                        "color": {
                            "rgba": color
                        }
                    }
                },
                "outline": True,
                "outlineColor": {
                    "rgba": [255, 255, 255, 100]  # White outline
                },
                "outlineWidth": 1,
                "height": 0,
                "extrudedHeight": self._quality_to_height(quality_value, mode)
            }
        }

    def _quality_to_height(self, quality_value: float, mode: str) -> float:
        """
        Map quality value to extruded height (3D elevation)

        Args:
            quality_value: Quality metric value
            mode: 'lte', 'starlink', 'combined'

        Returns:
            Height in meters (0-200m)
        """
        if mode == 'lte':
            # LTE RSRP: -140 ~ -40 dBm
            # Normalize to 0-200m height
            normalized = (quality_value + 140) / 100  # 0-1 range
            return normalized * 200
        elif mode == 'starlink':
            # Starlink SNR: 0 ~ 15 dB
            normalized = quality_value / 15
            return normalized * 200
        else:
            # Combined quality score: 0-1
            return quality_value * 200

    def _quality_to_color(self, quality_value: float, mode: str) -> List[int]:
        """
        Map quality value to RGBA color (Jet colormap)

        Returns:
            RGBA list [R, G, B, A] (0-255 range)
        """
        # Implement Jet colormap (same as existing system)
        # Blue (poor) → Green → Yellow → Red (excellent)
        pass
```

#### 1.3 Flask Route 수정: `analysis/api/threed/routes.py`

```python
from .hexagonal_heatmap import HexagonalHeatmapGenerator

@api_3d_bp.route('/api/3d/heatmap/<session_id>', methods=['GET'])
def get_heatmap_czml(session_id: str):
    """
    Generate heatmap CZML data

    Query Parameters:
        mode: 'lte', 'starlink', 'combined'
        style: 'point', 'voxel', 'hexagon'  ← NEW
        resolution: H3 resolution (7-10, default 8)  ← NEW
        aggregation: 'mean', 'max', 'min', 'median'  ← NEW
    """
    mode = request.args.get('mode', 'combined')
    style = request.args.get('style', 'point')
    resolution = int(request.args.get('resolution', 8))
    aggregation = request.args.get('aggregation', 'mean')

    # Load data
    df = load_merged_data(session_id)

    if style == 'hexagon':
        # NEW: Hexagonal heatmap
        generator = HexagonalHeatmapGenerator(resolution=resolution)
        czml = generator.generate_czml(df, mode, aggregation)
    elif style == 'voxel':
        # Existing voxel implementation
        czml = generate_voxel_czml(df, mode)
    else:
        # Existing point implementation
        czml = generate_point_czml(df, mode)

    return jsonify(czml)
```

---

### Phase 2: Frontend - UI Controls

#### 2.1 TypeScript Types: `frontend/src/types/heatmap.ts`

```typescript
export type HeatmapStyle = 'point' | 'voxel' | 'hexagon';

export interface HeatmapOptions {
  style: HeatmapStyle;
  resolution?: number;  // H3 resolution (7-10)
  aggregation?: 'mean' | 'max' | 'min' | 'median';
}
```

#### 2.2 Control Panel Update: `frontend/src/components/UnifiedControlPanel.tsx`

```typescript
// Add hexagon controls
{heatmapStyle === 'hexagon' && (
  <div className="space-y-2">
    <label className="text-xs text-gray-300">H3 Resolution</label>
    <select
      value={h3Resolution}
      onChange={(e) => setH3Resolution(Number(e.target.value))}
      className="w-full px-2 py-1 bg-gray-700 text-white rounded text-xs"
    >
      <option value={7}>7 - Coarse (1.22 km)</option>
      <option value={8}>8 - Medium (461 m) ✓</option>
      <option value={9}>9 - Fine (174 m)</option>
      <option value={10}>10 - Very Fine (66 m)</option>
    </select>

    <label className="text-xs text-gray-300">Aggregation</label>
    <select
      value={aggregation}
      onChange={(e) => setAggregation(e.target.value)}
      className="w-full px-2 py-1 bg-gray-700 text-white rounded text-xs"
    >
      <option value="mean">Mean (Average)</option>
      <option value="max">Maximum</option>
      <option value="min">Minimum</option>
      <option value="median">Median</option>
    </select>
  </div>
)}
```

#### 2.3 API Call Update: `frontend/src/services/api.ts`

```typescript
export async function getHeatmapCZML(
  sessionId: string,
  mode: 'lte' | 'starlink' | 'combined',
  style: 'point' | 'voxel' | 'hexagon' = 'point',
  options?: {
    resolution?: number;
    aggregation?: 'mean' | 'max' | 'min' | 'median';
    flight_id?: number;
  }
): Promise<CZMLDocument> {
  const params = new URLSearchParams({ mode, style });

  if (options?.resolution) {
    params.append('resolution', options.resolution.toString());
  }

  if (options?.aggregation) {
    params.append('aggregation', options.aggregation);
  }

  if (options?.flight_id !== undefined) {
    params.append('flight_id', options.flight_id.toString());
  }

  const url = `${API_BASE_URL}/api/3d/heatmap/${sessionId}?${params.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch heatmap CZML: ${response.statusText}`);
  }

  return response.json();
}
```

---

## 🎨 시각화 예시

### LTE RSRP Hexagonal Heatmap (Resolution 8)

```
좋은 신호 (빨강, 높이 200m)
  🔴🔴🔴
 🔴🟠🟠🔴
🔴🟠🟡🟡🟠🔴
 🟠🟡🟢🟢🟡🟠
  🟡🟢🔵🔵🟢🟡
   🟢🔵🔵🟢
    🔵🔵  (파랑, 높이 0m)
나쁜 신호
```

### 3D View Features
- **Color**: 통신 품질 (Jet colormap)
- **Height**: 통신 품질 강도 (0-200m extrusion)
- **Opacity**: 반투명 (0.7 alpha)
- **Outline**: 흰색 경계선 (1px)

---

## 📊 성능 고려사항

### 데이터 볼륨 최적화

| Resolution | Approx. Cells | CZML Size | Cesium Performance |
|------------|---------------|-----------|---------------------|
| 7          | 50-100        | ~50 KB    | Excellent ⚡       |
| 8          | 200-400       | ~200 KB   | Good ✓             |
| 9          | 800-1600      | ~800 KB   | Moderate ⚠️        |
| 10         | 3000-6000     | ~3 MB     | Slow 🐌            |

**권장 Resolution**: 8 (200-400 cells, 200KB CZML)

### Redis Caching Strategy
```python
# Cache key format
cache_key = f"hexagon_heatmap:{session_id}:{mode}:{style}:{resolution}:{aggregation}"
cache_ttl = 3600  # 1 hour
```

---

## 🧪 테스트 계획

### 1. Backend 단위 테스트
```bash
pytest tests/test_hexagonal_heatmap.py -v
```

**테스트 케이스**:
- H3 cell 변환 정확도
- 집계 함수 (mean, max, min, median)
- CZML 폴리곤 구조 검증
- 색상 매핑 정확도

### 2. Frontend 통합 테스트
- UI 컨트롤 상태 관리
- CZML 로딩 및 렌더링
- 해상도 변경 시 재렌더링
- 성능 측정 (렌더링 시간)

### 3. 시각적 검증
- Resolution 7, 8, 9, 10 각각 렌더링
- LTE, Starlink, Combined 모드 확인
- 3D 높이 표현 정확도
- 색상 그라데이션 부드러움

---

## 📅 개발 일정

| Phase | Task | Duration | Priority |
|-------|------|----------|----------|
| 1     | Backend H3 Generator | 4 hours | 🔴 High |
| 2     | CZML Polygon 생성 | 3 hours | 🔴 High |
| 3     | Flask Route 통합 | 2 hours | 🔴 High |
| 4     | Frontend UI Controls | 3 hours | 🟡 Medium |
| 5     | API Integration | 2 hours | 🟡 Medium |
| 6     | Testing & Debugging | 4 hours | 🟢 Low |
| 7     | Performance Tuning | 2 hours | 🟢 Low |

**총 예상 시간**: 20 hours (약 3일)

---

## ✅ 완료 기준

1. ✅ H3 라이브러리 통합 및 테스트
2. ✅ Hexagonal CZML 생성 정상 작동
3. ✅ UI에서 "Hexagon" 스타일 선택 가능
4. ✅ Resolution 7-10 정상 렌더링
5. ✅ Aggregation (mean/max/min/median) 정확도
6. ✅ 3D Extrusion height 정상 표시
7. ✅ 기존 point/voxel 스타일 정상 작동 (호환성)
8. ✅ Redis 캐싱으로 <100ms 응답 시간

---

## 🔗 참고 링크

- [H3 Hexagonal Grid System](https://h3geo.org/)
- [H3 Python Documentation](https://uber.github.io/h3-py/)
- [Cesium CZML Polygon Guide](https://github.com/CesiumGS/cesium/blob/master/Apps/Sandcastle/gallery/CZML%20Polygon.html)
- [H3 Tutorial: Constructing Hexagon Maps](https://towardsdatascience.com/constructing-hexagon-maps-with-h3-and-plotly-a-comprehensive-tutorial-8f37a91573bb/)
- [Cellular Coverage Visualization Best Practices](https://poynting.tech/articles/antenna-faq/signal-strength-measure-rsrp-rsrq-and-sinr-reference-for-lte-cheat-sheet/)

---

## 📝 Notes

- Hexagonal heatmap은 통신 품질 분석의 업계 표준 방법입니다
- H3 시스템은 Uber에서 개발하여 오픈소스로 공개한 검증된 기술입니다
- Resolution 8 (461m edge)이 비행 경로 분석에 가장 적합합니다
- 3D extrusion을 통해 품질 강도를 시각적으로 직관적으로 표현할 수 있습니다
