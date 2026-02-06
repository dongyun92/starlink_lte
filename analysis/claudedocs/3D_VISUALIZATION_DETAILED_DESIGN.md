# 3D 비행 통신 품질 시각화 시스템 상세 설계서

**작성일**: 2026-02-06
**프로젝트**: Starlink/LTE 통신 품질 분석 플랫폼 - 3D 시각화 모듈
**버전**: 1.0
**상태**: 설계 단계

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [기술 스택 결정](#3-기술-스택-결정)
4. [데이터 플로우](#4-데이터-플로우)
5. [컴포넌트 구조](#5-컴포넌트-구조)
6. [단계별 구현 계획](#6-단계별-구현-계획)
7. [위험 요소 및 대응책](#7-위험-요소-및-대응책)
8. [성능 요구사항](#8-성능-요구사항)
9. [테스트 전략](#9-테스트-전략)
10. [배포 계획](#10-배포-계획)

---

## 1. 프로젝트 개요

### 1.1 목표

**핵심 목표**: 비행체의 통신 품질 데이터를 3D 지구본 환경에서 시간에 따라 시각화하여 직관적인 분석 환경 제공

**구체적 목표**:
- ✅ 비행 경로를 3D 지구본에 고도별 색상으로 표시
- ✅ LTE 기지국 위치 및 커버리지 시각화
- ✅ Starlink 위성 궤도 및 통신 링크 표시
- ✅ 시간 슬라이더를 통한 비행 재생 기능
- ✅ 신호 세기 히트맵 오버레이
- ✅ 실시간/준실시간 데이터 스트리밍 지원

### 1.2 사용자 스토리

**AS-IS (현재 2D 시스템)**:
```
사용자: "비행 경로를 Folium 2D 지도에서 보고 있지만,
        고도 변화와 통신 품질의 관계를 파악하기 어렵습니다."
```

**TO-BE (3D 시스템)**:
```
사용자: "3D 지구본에서 비행 경로를 회전하며 관찰하고,
        고도에 따른 신호 세기 변화를 입체적으로 확인합니다.
        Starlink 위성과의 연결 상태를 실시간으로 추적합니다."
```

### 1.3 성공 기준

| 항목 | 지표 | 목표값 |
|------|------|--------|
| **성능** | 초기 로딩 시간 | < 3초 |
| **성능** | 60 FPS 유지 | 10,000 데이터포인트 |
| **UX** | 사용자 학습 시간 | < 5분 |
| **기능** | 비행 재생 정확도 | 99% |
| **안정성** | 크래시 없는 연속 실행 | 1시간+ |

---

## 2. 시스템 아키텍처

### 2.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     Client (Browser)                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │           React 18 + TypeScript App                  │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │ UI Layer │  │ 3D Viewer│  │ Control Panel    │  │  │
│  │  │ (Radix)  │  │ (Cesium) │  │ (Timeline, etc)  │  │  │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │   State Management (Zustand)                 │   │  │
│  │  │   - Viewer State                             │   │  │
│  │  │   - Flight Data                              │   │  │
│  │  │   - Time Control                             │   │  │
│  │  │   - Layer Visibility                         │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │   Data Layer                                 │   │  │
│  │  │   - REST API Client                          │   │  │
│  │  │   - WebSocket Client (실시간)                │   │  │
│  │  │   - CZML Parser                              │   │  │
│  │  │   - Data Cache (IndexedDB)                   │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/WS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Backend (Flask/Python)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │   Flask App (Port 5002)                              │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────────────────┐ │  │
│  │  │ REST API│  │ WS Server│  │ 3D Data Endpoints   │ │  │
│  │  │ (기존)  │  │ (신규)  │  │ /api/3d/flights     │ │  │
│  │  └─────────┘  └─────────┘  │ /api/3d/czml        │ │  │
│  │                             │ /api/3d/stations    │ │  │
│  │                             │ /api/3d/satellites  │ │  │
│  │                             └──────────────────────┘ │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │   Data Processing                            │   │  │
│  │  │   - ULG Parser (기존)                        │   │  │
│  │  │   - CZML Generator (신규)                    │   │  │
│  │  │   - TLE Parser (위성 궤도, 신규)             │   │  │
│  │  │   - Interpolation (데이터 보간)             │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ DB Query
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data Storage                                │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  PostgreSQL │  │  File Storage│  │  External APIs   │  │
│  │  (비행 데이터)│  │  (ULG, CZML) │  │  (Starlink TLE)  │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 3D 렌더링 파이프라인

```
┌─────────────────────────────────────────────────────────────┐
│                  Cesium.js 렌더링 파이프라인                  │
└─────────────────────────────────────────────────────────────┘

1. 데이터 로드
   ├─ CZML 로드 (비행 경로, 시간 데이터)
   ├─ GeoJSON 로드 (기지국 위치)
   └─ TLE 데이터 로드 (위성 궤도)

2. Scene 구성
   ├─ Globe (Cesium World Terrain)
   ├─ ImageryLayer (Bing Maps 또는 OSM)
   ├─ 3D Buildings (OSM Buildings)
   └─ Atmosphere & Lighting

3. Entity 생성
   ├─ Flight Path (PolylineGraphics + 고도 색상)
   ├─ Aircraft Model (Billboard + 3D Model)
   ├─ Base Stations (Point + Billboard)
   ├─ Satellites (Point + Orbit Path)
   └─ Communication Links (PolylineGraphics)

4. 애니메이션
   ├─ Clock (JulianDate 기반)
   ├─ SampledPositionProperty (보간)
   ├─ TimeIntervalCollection (시간별 속성)
   └─ Camera Tracking (Follow mode)

5. 인터랙션
   ├─ Mouse/Touch Handlers
   ├─ Entity Selection
   ├─ Tooltip/Popup
   └─ Time Slider Control

6. 최적화
   ├─ Frustum Culling (시야 밖 제거)
   ├─ Level of Detail (거리별 세부도)
   ├─ Batching (여러 Entity 통합)
   └─ Data Streaming (필요한 데이터만)
```

---

## 3. 기술 스택 결정

### 3.1 최종 선정 기술 스택

| 레이어 | 기술 | 버전 | 선정 이유 |
|--------|------|------|-----------|
| **프론트엔드 프레임워크** | React | 18.x | 컴포넌트 재사용, 생태계 |
| **언어** | TypeScript | 5.x | 타입 안정성, IDE 지원 |
| **빌드 도구** | Vite | 5.x | 빠른 개발 서버, HMR |
| **3D 라이브러리** | Cesium.js | 1.120+ | 지리공간 전문, 항공 적합 |
| **상태 관리** | Zustand | 4.x | 간단한 API, 성능 |
| **UI 컴포넌트** | Radix UI | 1.x | 접근성, 커스터마이징 |
| **스타일링** | Tailwind CSS | 3.x | 유틸리티 우선, 빠른 개발 |
| **백엔드** | Flask | 3.x | 기존 시스템 연계 |
| **WebSocket** | Flask-SocketIO | 5.x | 실시간 통신 |
| **데이터베이스** | PostgreSQL | 15+ | 기존 시스템 |
| **배포** | Docker | 최신 | 컨테이너화 |

### 3.2 의사결정 근거

#### 3.2.1 왜 Cesium.js인가?

**장점**:
- ✅ **항공 전문성**: FAA ActiveFlight 프로젝트 사용
- ✅ **CZML 포맷**: 시계열 데이터 애니메이션 최적화
- ✅ **Terrain**: Cesium World Terrain 무료 제공
- ✅ **위성 추적**: TLE 데이터 기반 위성 궤도 계산
- ✅ **생태계**: 풍부한 플러그인, 활발한 커뮤니티

**단점 및 완화 방안**:
- ⚠️ 번들 크기 (1.4MB) → Code splitting, CDN 사용
- ⚠️ 학습 곡선 → 공식 튜토리얼, 예제 코드 활용

#### 3.2.2 왜 React + TypeScript인가?

- **React**: 기존 웹 대시보드와 기술 스택 통일
- **TypeScript**: Cesium API 타입 정의 제공, 런타임 오류 감소
- **Vite**: 개발 서버 시작 < 1초, HMR < 100ms

#### 3.2.3 왜 Flask-SocketIO인가?

- **기존 Flask 앱 확장**: 새 서버 불필요
- **양방향 통신**: 실시간 비행 데이터 스트리밍
- **간단한 API**: Socket.IO 클라이언트와 호환

---

## 4. 데이터 플로우

### 4.1 정적 데이터 로드 플로우

```
[사용자 액션: 비행 세션 선택]
        ↓
[Frontend: API 요청 (GET /api/3d/flights/{session_id})]
        ↓
[Backend: PostgreSQL 쿼리]
        ↓
[Backend: CZML 생성]
  - 비행 경로 (latitude, longitude, altitude, timestamp)
  - 고도별 색상 매핑
  - 속도/방향 데이터
        ↓
[Backend: 응답 (CZML JSON)]
        ↓
[Frontend: CZML 파싱]
        ↓
[Cesium: Entity 생성]
  - PolylineGraphics (경로)
  - Billboard (항공기)
  - SampledPositionProperty (보간)
        ↓
[Cesium: 렌더링]
```

### 4.2 실시간 데이터 스트리밍 플로우

```
[Backend: 라즈베리파이에서 LTE 데이터 수신]
        ↓
[Backend: WebSocket 브로드캐스트]
  Event: 'flight_update'
  Data: { position, altitude, lte_rsrp, starlink_latency, timestamp }
        ↓
[Frontend: WebSocket 수신]
        ↓
[Frontend: Zustand 상태 업데이트]
        ↓
[Cesium: Entity 업데이트]
  - 위치 업데이트 (SampledPositionProperty.addSample)
  - 색상 업데이트 (신호 세기 반영)
  - 카메라 추적 (선택 시)
        ↓
[Cesium: 리렌더링 (requestAnimationFrame)]
```

### 4.3 CZML 데이터 구조

```json
[
  {
    "id": "document",
    "version": "1.0",
    "name": "Flight QoS Visualization",
    "clock": {
      "interval": "2026-02-06T05:08:01Z/2026-02-06T05:28:51Z",
      "currentTime": "2026-02-06T05:08:01Z",
      "multiplier": 1
    }
  },
  {
    "id": "aircraft_umt001",
    "name": "UMT001 Flight",
    "availability": "2026-02-06T05:08:01Z/2026-02-06T05:28:51Z",
    "position": {
      "epoch": "2026-02-06T05:08:01Z",
      "cartographicDegrees": [
        0, 34.610346, 127.210551, 6.096,
        1, 34.610348, 127.210547, 7.010,
        ...
      ]
    },
    "path": {
      "show": true,
      "width": 3,
      "material": {
        "polylineGradient": {
          "colors": [
            { "rgba": [0, 255, 0, 255] },
            { "rgba": [255, 255, 0, 255] },
            { "rgba": [255, 0, 0, 255] }
          ],
          "stops": [0.0, 0.5, 1.0]
        }
      },
      "resolution": 60
    },
    "billboard": {
      "image": "/static/aircraft_icon.png",
      "scale": 0.5,
      "eyeOffset": { "cartesian": [0, 0, 0] }
    },
    "properties": {
      "lte_rsrp": -85.5,
      "starlink_latency": 45.2,
      "speed_knots": 25,
      "altitude_feet": 500
    }
  }
]
```

---

## 5. 컴포넌트 구조

### 5.1 프론트엔드 컴포넌트 트리

```
App
├── GlobalStyles (Tailwind)
├── Router
│   ├── HomePage ("/")
│   │   └── SessionList (기존 2D 대시보드)
│   │
│   └── Viewer3D ("/3d/:sessionId")
│       ├── CesiumViewer (핵심 3D 뷰어)
│       │   ├── useGlobe (지구본 초기화)
│       │   ├── useFlightData (비행 데이터 로드)
│       │   ├── useCamera (카메라 제어)
│       │   └── useEntities (Entity 관리)
│       │
│       ├── ControlPanel (우측 패널)
│       │   ├── TimelineControl (시간 슬라이더)
│       │   │   ├── PlayButton
│       │   │   ├── SpeedControl (0.5x, 1x, 2x, 5x)
│       │   │   └── CurrentTime
│       │   │
│       │   ├── LayerControl (레이어 토글)
│       │   │   ├── FlightPathToggle
│       │   │   ├── BaseStationsToggle
│       │   │   ├── SatellitesToggle
│       │   │   └── HeatmapToggle
│       │   │
│       │   └── DataPanel (실시간 데이터)
│       │       ├── AltitudeIndicator
│       │       ├── SpeedIndicator
│       │       ├── LTE_RSRP_Indicator
│       │       └── Starlink_Latency_Indicator
│       │
│       ├── Toolbar (상단 툴바)
│       │   ├── HomeButton (지구본 리셋)
│       │   ├── FollowModeToggle
│       │   ├── ViewModeSelector (Free, Follow, Top-Down)
│       │   └── ExportButton (스크린샷, 비디오)
│       │
│       └── LoadingOverlay (데이터 로딩 중)
```

### 5.2 핵심 커스텀 훅

#### 5.2.1 `useCesiumViewer`

```typescript
/**
 * Cesium Viewer 초기화 및 관리
 */
export function useCesiumViewer(containerId: string) {
  const [viewer, setViewer] = useState<Cesium.Viewer | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const cesiumViewer = new Cesium.Viewer(containerId, {
      terrainProvider: await Cesium.createWorldTerrainAsync({
        requestVertexNormals: true,
        requestWaterMask: true
      }),
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      timeline: false,
      animation: false,
      navigationHelpButton: false,
      sceneModePicker: false,
      imageryProvider: new Cesium.IonImageryProvider({ assetId: 2 })
    });

    // OSM Buildings 추가
    const osmBuildingsTileset = await Cesium.createOsmBuildingsAsync();
    cesiumViewer.scene.primitives.add(osmBuildingsTileset);

    setViewer(cesiumViewer);
    setIsReady(true);

    return () => {
      cesiumViewer.destroy();
    };
  }, [containerId]);

  return { viewer, isReady };
}
```

#### 5.2.2 `useFlightData`

```typescript
/**
 * 비행 데이터 로드 및 CZML 파싱
 */
export function useFlightData(sessionId: string) {
  const [flightData, setFlightData] = useState<FlightData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const response = await fetch(`/api/3d/czml/${sessionId}`);
        const czmlData = await response.json();

        setFlightData({
          czml: czmlData,
          startTime: Cesium.JulianDate.fromIso8601(czmlData[0].clock.interval.split('/')[0]),
          endTime: Cesium.JulianDate.fromIso8601(czmlData[0].clock.interval.split('/')[1]),
          duration: Cesium.JulianDate.secondsDifference(endTime, startTime)
        });

        setLoading(false);
      } catch (err) {
        setError(err);
        setLoading(false);
      }
    }

    loadData();
  }, [sessionId]);

  return { flightData, loading, error };
}
```

#### 5.2.3 `useTimelineControl`

```typescript
/**
 * 시간 제어 (재생, 일시정지, 속도 조절)
 */
export function useTimelineControl(viewer: Cesium.Viewer | null) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState<Cesium.JulianDate | null>(null);
  const [multiplier, setMultiplier] = useState(1);

  const play = useCallback(() => {
    if (viewer) {
      viewer.clock.shouldAnimate = true;
      setIsPlaying(true);
    }
  }, [viewer]);

  const pause = useCallback(() => {
    if (viewer) {
      viewer.clock.shouldAnimate = false;
      setIsPlaying(false);
    }
  }, [viewer]);

  const setSpeed = useCallback((speed: number) => {
    if (viewer) {
      viewer.clock.multiplier = speed;
      setMultiplier(speed);
    }
  }, [viewer]);

  const seekTo = useCallback((time: Cesium.JulianDate) => {
    if (viewer) {
      viewer.clock.currentTime = time;
      setCurrentTime(time);
    }
  }, [viewer]);

  // Clock tick 리스너
  useEffect(() => {
    if (!viewer) return;

    const removeListener = viewer.clock.onTick.addEventListener((clock) => {
      setCurrentTime(clock.currentTime.clone());
    });

    return () => {
      removeListener();
    };
  }, [viewer]);

  return { isPlaying, currentTime, multiplier, play, pause, setSpeed, seekTo };
}
```

### 5.3 Zustand 상태 관리

```typescript
/**
 * 전역 상태 관리
 */
interface Viewer3DState {
  // Viewer 상태
  viewer: Cesium.Viewer | null;
  setViewer: (viewer: Cesium.Viewer | null) => void;

  // 비행 데이터
  flightData: FlightData | null;
  setFlightData: (data: FlightData) => void;

  // 레이어 가시성
  layers: {
    flightPath: boolean;
    baseStations: boolean;
    satellites: boolean;
    heatmap: boolean;
  };
  toggleLayer: (layer: keyof Viewer3DState['layers']) => void;

  // 카메라 모드
  cameraMode: 'free' | 'follow' | 'topDown';
  setCameraMode: (mode: Viewer3DState['cameraMode']) => void;

  // 시간 제어
  isPlaying: boolean;
  currentTime: Cesium.JulianDate | null;
  playbackSpeed: number;
  setIsPlaying: (playing: boolean) => void;
  setCurrentTime: (time: Cesium.JulianDate) => void;
  setPlaybackSpeed: (speed: number) => void;
}

export const useViewer3DStore = create<Viewer3DState>((set) => ({
  viewer: null,
  setViewer: (viewer) => set({ viewer }),

  flightData: null,
  setFlightData: (data) => set({ flightData: data }),

  layers: {
    flightPath: true,
    baseStations: true,
    satellites: false,
    heatmap: false
  },
  toggleLayer: (layer) => set((state) => ({
    layers: { ...state.layers, [layer]: !state.layers[layer] }
  })),

  cameraMode: 'free',
  setCameraMode: (mode) => set({ cameraMode: mode }),

  isPlaying: false,
  currentTime: null,
  playbackSpeed: 1,
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setCurrentTime: (time) => set({ currentTime: time }),
  setPlaybackSpeed: (speed) => set({ playbackSpeed: speed })
}));
```

---

## 6. 단계별 구현 계획

### Phase 1: 기초 인프라 (1-2주)

**목표**: Cesium 뷰어 구동 + 기본 비행 경로 표시

**작업 항목**:
1. ✅ React + TypeScript + Vite 프로젝트 생성
2. ✅ Cesium.js 설치 및 설정
3. ✅ 기본 Globe + Terrain 렌더링
4. ✅ ULG 데이터 → CZML 변환 스크립트
5. ✅ 단일 비행 경로 표시 (정적)
6. ✅ 카메라 조작 (마우스/터치)

**완료 기준**:
- [ ] Cesium 뷰어가 3D 지구본을 렌더링
- [ ] 기존 ULG 파일의 비행 경로가 3D로 표시됨
- [ ] 마우스로 화면을 회전/확대/축소 가능

**핵심 파일**:
```
frontend/
├── src/
│   ├── components/
│   │   └── CesiumViewer.tsx
│   ├── hooks/
│   │   └── useCesiumViewer.ts
│   └── App.tsx
backend/
└── api/
    └── czml_generator.py  (신규)
```

---

### Phase 2: 시간 애니메이션 (2주차)

**목표**: 비행 경로 재생 + 시간 슬라이더

**작업 항목**:
1. ✅ CZML Clock 설정
2. ✅ SampledPositionProperty 사용
3. ✅ Timeline 컴포넌트 개발
4. ✅ Play/Pause/Speed 컨트롤
5. ✅ 현재 시각 표시 및 탐색

**완료 기준**:
- [ ] "재생" 버튼 클릭 시 항공기가 경로를 따라 이동
- [ ] 시간 슬라이더로 특정 시각으로 이동 가능
- [ ] 재생 속도 조절 (0.5x, 1x, 2x, 5x)

**핵심 파일**:
```
frontend/src/components/
├── TimelineControl.tsx
├── PlaybackControls.tsx
└── TimeSlider.tsx
```

---

### Phase 3: 고도 색상 매핑 (3주차)

**목표**: 고도에 따른 비행 경로 색상 표시

**작업 항목**:
1. ✅ 고도 데이터 분석 (min, max)
2. ✅ 색상 그라데이션 알고리즘 (viridis, terrain)
3. ✅ PolylineGradientMaterial 적용
4. ✅ 색상 범례 UI 추가

**완료 기준**:
- [ ] 낮은 고도는 파랑/초록, 높은 고도는 노랑/빨강
- [ ] 범례가 표시되어 색상-고도 매핑 확인 가능

**기술 노트**:
```javascript
// 고도별 색상 계산
function getAltitudeColor(altitude, minAlt, maxAlt) {
  const normalized = (altitude - minAlt) / (maxAlt - minAlt);
  return Cesium.Color.fromCssColorString(
    viridis(normalized)  // viridis colormap
  );
}
```

---

### Phase 4: LTE 기지국 시각화 (4주차)

**목표**: LTE 기지국 위치 표시 + 커버리지 반경

**작업 항목**:
1. ✅ 기지국 위치 데이터 수집 (CellMapper API 또는 수동 입력)
2. ✅ GeoJSON 형식으로 저장
3. ✅ Cesium Billboard로 기지국 표시
4. ✅ 커버리지 원 그리기 (EllipseGraphics)
5. ✅ 클릭 시 기지국 정보 팝업

**완료 기준**:
- [ ] 지도에 기지국 마커가 표시됨
- [ ] 각 기지국 주변에 커버리지 영역 표시
- [ ] 기지국 클릭 시 정보 (ID, 주파수, 세기) 표시

**데이터 구조**:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [127.210, 34.610, 50]  // lon, lat, height
      },
      "properties": {
        "id": "BS_001",
        "name": "LTE 기지국 #1",
        "frequency": "2100MHz",
        "coverage_radius": 5000  // meters
      }
    }
  ]
}
```

---

### Phase 5: 신호 세기 히트맵 (5-6주차)

**목표**: LTE/Starlink 신호 세기를 3D 히트맵으로 표시

**작업 항목**:
1. ✅ 비행 경로상 신호 세기 데이터 추출
2. ✅ 보간 알고리즘 (IDW, Kriging)
3. ✅ 3D 포인트 클라우드 또는 볼륨 렌더링
4. ✅ 색상 스케일 (강함: 초록, 약함: 빨강)
5. ✅ 레이어 토글 기능

**완료 기준**:
- [ ] "히트맵" 토글 활성화 시 신호 세기 시각화 표시
- [ ] 신호가 강한 영역은 초록, 약한 영역은 빨강

**기술 선택지**:
- **옵션 A**: Cesium Point Primitives (빠름, 단순)
- **옵션 B**: Custom Shader (고급, 부드러운 그라데이션)

---

### Phase 6: Starlink 위성 시각화 (7-8주차)

**목표**: Starlink 위성 궤도 표시 + 통신 링크

**작업 항목**:
1. ✅ TLE 데이터 다운로드 (CelesTrak API)
2. ✅ TLE → 궤도 계산 (SGP4 알고리즘)
3. ✅ Cesium Satellite 엔티티 추가
4. ✅ 비행체-위성 연결선 그리기
5. ✅ 실시간 위성 위치 업데이트

**완료 기준**:
- [ ] 지구 주위 Starlink 위성들이 표시됨
- [ ] 비행체와 통신 중인 위성과 연결선 표시
- [ ] 위성 궤도 경로 표시

**외부 API**:
```python
# TLE 데이터 다운로드
import requests

response = requests.get('https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle')
tle_lines = response.text.split('\n')
```

---

### Phase 7: 실시간 스트리밍 (9주차)

**목표**: WebSocket을 통한 실시간 비행 데이터 스트리밍

**작업 항목**:
1. ✅ Flask-SocketIO 설정
2. ✅ 라즈베리파이 → 백엔드 WebSocket 연결
3. ✅ 백엔드 → 프론트엔드 브로드캐스트
4. ✅ 실시간 Entity 업데이트
5. ✅ 버퍼링 및 성능 최적화

**완료 기준**:
- [ ] 라즈베리파이에서 수집한 데이터가 실시간으로 3D 뷰에 반영
- [ ] 1초 이내 지연 (latency < 1s)
- [ ] 끊김 없이 부드러운 업데이트

**WebSocket 이벤트**:
```javascript
// Frontend
socket.on('flight_update', (data) => {
  const { position, altitude, lte_rsrp, starlink_latency, timestamp } = data;

  // Entity 업데이트
  aircraftEntity.position.addSample(
    Cesium.JulianDate.fromIso8601(timestamp),
    Cesium.Cartesian3.fromDegrees(position.lon, position.lat, altitude)
  );
});
```

---

### Phase 8: 고급 기능 (10주+)

**선택적 기능** (우선순위 낮음):

1. **다중 비행 동시 재생**
   - 여러 비행 세션을 동시에 표시 및 비교

2. **경로 비교 모드**
   - 두 비행의 경로를 겹쳐서 표시
   - 차이점 하이라이트

3. **VR/AR 지원**
   - WebXR API 활용
   - VR 헤드셋으로 3D 공간 탐험

4. **비디오 녹화**
   - Cesium 화면을 비디오로 녹화
   - 보고서용 영상 생성

5. **AI 인사이트**
   - 이상 패턴 자동 감지
   - 신호 품질 저하 예측

---

## 7. 위험 요소 및 대응책

### 7.1 성능 위험

| 위험 | 영향도 | 발생 가능성 | 대응책 |
|------|--------|-------------|--------|
| **대용량 데이터 로딩 지연** | 높음 | 높음 | - Progressive loading<br>- Data chunking<br>- IndexedDB 캐싱 |
| **60 FPS 미달 (끊김)** | 높음 | 중간 | - LOD (Level of Detail)<br>- Frustum culling<br>- Entity batching |
| **메모리 누수** | 중간 | 중간 | - Entity 재사용<br>- dispose() 호출<br>- 메모리 프로파일링 |
| **WebSocket 연결 끊김** | 중간 | 높음 | - 자동 재연결<br>- Exponential backoff<br>- 오프라인 모드 |

### 7.2 기술 위험

| 위험 | 영향도 | 발생 가능성 | 대응책 |
|------|--------|-------------|--------|
| **Cesium 학습 곡선** | 중간 | 높음 | - 공식 튜토리얼 우선 학습<br>- MVP부터 시작<br>- 커뮤니티 활용 |
| **CZML 데이터 변환 오류** | 높음 | 중간 | - 단위 테스트<br>- 샘플 데이터 검증<br>- 스키마 검증 |
| **TLE 데이터 파싱 실패** | 낮음 | 낮음 | - 라이브러리 사용 (satellite.js)<br>- 예외 처리 |
| **브라우저 호환성 문제** | 중간 | 낮음 | - WebGL 2 폴백<br>- 지원 브라우저 명시 |

### 7.3 사용자 경험 위험

| 위험 | 영향도 | 발생 가능성 | 대응책 |
|------|--------|-------------|--------|
| **복잡한 UI로 인한 혼란** | 높음 | 높음 | - Progressive disclosure<br>- 온보딩 튜토리얼<br>- 프리셋 제공 |
| **모바일 성능 저하** | 중간 | 높음 | - 모바일 전용 최적화<br>- 저사양 모드<br>- 데이터 제한 |
| **3D 멀미** | 낮음 | 중간 | - 부드러운 카메라 전환<br>- FOV 조절 옵션<br>- 2D 폴백 제공 |

---

## 8. 성능 요구사항

### 8.1 목표 지표

| 지표 | 목표값 | 측정 방법 |
|------|--------|-----------|
| **초기 로딩 시간** | < 3초 | Time to Interactive (TTI) |
| **FPS** | 60 FPS | Chrome DevTools Performance |
| **메모리 사용량** | < 500MB | Chrome Task Manager |
| **WebSocket 지연** | < 1초 | 타임스탬프 비교 |
| **번들 크기** | < 2MB (gzipped) | Webpack Bundle Analyzer |

### 8.2 최적화 전략

#### 8.2.1 데이터 최적화

```python
# LTTB (Largest Triangle Three Buckets) 알고리즘
# 10,000개 데이터포인트 → 1,000개로 압축 (90% 감소)

def lttb_downsample(data, threshold):
    """
    Largest Triangle Three Buckets 다운샘플링
    시각적 정보 손실 최소화
    """
    data_length = len(data)
    if threshold >= data_length or threshold == 0:
        return data

    sampled = [data[0]]
    every = (data_length - 2) / (threshold - 2)

    a = 0
    next_a = 0

    for i in range(threshold - 2):
        avg_x = 0
        avg_y = 0
        avg_range_start = int(math.floor((i + 1) * every) + 1)
        avg_range_end = int(math.floor((i + 2) * every) + 1)
        avg_range_end = min(avg_range_end, data_length)

        avg_range_length = avg_range_end - avg_range_start

        while avg_range_start < avg_range_end:
            avg_x += data[avg_range_start]['x']
            avg_y += data[avg_range_start]['y']
            avg_range_start += 1

        avg_x /= avg_range_length
        avg_y /= avg_range_length

        range_offs = int(math.floor((i + 0) * every) + 1)
        range_to = int(math.floor((i + 1) * every) + 1)

        point_a_x = data[a]['x']
        point_a_y = data[a]['y']

        max_area = -1

        while range_offs < range_to:
            area = abs(
                (point_a_x - avg_x) * (data[range_offs]['y'] - point_a_y) -
                (point_a_x - data[range_offs]['x']) * (avg_y - point_a_y)
            ) * 0.5
            if area > max_area:
                max_area = area
                next_a = range_offs

            range_offs += 1

        sampled.append(data[next_a])
        a = next_a

    sampled.append(data[data_length - 1])
    return sampled
```

#### 8.2.2 렌더링 최적화

```javascript
// Entity Batching (여러 Entity를 하나로 통합)
const pointCollection = viewer.scene.primitives.add(
  new Cesium.PointPrimitiveCollection()
);

baseStations.forEach(station => {
  pointCollection.add({
    position: Cesium.Cartesian3.fromDegrees(station.lon, station.lat),
    color: Cesium.Color.RED,
    pixelSize: 10
  });
});

// Level of Detail (LOD)
viewer.scene.globe.maximumScreenSpaceError = 2;  // 기본값 2, 낮을수록 고품질

// Frustum Culling (자동, 시야 밖 Entity 렌더링 안 함)
// Cesium이 자동으로 처리
```

#### 8.2.3 Code Splitting

```javascript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'cesium': ['cesium'],
          'vendor': ['react', 'react-dom'],
          'ui': ['@radix-ui/react-dialog', '@radix-ui/react-slider']
        }
      }
    }
  }
});
```

---

## 9. 테스트 전략

### 9.1 테스트 피라미드

```
        /\
       /  \        E2E Tests (10%)
      /____\       - Playwright
     /      \
    /        \     Integration Tests (30%)
   /__________\    - React Testing Library
  /            \
 /              \  Unit Tests (60%)
