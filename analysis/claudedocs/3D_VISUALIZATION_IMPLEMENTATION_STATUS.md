# 3D 비행 통신 품질 시각화 - 구현 현황 및 다음 단계

**업데이트**: 2026-02-06 19:00
**버전**: 1.0
**상태**: Phase 1-2 완료, Phase 3 진행 중

---

## ✅ 완료된 항목 (Phase 1-2)

### Phase 1: 기초 인프라 ✅
- ✅ Cesium.js 1.120.0 통합 (정적 로딩 방식)
- ✅ React 18 + TypeScript 프론트엔드
- ✅ Flask Backend API (3D 엔드포인트)
- ✅ CZML 데이터 생성 파이프라인
- ✅ PostgreSQL 세션 데이터 통합
- ✅ 서버 관리 스크립트 (server.sh)

### Phase 2: 기본 시각화 ✅
- ✅ 비행 경로 3D 표시 (Polyline)
- ✅ 시간 기반 애니메이션 (Timeline)
- ✅ 비행기 위치 마커 (Point)
- ✅ 세션 선택기 UI (SessionSelector)
- ✅ 자동 카메라 이동
- ✅ 카메라 모드 전환 (추적/자유 시점)

**기술 세부사항:**
```typescript
// 구현된 Entity 구조
{
  flight_path: Polyline,      // 전체 경로 (고정)
  aircraft: Point + Position   // 애니메이션 마커
}

// 카메라 모드
- Free View: 사용자 마우스 제어
- Track Mode: viewer.trackedEntity = aircraft
```

---

## 🚀 다음 구현: Phase 3 - 듀얼 통신 품질 시각화

### 개요
**목표**: LTE와 Starlink 통신 품질을 동시에 비교하여 시각화

**핵심 개념**:
- 하나의 비행 경로를 두 개의 평행한 선으로 표시
- LTE 경로: 신호 강도(RSSI) 기반 색상
- Starlink 경로: SNR/품질 기반 색상
- 사용자가 선택적으로 표시/숨김 가능

### 시각적 디자인

```
        비행기 (빨간 점)
              ↓
    ┌─────────────────────┐
    │                     │
    │  🔴 LTE Path        │  ← 빨강(약함) - 노랑(보통) - 녹색(강함)
    │     (좌측 5m)        │     RSSI < -100  |  -100~-80  |  > -80
    │                     │
    │  ─ ─ ─ ─ ─ ─ ─ ─   │  ← 중심 경로 (기준선)
    │                     │
    │  🔵 Starlink Path   │  ← 파랑(약함) - 하늘색(보통) - 흰색(강함)
    │     (우측 5m)        │     SNR < 5      |  5~10      |  > 10
    │                     │
    └─────────────────────┘
```

### 데이터 매핑

**LTE 신호 강도 (RSSI dBm)**:
| RSSI 범위 | 품질 | 색상 | RGB |
|-----------|------|------|-----|
| < -110 | 매우 나쁨 | 빨강 | (255, 0, 0) |
| -110 ~ -100 | 나쁨 | 주황 | (255, 127, 0) |
| -100 ~ -90 | 보통 | 노랑 | (255, 255, 0) |
| -90 ~ -80 | 좋음 | 연두 | (127, 255, 0) |
| > -80 | 매우 좋음 | 녹색 | (0, 255, 0) |

**Starlink 신호 품질 (SNR dB)**:
| SNR 범위 | 품질 | 색상 | RGB |
|----------|------|------|-----|
| < 3 | 매우 나쁨 | 진한 파랑 | (0, 0, 139) |
| 3 ~ 5 | 나쁨 | 파랑 | (0, 0, 255) |
| 5 ~ 8 | 보통 | 하늘색 | (0, 191, 255) |
| 8 ~ 12 | 좋음 | 청록 | (64, 224, 208) |
| > 12 | 매우 좋음 | 흰색 | (255, 255, 255) |

### 구현 세부사항

#### 1. Backend (CZML Generator)

**파일**: `analysis/api/threed/czml_generator.py`

