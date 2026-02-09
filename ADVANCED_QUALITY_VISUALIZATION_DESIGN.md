# Advanced Quality Visualization Design
**날짜**: 2026-02-09
**프로젝트**: Starlink Flight Analysis 3D Visualization

---

## 📋 요구사항 요약

1. **중복 필드 자동 선택**: 같은 데이터가 여러 필드에 있으면 실제 값이 있는 것만 사용
2. **커스텀 종합 품질 스코어**: 사용자가 지표를 다중 선택하고 가중치 조절 가능
3. **개별 지표 시각화**: 모든 데이터 품질 지표를 Path Color Mode에서 선택 가능
4. **위성 방향 + 신호품질 관계**: 방위각/고도각과 신호품질의 관계 시각화
5. **다양한 탐색 방법**: 사용자가 여러 방식으로 데이터 분석 가능

---

## 🎨 UI/UX 설계

### 1. Path Color Mode 대폭 확장

#### **현재 구조** (5개 모드)
```
- Altitude
- Speed
- LTE Quality ▼
  - Combined (RSRP + SINR + RSRQ)
  - RSRP
  - SINR
  - RSRQ
- Starlink Quality ▼
  - Combined (SNR + Latency)
  - SNR
  - Latency
```

#### **신규 구조** (카테고리별 그룹핑)
```
📍 Basic Metrics
  - Altitude
  - Speed

📡 LTE Quality
  - 🌟 Custom Combined (사용자 정의)
  - Combined (RSRP 30% + SINR 50% + RSRQ 20%)
  - RSRP (Signal Strength)
  - SINR (Signal Quality)
  - RSRQ (Overall Quality)
  - RSSI (Signal Strength - fallback)

🛰️ Starlink Quality
  - 🌟 Custom Combined (사용자 정의)
  - Combined (Auto: SNR + Latency + Packet Loss + Obstruction)
  - SNR (Signal to Noise)
  - Latency (Round-trip)
  - Packet Loss (Drop Rate)
  - Throughput Down (Download Speed)
  - Throughput Up (Upload Speed)
  - Obstruction (Blocked Signal)
  - Connection Uptime

🎯 Satellite Direction
  - Azimuth + Quality (방위각 + 신호품질 복합)
  - Elevation + Quality (고도각 + 신호품질 복합)
  - Direction Vector (3D 화살표로 방향 표시)
```

---

### 2. Custom Quality Score Builder (새로운 기능)

#### **UI 위치**: Modal/Sidebar Panel
#### **트리거**: "Custom Combined" 선택 시 자동 열림 또는 "⚙️ Customize" 버튼

#### **UI 구성**:
```
┌─────────────────────────────────────────────┐
│  🎛️ Custom Quality Score Builder           │
├─────────────────────────────────────────────┤
│                                             │
│  Select Metrics (at least 1):               │
│                                             │
│  ☑ SNR (Signal to Noise)         [40%]     │
│     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│                                             │
│  ☑ Latency                        [25%]     │
│     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│                                             │
│  ☑ Packet Loss                    [20%]     │
│     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│                                             │
│  ☑ Obstruction                    [15%]     │
│     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│                                             │
│  ☐ Throughput Down                 [0%]     │
│     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│                                             │
│  ☐ Throughput Up                   [0%]     │
│     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│                                             │
│  ☐ Connection Uptime               [0%]     │
│     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │
│                                             │
│  ─────────────────────────────────────      │
│  Total Weight: 100% ✅                      │
│                                             │
│  [Auto-normalize] ☑                         │
│  (자동으로 100%가 되도록 조정)               │
│                                             │
│  ┌──────────────┐  ┌──────────────┐        │
│  │   Cancel     │  │   Confirm ✓  │        │
│  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────┘
```

#### **기능**:
1. **체크박스**: 지표 선택/해제
2. **슬라이더**: 가중치 조절 (0-100%)
3. **Auto-normalize**: 체크 시 자동으로 총합 100%로 조정
4. **Confirm**: 설정 적용 → 백엔드에 커스텀 스코어 요청

---

### 3. 위성 방향 + 신호품질 시각화

#### **옵션 A: 2D 극좌표 투영** (간단)
- 방위각(0-360°)을 원의 각도로 매핑
- 고도각(0-90°)을 반지름으로 매핑
- 신호품질을 색상으로 표시 (Red→Green)
- 장점: 구현 쉬움, 2D 오버레이 가능
- 단점: 3D 공간감 부족

#### **옵션 B: 3D 방향 벡터** (추천)
- Cesium 3D polyline/arrow로 위성 방향 표시
- 화살표 색상 = 신호품질
- 화살표 길이 = 신호 강도
- 장점: 3D 공간에서 직관적, Cesium과 완벽 통합
- 단점: 구현 복잡도 중간

#### **옵션 C: 히트맵 오버레이** (고급)
- 방위각/고도각을 2D 그리드로 변환
- 각 그리드 셀에 평균 신호품질 표시
- 장점: 패턴 분석 용이
- 단점: 별도 차트 라이브러리 필요