/________________\ - Vitest
```

### 9.2 단위 테스트 (Vitest)

```typescript
// hooks/useCesiumViewer.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useCesiumViewer } from './useCesiumViewer';

describe('useCesiumViewer', () => {
  it('should initialize Cesium Viewer', async () => {
    const { result } = renderHook(() => useCesiumViewer('cesium-container'));

    await waitFor(() => {
      expect(result.current.viewer).not.toBeNull();
      expect(result.current.isReady).toBe(true);
    });
  });

  it('should destroy Viewer on unmount', async () => {
    const { result, unmount } = renderHook(() => useCesiumViewer('cesium-container'));

    await waitFor(() => {
      expect(result.current.isReady).toBe(true);
    });

    const viewer = result.current.viewer;
    unmount();

    expect(viewer.isDestroyed()).toBe(true);
  });
});
```

### 9.3 통합 테스트 (React Testing Library)

```typescript
// components/TimelineControl.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { TimelineControl } from './TimelineControl';

describe('TimelineControl', () => {
  it('should play and pause animation', () => {
    const onPlayMock = vi.fn();
    const onPauseMock = vi.fn();

    render(
      <TimelineControl
        isPlaying={false}
        onPlay={onPlayMock}
        onPause={onPauseMock}
      />
    );

    const playButton = screen.getByRole('button', { name: /play/i });
    fireEvent.click(playButton);

    expect(onPlayMock).toHaveBeenCalledTimes(1);
  });
});
```

### 9.4 E2E 테스트 (Playwright)

```typescript
// e2e/flight-visualization.spec.ts
import { test, expect } from '@playwright/test';