```python
class CZMLGenerator:
    def generate(self, sample_rate: int = 1,
                 color_by: str = 'dual'):  # 'dual' 모드 추가
        """
        Generate CZML with dual paths for LTE and Starlink

        Args:
            color_by: 'altitude' | 'lte' | 'starlink' | 'dual'
        """
        czml = []
        czml.append(self._create_document_header(df))

        if color_by == 'dual':
            # 두 개의 polyline 생성
            czml.extend(self._create_dual_path_entities(df))
        else:
            czml.extend(self._create_flight_path_entity(df, color_by))

        return czml

    def _create_dual_path_entities(self, df) -> list:
        """
        Create separate polylines for LTE and Starlink with offset
        """
        entities = []

        # LTE Path (좌측 offset)
        lte_positions = self._build_offset_positions(df, offset=-0.00005)
        lte_colors = self._calculate_lte_colors(df)
        entities.append({
            "id": f"lte_path_{self.session_id}",
            "name": "LTE Signal Quality",
            "polyline": {
                "positions": {"cartographicDegrees": lte_positions},
                "width": 6,
                "material": self._build_gradient_material(lte_colors)
            }
        })

        # Starlink Path (우측 offset)
        starlink_positions = self._build_offset_positions(df, offset=0.00005)
        starlink_colors = self._calculate_starlink_colors(df)
        entities.append({
            "id": f"starlink_path_{self.session_id}",
            "name": "Starlink Signal Quality",
            "polyline": {
                "positions": {"cartographicDegrees": starlink_positions},
                "width": 6,
                "material": self._build_gradient_material(starlink_colors)
            }
        })

        # Aircraft entity (중앙)
        aircraft = self._create_aircraft_entity(df)
        entities.append(aircraft)

        return entities

    def _build_offset_positions(self, df, offset: float) -> list:
        """
        Build positions with longitude offset

        Args:
            offset: Longitude offset in degrees (~5-10 meters)
        """
        positions = []
        for _, row in df.iterrows():
            lon = row['longitude'] + offset
            lat = row['latitude']
            alt = row['altitude']
            positions.extend([lon, lat, alt])
        return positions

    def _calculate_lte_colors(self, df) -> np.ndarray:
        """
        Calculate colors based on LTE RSSI
        """
        rssi = df['lte_rssi'].fillna(-120)  # Default to very weak
        colors = np.zeros((len(rssi), 4), dtype=np.uint8)

        for i, value in enumerate(rssi):
            if value > -80:
                colors[i] = [0, 255, 0, 255]      # 녹색
            elif value > -90:
                colors[i] = [127, 255, 0, 255]    # 연두
            elif value > -100:
                colors[i] = [255, 255, 0, 255]    # 노랑
            elif value > -110:
                colors[i] = [255, 127, 0, 255]    # 주황
            else:
                colors[i] = [255, 0, 0, 255]      # 빨강

        return colors

    def _calculate_starlink_colors(self, df) -> np.ndarray:
        """
        Calculate colors based on Starlink SNR
        """
        snr = df['starlink_snr'].fillna(0)  # Default to no signal
        colors = np.zeros((len(snr), 4), dtype=np.uint8)

        for i, value in enumerate(snr):
            if value > 12:
                colors[i] = [255, 255, 255, 255]   # 흰색
            elif value > 8:
                colors[i] = [64, 224, 208, 255]    # 청록
            elif value > 5:
                colors[i] = [0, 191, 255, 255]     # 하늘색
            elif value > 3:
                colors[i] = [0, 0, 255, 255]       # 파랑
            else:
                colors[i] = [0, 0, 139, 255]       # 진한 파랑

        return colors
```

#### 2. Frontend (UI Controls)

**파일**: `frontend/src/components/DataLayerControl.tsx` (신규)