**추천**: **옵션 B (3D 방향 벡터)** - Cesium의 강점 활용

---

## 🔧 백엔드 구현 계획

### 1. 데이터 필드 자동 선택 로직

```python
def _get_best_available_field(df, field_candidates: list) -> str:
    """
    중복 필드 중 실제 데이터가 있는 것 선택

    Args:
        df: DataFrame
        field_candidates: ['starlink_snr', 'starlink_raw_status.snr']

    Returns:
        실제 데이터가 있는 필드명
    """
    for field in field_candidates:
        if field in df.columns and not df[field].isna().all():
            return field
    return None
```

### 2. Starlink 개별 지표 모드 추가

#### **czml_generator.py 수정**:
```python
# 새로운 color_by 모드들
'starlink_packet_loss'        # starlink_ping_drop_rate
'starlink_throughput_down'    # starlink_downlink_throughput_bps
'starlink_throughput_up'      # starlink_uplink_throughput_bps
'starlink_obstruction'        # starlink_raw_status.fraction_obstructed
'starlink_uptime'             # starlink_uptime
'starlink_azimuth_quality'    # azimuth + quality 복합
'starlink_elevation_quality'  # elevation + quality 복합
```

#### **정규화 범위**:
```python
# Domain-specific normalization
'starlink_packet_loss':      0 ~ 1 (0=good, 1=bad, INVERTED!)
'starlink_throughput_down':  0 ~ 100 Mbps (higher=better)
'starlink_throughput_up':    0 ~ 10 Mbps (higher=better)
'starlink_obstruction':      0 ~ 1 (0=good, 1=bad, INVERTED!)
'starlink_uptime':           0 ~ max(uptime) (higher=better)
```

### 3. Custom Combined Score 계산

```python
def _calculate_starlink_custom_combined(self, df, selected_metrics: dict) -> np.ndarray:
    """
    사용자 정의 종합 품질 스코어

    Args:
        df: DataFrame
        selected_metrics: {
            'snr': 0.40,
            'latency': 0.25,
            'packet_loss': 0.20,
            'obstruction': 0.15
        }

    Returns:
        Combined score (0-1)
    """
    combined = np.zeros(len(df))

    for metric, weight in selected_metrics.items():
        if metric == 'snr':
            values = df['starlink_snr'].values
            normalized = np.clip((values - 0) / (15 - 0), 0, 1)
        elif metric == 'latency':
            values = df['starlink_latency'].values
            normalized = np.clip((values - 200) / (0 - 200), 0, 1)  # INVERTED
        # ... 다른 지표들

        combined += weight * normalized

    return combined
```

### 4. 위성 방향 시각화 데이터

#### **새로운 CZML 생성 함수**:
```python
def create_satellite_direction_czml(self, df) -> list:
    """
    위성 방향 벡터 CZML 생성

    Returns:
        CZML with polyline arrows showing satellite direction
    """
    entities = []

    for idx, row in df.iterrows():
        azimuth = row['starlink_azimuth']
        elevation = row['starlink_elevation']
        quality = row['starlink_snr']  # or custom score

        # 3D 벡터 계산 (구면 좌표 → 직교 좌표)
        arrow_length = 1000  # meters
        dx = arrow_length * np.cos(np.radians(elevation)) * np.sin(np.radians(azimuth))
        dy = arrow_length * np.cos(np.radians(elevation)) * np.cos(np.radians(azimuth))
        dz = arrow_length * np.sin(np.radians(elevation))

        # 색상: 신호품질에 따라
        color = self._get_quality_color(quality)

        # CZML polyline entity
        entity = {
            "id": f"sat_direction_{idx}",
            "polyline": {
                "positions": {
                    "cartographicDegrees": [
                        lon, lat, alt,
                        lon + dx, lat + dy, alt + dz
                    ]
                },
                "material": {"solidColor": {"color": {"rgba": color}}},
                "width": 3
            }
        }
        entities.append(entity)

    return entities
```

---

## 🎯 프론트엔드 구현 계획

### 1. 새로운 컴포넌트

#### **CustomQualityBuilder.tsx** (새로 생성)
```typescript
interface MetricOption {
  id: string;
  label: string;
  enabled: boolean;
  weight: number;
  description: string;
}

interface CustomQualityBuilderProps {
  type: 'lte' | 'starlink';
  onConfirm: (metrics: Record<string, number>) => void;
  onCancel: () => void;
}

export const CustomQualityBuilder: React.FC<CustomQualityBuilderProps> = ({
  type,
  onConfirm,
  onCancel
}) => {
  const [metrics, setMetrics] = useState<MetricOption[]>([...]);
  const [autoNormalize, setAutoNormalize] = useState(true);

  // 슬라이더 변경 시 auto-normalize
  const handleWeightChange = (id: string, weight: number) => {
    if (autoNormalize) {
      // 자동으로 100%가 되도록 다른 지표들 조정
      normalizeWeights(id, weight);
    } else {
      setMetricWeight(id, weight);
    }
  };

  // Confirm 버튼
  const handleConfirm = () => {
    const selectedMetrics = metrics
      .filter(m => m.enabled)
      .reduce((acc, m) => ({ ...acc, [m.id]: m.weight / 100 }), {});
    onConfirm(selectedMetrics);
  };

  return (
    <div className="modal">
      {/* UI 구현 */}
    </div>
  );
};
```