test('should load and play flight animation', async ({ page }) => {
  await page.goto('http://localhost:5173/3d/test_session');

  // 3D 뷰어 로드 대기
  await expect(page.locator('.cesium-viewer')).toBeVisible({ timeout: 10000 });

  // 재생 버튼 클릭
  await page.click('button[aria-label="Play"]');

  // 시간이 흐르는지 확인
  const initialTime = await page.textContent('.current-time');
  await page.waitForTimeout(2000);
  const updatedTime = await page.textContent('.current-time');

  expect(initialTime).not.toBe(updatedTime);
});
```

### 9.5 성능 테스트

```javascript
// performance/rendering.bench.js
import { bench, describe } from 'vitest';

describe('Cesium Rendering Performance', () => {
  bench('render 10,000 entities', () => {
    const viewer = new Cesium.Viewer('container');
    const entities = [];

    for (let i = 0; i < 10000; i++) {
      entities.push(viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(
          Math.random() * 360 - 180,
          Math.random() * 180 - 90,
          0
        ),
        point: {
          pixelSize: 5,
          color: Cesium.Color.RED
        }
      }));
    }

    viewer.render();
    viewer.destroy();
  }, { iterations: 10 });
});
```

---

## 10. 배포 계획

### 10.1 Docker 컨테이너화

```dockerfile
# Dockerfile.frontend
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