```typescript
interface DataLayerControlProps {
  onLayerToggle: (layer: 'lte' | 'starlink', visible: boolean) => void;
}

export default function DataLayerControl({ onLayerToggle }: DataLayerControlProps) {
  const [layers, setLayers] = useState({
    lte: true,
    starlink: true,
  });

  const handleToggle = (layer: 'lte' | 'starlink') => {
    const newState = !layers[layer];
    setLayers({ ...layers, [layer]: newState });
    onLayerToggle(layer, newState);
  };

  return (
    <div className="absolute top-32 right-4 z-10 bg-gray-900/95 p-4 rounded-lg shadow-lg">
      <h3 className="text-white font-bold mb-3">📡 데이터 표시</h3>

      {/* LTE Toggle */}
      <label className="flex items-center gap-2 mb-2 cursor-pointer">
        <input
          type="checkbox"
          checked={layers.lte}
          onChange={() => handleToggle('lte')}
          className="w-4 h-4"
        />
        <span className="text-white">🔴 LTE 신호 품질</span>
      </label>

      {/* Starlink Toggle */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={layers.starlink}
          onChange={() => handleToggle('starlink')}
          className="w-4 h-4"
        />
        <span className="text-white">🔵 Starlink 신호 품질</span>
      </label>

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-gray-700">
        <div className="text-xs text-gray-400 mb-2">범례:</div>
        <div className="text-xs text-white space-y-1">
          <div>🔴 빨강: 약함 | 🟡 노랑: 보통 | 🟢 녹색: 강함</div>
          <div>🔵 파랑: 약함 | 🔷 하늘: 보통 | ⚪ 흰색: 강함</div>
        </div>
      </div>
    </div>
  );
}
```

**파일**: `frontend/src/components/CesiumViewer.tsx` (업데이트)

```typescript
export default function CesiumViewer({ ... }: CesiumViewerProps) {
  const lteEntityRef = useRef<any>(null);
  const starlinkEntityRef = useRef<any>(null);

  const handleLayerToggle = (layer: 'lte' | 'starlink', visible: boolean) => {
    if (layer === 'lte' && lteEntityRef.current) {
      lteEntityRef.current.show = visible;
      console.log(`🔴 LTE layer: ${visible ? 'visible' : 'hidden'}`);
    } else if (layer === 'starlink' && starlinkEntityRef.current) {
      starlinkEntityRef.current.show = visible;
      console.log(`🔵 Starlink layer: ${visible ? 'visible' : 'hidden'}`);
    }
  };

  useEffect(() => {
    // Load CZML with dual paths
    const czmlData = await getCZMLData(selectedSessionId, {
      sample_rate: 1,
      color_by: 'dual',  // 듀얼 모드 활성화
    });

    // Find and store entity references
    const entities = dataSource.entities.values;
    lteEntityRef.current = entities.find((e: any) =>
      e.id.includes('lte_path')
    );
    starlinkEntityRef.current = entities.find((e: any) =>
      e.id.includes('starlink_path')
    );
  }, [selectedSessionId]);

  return (
    <div className={className}>
      <DataLayerControl onLayerToggle={handleLayerToggle} />
      <div ref={viewerRef} className="w-full h-full" />
    </div>
  );
}
```

#### 3. API Routes (업데이트)

**파일**: `analysis/api/threed/routes.py`

```python
@api_3d_bp.route('/czml/<session_id>', methods=['GET'])
def get_czml_data(session_id):
    """
    Get CZML data with optional dual path visualization

    Query params:
        - sample_rate: int (default 1)
        - color_by: str ('altitude' | 'lte' | 'starlink' | 'dual')
    """
    sample_rate = request.args.get('sample_rate', 1, type=int)
    color_by = request.args.get('color_by', 'altitude', type=str)

    # Validate color_by parameter
    valid_modes = ['altitude', 'lte', 'starlink', 'dual']
    if color_by not in valid_modes:
        return jsonify({
            'error': f'Invalid color_by. Must be one of: {valid_modes}'
        }), 400

    generator = CZMLGenerator(session_id)
    czml_data = generator.generate(
        sample_rate=sample_rate,
        color_by=color_by
    )

    return jsonify(czml_data), 200
```

### 데이터 처리 고려사항