### 2. UnifiedControlPanel 확장

```typescript
// Path Color Mode에 새로운 옵션들 추가
type PathColorMode =
  | 'altitude' | 'speed'
  | 'lte_quality_combined' | 'lte_quality_custom' | 'lte_rsrp' | ...
  | 'starlink_quality_combined' | 'starlink_quality_custom' | 'starlink_snr' | ...
  | 'starlink_packet_loss' | 'starlink_throughput_down' | ...
  | 'starlink_azimuth_quality' | 'starlink_elevation_quality';

// Custom Combined 선택 시 Builder 열기
const [showCustomBuilder, setShowCustomBuilder] = useState(false);

if (pathColorMode === 'starlink_quality_custom') {
  setShowCustomBuilder(true);
}
```

### 3. API 타입 확장

```typescript
// api.ts
export async function getCZMLData(
  sessionId: string,
  options?: {
    sample_rate?: number;
    color_by?: PathColorMode;
    custom_metrics?: Record<string, number>;  // 새로운 옵션
    flight_id?: number;
  }
): Promise<CZMLDocument> {
  // ...
}
```

---

## 📊 데이터 품질 지표 우선순위

### **Tier 1: 핵심 지표** (반드시 구현)
1. SNR (Signal to Noise)
2. Latency
3. Packet Loss
4. Obstruction

### **Tier 2: 중요 지표** (우선 구현)
5. Throughput Down
6. Throughput Up
7. Connection Uptime

### **Tier 3: 고급 지표** (추후 구현)
8. Azimuth + Quality
9. Elevation + Quality
10. Direction Vector

---

## 🚀 구현 단계

### **Phase 1: 개별 지표 시각화** (1-2일)
- [ ] Backend: Starlink 개별 지표 color_by 모드 추가
- [ ] Backend: 중복 필드 자동 선택 로직
- [ ] Backend: 도메인별 정규화 범위 설정
- [ ] Frontend: UnifiedControlPanel에 새 옵션 추가
- [ ] Frontend: API 타입 확장
- [ ] Test: 모든 개별 지표 정상 작동 확인

### **Phase 2: Custom Quality Builder** (2-3일)
- [ ] Frontend: CustomQualityBuilder 컴포넌트 생성
- [ ] Frontend: 체크박스 + 슬라이더 UI
- [ ] Frontend: Auto-normalize 로직
- [ ] Backend: Custom combined score 계산 엔드포인트
- [ ] Backend: 선택된 지표만 사용하여 계산
- [ ] Test: 다양한 조합 테스트

### **Phase 3: 위성 방향 시각화** (2-3일)
- [ ] Backend: Satellite direction CZML 생성
- [ ] Backend: Azimuth/Elevation → 3D vector 변환
- [ ] Frontend: Direction vector toggle control
- [ ] Frontend: 방향 화살표 Cesium 렌더링
- [ ] Test: 방향과 품질의 관계 시각 확인

---

## 🎨 색상 및 스타일 가이드

### **Traffic Light Colormap** (품질 지표)
- 0-20%: 빨강 (Very Bad)
- 20-40%: 주황 (Bad)
- 40-60%: 노랑 (Medium)
- 60-80%: 연두 (Good)
- 80-100%: 초록 (Excellent)

### **Inverted Metrics** (낮을수록 좋음)
- Latency: 200ms(bad) → 0ms(good)
- Packet Loss: 1.0(bad) → 0.0(good)
- Obstruction: 1.0(bad) → 0.0(good)

---

## 💡 추가 아이디어

### **차트 라이브러리 통합** (선택사항)
- Recharts 또는 Chart.js 추가
- 시계열 차트로 신호 품질 트렌드 분석
- 방위각/고도각 vs 품질 scatter plot

### **통계 요약 패널**
- 평균, 최소, 최대, 표준편차
- 데이터 커버리지 (Non-NaN %)
- 품질 분포 히스토그램

### **프리셋 저장**
- Custom Quality 설정 저장/불러오기
- LocalStorage 또는 서버 저장

---

## ✅ Success Criteria

1. ✅ 모든 Starlink 개별 지표를 Path Color로 시각화 가능
2. ✅ 사용자가 자유롭게 지표 조합 + 가중치 설정 가능
3. ✅ Custom Combined Score가 실시간으로 계산되어 경로에 표시
4. ✅ 위성 방향과 신호품질의 관계를 3D로 확인 가능
5. ✅ 중복 필드는 자동으로 유효한 데이터만 사용
6. ✅ UI가 직관적이고 사용하기 쉬움

---

**다음 단계**: 설계 검토 후 Phase 1 구현 시작