```dockerfile
# Dockerfile.backend (기존 Flask 확장)
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 환경 변수
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5002

CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "4", "--worker-class", "eventlet", "app:app"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "5002:5002"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/starlink
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: starlink
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 10.2 CI/CD 파이프라인

```yaml
# .github/workflows/deploy.yml
name: Deploy 3D Visualization

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 20
      - run: npm ci
      - run: npm run test
      - run: npm run build

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and push Docker images
        run: |
          docker-compose build
          docker-compose push
      - name: Deploy to production
        run: |
          ssh user@server 'cd /app && docker-compose pull && docker-compose up -d'
```

### 10.3 모니터링 및 로깅

**Sentry** (에러 추적):
```javascript
import * as Sentry from '@sentry/react';

Sentry.init({
  dsn: 'YOUR_SENTRY_DSN',
  integrations: [new Sentry.BrowserTracing()],
  tracesSampleRate: 1.0
});
```

**Google Analytics** (사용자 행동):
```javascript
import ReactGA from 'react-ga4';

ReactGA.initialize('YOUR_GA_MEASUREMENT_ID');

// 페이지 뷰 추적
ReactGA.send({ hitType: 'pageview', page: window.location.pathname });

// 이벤트 추적
ReactGA.event({
  category: '3D Viewer',
  action: 'Play Flight Animation',
  label: sessionId
});
```

---

## 다음 단계

### 즉시 시작 가능한 작업

1. **Phase 1 킥오프**: React + Vite + Cesium 프로젝트 생성
2. **POC 개발**: 기존 ULG 파일 하나를 3D로 시각화
3. **팀 리뷰**: POC 데모 후 피드백 수렴

### 의사결정 필요 사항

1. **Cesium Ion 계정**: 무료 tier vs 유료 (더 많은 기능)
2. **배포 환경**: 로컬 서버 vs 클라우드 (AWS, Azure)
3. **TLE 데이터 소스**: CelesTrak vs Space-Track
4. **UI 디자인**: 기존 스타일 유지 vs 새로운 디자인 시스템

### 리소스 요구사항

- **개발자**: 1명 (풀타임, 10주)
- **디자이너**: 0.5명 (UI 설계, 아이콘)
- **QA**: 0.3명 (테스트 계획, 실행)
- **인프라**: 최소 8GB RAM, WebGL 2 지원 GPU

---

**문서 작성자**: Claude Sonnet 4.5
**검토자**: (검토 필요)
**승인자**: (승인 필요)

**변경 이력**:
- 2026-02-06: 초안 작성