#### 데이터 누락 처리
```python
# LTE 데이터가 없는 경우
df['lte_rssi'].fillna(-120)  # 매우 약한 신호로 표시 (회색)

# Starlink 데이터가 없는 경우
df['starlink_snr'].fillna(0)  # 신호 없음 (검정)
```

#### 성능 최적화
```python
# 너무 많은 포인트는 샘플링
if len(df) > 10000:
    df = df.iloc[::sample_rate]  # 균등 샘플링
```

### 완료 기준

- [ ] LTE 경로가 RSSI 값에 따라 색상으로 표시됨
- [ ] Starlink 경로가 SNR 값에 따라 색상으로 표시됨
- [ ] 두 경로가 평행하게 나란히 표시됨
- [ ] 체크박스로 각 레이어를 개별적으로 표시/숨김 가능
- [ ] 범례가 색상-품질 매핑을 명확히 표시
- [ ] 데이터가 없는 구간도 적절히 처리됨

### 테스트 시나리오

1. **기본 시나리오**
   - 페이지 로드 → 두 경로 모두 표시
   - LTE 체크박스 해제 → LTE 경로만 숨김
   - Starlink 체크박스 해제 → Starlink 경로만 숨김

2. **데이터 품질 비교**
   - 빨간 LTE 경로 + 파란 Starlink 경로 = 둘 다 신호 약함
   - 녹색 LTE 경로 + 파란 Starlink 경로 = LTE는 좋지만 Starlink 약함
   - 빨간 LTE 경로 + 흰색 Starlink 경로 = LTE 약하지만 Starlink 좋음

3. **성능 테스트**
   - 10,000 포인트 데이터에서도 60 FPS 유지
   - 레이어 토글 시 즉각 반응 (< 100ms)

---

## 📋 구현 체크리스트

### Backend
- [ ] `_create_dual_path_entities()` 메서드 구현
- [ ] `_build_offset_positions()` 메서드 구현
- [ ] `_calculate_lte_colors()` 메서드 구현
- [ ] `_calculate_starlink_colors()` 메서드 구현
- [ ] `_build_gradient_material()` 메서드 구현
- [ ] API 라우트에 'dual' 모드 파라미터 추가
- [ ] 테스트: curl로 API 응답 확인

### Frontend
- [ ] `DataLayerControl.tsx` 컴포넌트 생성
- [ ] `CesiumViewer.tsx`에 레이어 토글 로직 추가
- [ ] Entity ref 관리 (lte, starlink)
- [ ] API 호출 시 `color_by: 'dual'` 파라미터 전달
- [ ] CSS 스타일링 (체크박스, 범례)
- [ ] 테스트: 브라우저에서 동작 확인

### 테스트
- [ ] LTE만 표시
- [ ] Starlink만 표시
- [ ] 둘 다 표시 (기본)
- [ ] 데이터 누락 시나리오
- [ ] 성능 테스트 (10K+ 포인트)

---

## 📊 예상 결과

### Before (현재)
```
단일 녹색-노란색 경로만 표시
고도 정보만 확인 가능
```

### After (구현 후)
```
🔴 LTE 경로: 어디서 LTE 신호가 약했는지 빨간색으로 표시
🔵 Starlink 경로: 어디서 Starlink 신호가 좋았는지 흰색으로 표시
→ 한눈에 두 통신 방식의 품질 비교 가능
→ 특정 구간에서 어떤 통신이 더 나은지 즉시 파악
```

---

## 🔄 다음 단계 (Phase 4 이후)

구현 완료 후 고려할 추가 기능:

1. **실시간 데이터 패널**
   - 타임라인 재생 시 현재 위치의 LTE/Starlink 수치 표시
   - 예상 시간: 1시간

2. **LTE 기지국 마커**
   - 연결된 기지국 위치 표시
   - 예상 시간: 2시간

3. **통계 대시보드**
   - LTE vs Starlink 평균 품질 비교
   - 구간별 통신 품질 통계
   - 예상 시간: 2시간

---

**작성자**: Claude Sonnet 4.5
**다음 리뷰**: Phase 3 구현 완료 후
