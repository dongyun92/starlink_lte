import { useEffect, useRef, useState } from 'react';
import { getCZMLData, getHeatmapCZML, getFlightScenarios, getCellTowers, getSatelliteDirectionCZML, getTowerConnectionsCZML, getSignalLossSegments } from '@/services/api';
import type { FlightScenario, FlightSession } from '@/types/flight';
import { UnifiedControlPanel } from './UnifiedControlPanel';
import { AnalyticsPanel } from './AnalyticsPanel';
import { KPIDashboard } from './KPIDashboard';
import RootCausePanel from './RootCausePanel';
import { SignalLossDrilldownModal } from './SignalLossDrilldownModal';

interface CesiumViewerProps {
  className?: string;
  selectedSessionId: string | null;
  sessions: FlightSession[];
  onSessionSelect: (sessionId: string) => void;
}

type CameraMode = 'free' | 'track';

/**
 * CesiumViewer 컴포넌트
 * 3D 지구본과 지형, 건물을 렌더링하고 비행 경로를 표시하는 Cesium Viewer
 */
export default function CesiumViewer({ className = 'w-full h-screen', selectedSessionId, sessions, onSessionSelect }: CesiumViewerProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const cesiumViewerRef = useRef<any>(null);
  const czmlDataSourceRef = useRef<any>(null);
  const aircraftEntityRef = useRef<any>(null);

  // Heatmap data source refs
  const lteHeatmapSourceRef = useRef<any>(null);
  const starlinkHeatmapSourceRef = useRef<any>(null);
  const combinedHeatmapSourceRef = useRef<any>(null);

  // Cell tower refs
  const cellTowerEntitiesRef = useRef<any[]>([]);

  // Satellite direction ref
  const satelliteDirectionSourceRef = useRef<any>(null);

  // Tower connections ref
  const towerConnectionsSourceRef = useRef<any>(null);

  // Signal loss segments ref
  const signalLossEntitiesRef = useRef<any[]>([]);

  const [cameraMode, setCameraMode] = useState<CameraMode>('free');

  // Heatmap layer states
  const [lteHeatmap, setLteHeatmap] = useState<boolean>(false);
  const [starlinkHeatmap, setStarlinkHeatmap] = useState<boolean>(false);
  const [combinedHeatmap, setCombinedHeatmap] = useState<boolean>(false);
  const [heatmapStyle, setHeatmapStyle] = useState<'point' | 'voxel' | 'hexagon'>('point');

  // Hexagon heatmap parameters
  const [hexagonResolution, setHexagonResolution] = useState<number>(8);
  const [hexagonAggregation, setHexagonAggregation] = useState<'mean' | 'max' | 'min' | 'median'>('mean');
  const [hexagonExtrusionHeight, setHexagonExtrusionHeight] = useState<number>(200);

  // Mutual exclusive heatmap toggle handlers
  const handleLteHeatmapToggle = (enabled: boolean) => {
    if (enabled) {
      setStarlinkHeatmap(false);
      setCombinedHeatmap(false);
    }
    setLteHeatmap(enabled);
  };

  const handleStarlinkHeatmapToggle = (enabled: boolean) => {
    if (enabled) {
      setLteHeatmap(false);
      setCombinedHeatmap(false);
    }
    setStarlinkHeatmap(enabled);
  };

  const handleCombinedHeatmapToggle = (enabled: boolean) => {
    if (enabled) {
      setLteHeatmap(false);
      setStarlinkHeatmap(false);
    }
    setCombinedHeatmap(enabled);
  };

  // Flight scenario filtering
  const [flightScenarios, setFlightScenarios] = useState<FlightScenario[]>([]);
  const [selectedFlightId, setSelectedFlightId] = useState<number | null>(null);

  // Path color mode
  type PathColorMode = 'altitude' | 'speed' |
    'lte_quality_combined' | 'lte_rsrp' | 'lte_sinr' | 'lte_rsrq' |
    'starlink_quality_combined' | 'starlink_snr' | 'starlink_latency' |
    'starlink_packet_loss' | 'starlink_throughput_down' | 'starlink_throughput_up' |
    'starlink_obstruction' | 'starlink_uptime';
  const [pathColorMode, setPathColorMode] = useState<PathColorMode>('altitude');
  const [colorMetadata, setColorMetadata] = useState<{column: string; min: number; max: number; unit: string} | null>(null);
  const [customMetrics, setCustomMetrics] = useState<Record<string, number> | null>(null);

  // Heatmap metadata (actual columns detected by backend)
  const [heatmapMetadata, setHeatmapMetadata] = useState<{
    lteColumn: string | null;
    starlinkColumn: string | null;
  }>({
    lteColumn: null,
    starlinkColumn: null
  });

  // Cell tower states
  const [showCellTowers, setShowCellTowers] = useState<boolean>(false);
  const [cellTowerData, setCellTowerData] = useState<any>(null);

  // Analytics panel state
  const [showAnalytics, setShowAnalytics] = useState<boolean>(true);

  // KPI Dashboard state
  const [showKPIDashboard, setShowKPIDashboard] = useState<boolean>(true);

  // Root Cause Panel state
  const [showRootCausePanel, setShowRootCausePanel] = useState<boolean>(false);

  // Signal Loss Drilldown Modal state
  const [selectedSegment, setSelectedSegment] = useState<any | null>(null);
  const [showDrilldownModal, setShowDrilldownModal] = useState<boolean>(false);

  // Satellite direction state
  const [showSatelliteDirection, setShowSatelliteDirection] = useState<boolean>(false);

  // Tower connections state
  const [showTowerConnections, setShowTowerConnections] = useState<boolean>(false);

  // Signal loss state
  const [showSignalLoss, setShowSignalLoss] = useState<boolean>(false);
  const [signalLossSegments, setSignalLossSegments] = useState<any[]>([]);

  // Timeline control states
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(10);
  const [currentTime, setCurrentTime] = useState<string>('00:00:00');

  // Timeline control functions
  const handlePlayPause = () => {
    if (!cesiumViewerRef.current) return;

    const shouldAnimate = !isPlaying;
    cesiumViewerRef.current.clock.shouldAnimate = shouldAnimate;
    setIsPlaying(shouldAnimate);
  };

  const handleSpeedChange = (speed: number) => {
    if (!cesiumViewerRef.current) return;

    cesiumViewerRef.current.clock.multiplier = speed;
    setPlaybackSpeed(speed);
  };

  const formatTime = (julianDate: any): string => {
    if (!julianDate || typeof window.Cesium === 'undefined') return '00:00:00';

    const Cesium = window.Cesium;
    const gregorianDate = Cesium.JulianDate.toGregorianDate(julianDate);
    const hours = String(gregorianDate.hour).padStart(2, '0');
    const minutes = String(gregorianDate.minute).padStart(2, '0');
    const seconds = String(Math.floor(gregorianDate.second)).padStart(2, '0');

    return `${hours}:${minutes}:${seconds}`;
  };

  // Jump to location function for drilldown modal
  const handleJumpToLocation = (lat: number, lon: number, altitude: number) => {
    if (!cesiumViewerRef.current || typeof window.Cesium === 'undefined') return;

    const Cesium = window.Cesium;
    const viewer = cesiumViewerRef.current;

    // Fly to the location with smooth animation
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(lon, lat, altitude + 500), // 500m above the segment
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-45), // Look down at 45 degrees
        roll: 0.0,
      },
      duration: 2.0, // 2 seconds animation
    });

    // Close the modal after jumping
    setShowDrilldownModal(false);
  };

  // Track current time from clock
  useEffect(() => {
    if (!cesiumViewerRef.current) return;

    const interval = setInterval(() => {
      if (cesiumViewerRef.current && cesiumViewerRef.current.clock) {
        const currentJulian = cesiumViewerRef.current.clock.currentTime;
        setCurrentTime(formatTime(currentJulian));
      }
    }, 100); // Update every 100ms for smooth display

    return () => clearInterval(interval);
  }, [cesiumViewerRef.current]);

  // Cesium Viewer 초기화
  useEffect(() => {
    // Cesium이 로드될 때까지 대기
    if (typeof window.Cesium === 'undefined') {
      console.error('❌ Cesium이 로드되지 않았습니다.');
      return;
    }

    const Cesium = window.Cesium;

    // Cesium Ion 토큰 설정
    const token = import.meta.env.VITE_CESIUM_ION_TOKEN;
    if (!token) {
      console.error('❌ Cesium Ion 토큰이 설정되지 않았습니다. .env 파일을 확인하세요.');
      return;
    }
    Cesium.Ion.defaultAccessToken = token;

    // Viewer가 이미 생성되었거나 DOM 요소가 없으면 중단
    if (cesiumViewerRef.current || !viewerRef.current) {
      return;
    }

    // Cesium Viewer 초기화
    const initViewer = async () => {
      try {
        console.log('🌍 Cesium Viewer 초기화 중...');

        const viewer = new Cesium.Viewer(viewerRef.current!, {
          // 기본 지구본만 사용 (Terrain과 Buildings 제거로 WebGL 에러 방지)
          timeline: true,
          animation: true,
          baseLayerPicker: true,
          fullscreenButton: true,
          geocoder: true,
          homeButton: true,
          infoBox: true,
          sceneModePicker: true,
          selectionIndicator: true,
          navigationHelpButton: true,
          navigationInstructionsInitiallyVisible: false,
        });

        // 초기 카메라 위치 설정 (대한민국 상공)
        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(127.0, 37.5, 1000000), // 경도, 위도, 고도(m)
          orientation: {
            heading: 0,
            pitch: -Math.PI / 4, // -45도 각도
            roll: 0,
          },
        });

        cesiumViewerRef.current = viewer;
        console.log('✅ Cesium Viewer 초기화 완료');
      } catch (error) {
        console.error('❌ Cesium Viewer 초기화 실패:', error);
      }
    };

    initViewer();

    // 클린업: 컴포넌트 언마운트 시 Viewer 제거
    return () => {
      if (cesiumViewerRef.current && !cesiumViewerRef.current.isDestroyed()) {
        console.log('🧹 Cesium Viewer 정리 중...');
        cesiumViewerRef.current.destroy();
        cesiumViewerRef.current = null;
      }
    };
  }, []);

  // Load available flight scenarios for the selected session
  useEffect(() => {
    if (!selectedSessionId) {
      setFlightScenarios([]);
      setSelectedFlightId(null);
      return;
    }

    const loadScenarios = async () => {
      try {
        const scenarios = await getFlightScenarios(selectedSessionId);
        setFlightScenarios(scenarios);
        // Reset flight selection when session changes
        setSelectedFlightId(null);
      } catch (error) {
        console.error('Failed to load flight scenarios:', error);
        setFlightScenarios([]);
      }
    };

    loadScenarios();
  }, [selectedSessionId]);

  // 선택된 세션의 CZML 데이터 로드
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    const loadFlightData = async () => {
      try {
        console.log(`📡 Loading CZML data for session: ${selectedSessionId}`);

        // 기존 CZML 데이터 소스 제거
        if (czmlDataSourceRef.current) {
          cesiumViewerRef.current.dataSources.remove(czmlDataSourceRef.current);
          czmlDataSourceRef.current = null;
        }

        // CZML 데이터 가져오기 (단일 경로, 최적화된 샘플링)
        // pathColorMode가 이제 API 파라미터와 직접 매칭됨
        const czmlData = await getCZMLData(selectedSessionId, {
          sample_rate: 0.2,  // 5초마다 1개 포인트 (80% 빠름, 5배 적은 데이터)
          color_by: pathColorMode,
          flight_id: selectedFlightId !== null ? selectedFlightId : undefined,
          custom_metrics: customMetrics || undefined,
        });

        console.log('📦 CZML data loaded:', czmlData);

        // Extract color metadata from CZML document header
        if (Array.isArray(czmlData) && czmlData.length > 0 && czmlData[0].colorMetadata) {
          setColorMetadata(czmlData[0].colorMetadata);
          console.log('📊 Color metadata:', czmlData[0].colorMetadata);
        } else {
          setColorMetadata(null);
        }

        // CZML 데이터 소스 생성 및 추가
        const Cesium = window.Cesium;
        const dataSource = await Cesium.CzmlDataSource.load(czmlData);
        czmlDataSourceRef.current = dataSource;

        await cesiumViewerRef.current.dataSources.add(dataSource);

        // CZML 데이터에서 엔티티 정보 추출
        // Dual mode (gradient): Multiple segments + aircraft
        // Single mode (fallback): Single path + aircraft
        const entities = dataSource.entities.values;

        // Find aircraft entity (always has 'aircraft_' prefix)
        const aircraft = entities.find((e: any) => e.id.includes('aircraft_'));
        aircraftEntityRef.current = aircraft;

        // Get first position from aircraft
        let lon, lat, alt;
        if (aircraft && aircraft.position) {
          const aircraftData = czmlData.find((item: any) => item.id?.includes('aircraft_'));
          if (aircraftData && aircraftData.position) {
            const firstPosition = aircraftData.position.cartographicDegrees;
            lon = firstPosition[1];
            lat = firstPosition[2];
            alt = firstPosition[3];
          }
        }

        console.log(`📍 First position: lon=${lon}, lat=${lat}, alt=${alt}`);

        // 타임라인 시간 범위 설정 (CZML에서 clock 정보 추출)
        const documentPacket = czmlData[0];
        console.log('📋 Document packet:', documentPacket);

        if (documentPacket.clock) {
          const interval = documentPacket.clock.interval;
          const [startTimeStr, endTimeStr] = interval.split('/');

          console.log('⏰ Parsing time interval:', { interval, startTimeStr, endTimeStr });

          const startTime = Cesium.JulianDate.fromIso8601(startTimeStr);
          const endTime = Cesium.JulianDate.fromIso8601(endTimeStr);

          console.log('📅 Parsed JulianDates:', {
            start: Cesium.JulianDate.toIso8601(startTime),
            end: Cesium.JulianDate.toIso8601(endTime)
          });

          // Clock 설정
          const clock = cesiumViewerRef.current.clock;

          console.log('🕐 Clock BEFORE config:', {
            startTime: clock.startTime ? Cesium.JulianDate.toIso8601(clock.startTime) : 'null',
            stopTime: clock.stopTime ? Cesium.JulianDate.toIso8601(clock.stopTime) : 'null',
            currentTime: clock.currentTime ? Cesium.JulianDate.toIso8601(clock.currentTime) : 'null',
            multiplier: clock.multiplier,
            shouldAnimate: clock.shouldAnimate,
            clockRange: clock.clockRange
          });

          clock.startTime = startTime.clone();
          clock.stopTime = endTime.clone();
          clock.currentTime = startTime.clone();
          clock.clockRange = Cesium.ClockRange.LOOP_STOP;
          clock.multiplier = 10;
          clock.shouldAnimate = false;  // 자동재생 비활성화

          console.log('🕐 Clock AFTER config:', {
            startTime: Cesium.JulianDate.toIso8601(clock.startTime),
            stopTime: Cesium.JulianDate.toIso8601(clock.stopTime),
            currentTime: Cesium.JulianDate.toIso8601(clock.currentTime),
            multiplier: clock.multiplier,
            shouldAnimate: clock.shouldAnimate,
            clockRange: clock.clockRange
          });

          // 강제로 animation widget 업데이트
          if (cesiumViewerRef.current.animation) {
            console.log('🎬 Updating animation widget...');
            cesiumViewerRef.current.animation.viewModel.dateFormatter = Cesium.JulianDate.toIso8601;
          }

        } else {
          console.error('❌ No clock info in CZML document packet!');
        }

        // 카메라를 비행 경로 위치로 직접 이동 (고도 + 500m 상공에서 관찰)
        cesiumViewerRef.current.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(lon, lat, alt + 500),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-45),
            roll: 0.0,
          },
          duration: 2,
        });

        console.log('✅ Flight path visualization complete');
        console.log('⏸️ Timeline paused (autoplay disabled)');
      } catch (error) {
        console.error('❌ Failed to load flight data:', error);

        // Show user-friendly error message
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        if (errorMessage.includes('Insufficient data')) {
          // Data availability error - user needs to choose different color mode
          alert(`⚠️ ${errorMessage}\n\nPlease select a different Path Color Mode.`);
        } else {
          // Other errors
          alert(`❌ Failed to load flight path:\n${errorMessage}`);
        }
      }
    };

    loadFlightData();
  }, [selectedSessionId, selectedFlightId, pathColorMode, customMetrics]);

  // 카메라 모드 전환 효과
  useEffect(() => {
    if (!cesiumViewerRef.current || !aircraftEntityRef.current) {
      return;
    }

    if (cameraMode === 'track') {
      // 추적 모드: 비행기를 따라다니기
      cesiumViewerRef.current.trackedEntity = aircraftEntityRef.current;
      console.log('📹 Camera mode: Track (following aircraft)');
    } else {
      // 자유 시점: 추적 해제
      cesiumViewerRef.current.trackedEntity = undefined;
      console.log('📹 Camera mode: Free view');
    }
  }, [cameraMode]);

  // LTE Heatmap 로드 및 토글
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    // Don't load if all heatmaps are disabled (prevent re-triggering after cleanup)
    const allHeatmapsDisabled = !lteHeatmap && !starlinkHeatmap && !combinedHeatmap;
    if (allHeatmapsDisabled) {
      return;
    }

    const loadLTEHeatmap = async () => {
      if (!cesiumViewerRef.current) return;

      try {
        if (lteHeatmap) {
          // Remove existing heatmap if present
          if (lteHeatmapSourceRef.current) {
            cesiumViewerRef.current.dataSources.remove(lteHeatmapSourceRef.current);
            lteHeatmapSourceRef.current = null;
          }

          console.log(`🗺️ Loading LTE quality heatmap (${heatmapStyle})...`);
          const czmlData = await getHeatmapCZML(
            selectedSessionId,
            'lte',
            heatmapStyle,
            selectedFlightId !== null ? selectedFlightId : undefined,
            heatmapStyle === 'hexagon' ? {
              resolution: hexagonResolution,
              aggregation: hexagonAggregation,
              extrusion_height: hexagonExtrusionHeight
            } : undefined
          );

          // Extract heatmap metadata from CZML document header
          if (Array.isArray(czmlData) && czmlData.length > 0 && czmlData[0].heatmapMetadata) {
            setHeatmapMetadata({
              lteColumn: czmlData[0].heatmapMetadata.lteColumn || null,
              starlinkColumn: czmlData[0].heatmapMetadata.starlinkColumn || null
            });
            console.log('📊 Heatmap metadata:', czmlData[0].heatmapMetadata);
          }

          const Cesium = window.Cesium;
          const dataSource = await Cesium.CzmlDataSource.load(czmlData);
          lteHeatmapSourceRef.current = dataSource;

          await cesiumViewerRef.current.dataSources.add(dataSource);
          console.log('✅ LTE heatmap loaded');
        } else {
          // Remove heatmap when disabled
          if (lteHeatmapSourceRef.current) {
            try {
              cesiumViewerRef.current.dataSources.remove(lteHeatmapSourceRef.current);
              lteHeatmapSourceRef.current = null;
              console.log('🗺️ LTE heatmap removed');
            } catch (removeError) {
              console.error('❌ Error removing LTE heatmap:', removeError);
              lteHeatmapSourceRef.current = null;
            }
          }
        }
      } catch (error) {
        console.error('❌ Failed to load LTE heatmap:', error);
      }
    };

    loadLTEHeatmap();

    // Cleanup function
    return () => {
      if (lteHeatmapSourceRef.current && cesiumViewerRef.current) {
        try {
          cesiumViewerRef.current.dataSources.remove(lteHeatmapSourceRef.current);
          lteHeatmapSourceRef.current = null;
        } catch (error) {
          // Ignore cleanup errors
        }
      }
    };
  }, [selectedSessionId, lteHeatmap, heatmapStyle, selectedFlightId, hexagonResolution, hexagonAggregation, hexagonExtrusionHeight]);

  // Starlink Heatmap 로드 및 토글
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    // Don't load if all heatmaps are disabled (prevent re-triggering after cleanup)
    const allHeatmapsDisabled = !lteHeatmap && !starlinkHeatmap && !combinedHeatmap;
    if (allHeatmapsDisabled) {
      return;
    }

    const loadStarlinkHeatmap = async () => {
      if (!cesiumViewerRef.current) return;

      try {
        if (starlinkHeatmap) {
          // Remove existing heatmap if present
          if (starlinkHeatmapSourceRef.current) {
            cesiumViewerRef.current.dataSources.remove(starlinkHeatmapSourceRef.current);
            starlinkHeatmapSourceRef.current = null;
          }

          console.log(`🗺️ Loading Starlink quality heatmap (${heatmapStyle})...`);
          const czmlData = await getHeatmapCZML(
            selectedSessionId,
            'starlink',
            heatmapStyle,
            selectedFlightId !== null ? selectedFlightId : undefined,
            heatmapStyle === 'hexagon' ? {
              resolution: hexagonResolution,
              aggregation: hexagonAggregation,
              extrusion_height: hexagonExtrusionHeight
            } : undefined
          );

          // Extract heatmap metadata from CZML document header
          if (Array.isArray(czmlData) && czmlData.length > 0 && czmlData[0].heatmapMetadata) {
            setHeatmapMetadata({
              lteColumn: czmlData[0].heatmapMetadata.lteColumn || null,
              starlinkColumn: czmlData[0].heatmapMetadata.starlinkColumn || null
            });
            console.log('📊 Heatmap metadata:', czmlData[0].heatmapMetadata);
          }

          const Cesium = window.Cesium;
          const dataSource = await Cesium.CzmlDataSource.load(czmlData);
          starlinkHeatmapSourceRef.current = dataSource;

          await cesiumViewerRef.current.dataSources.add(dataSource);
          console.log('✅ Starlink heatmap loaded');
        } else {
          // Remove heatmap when disabled
          if (starlinkHeatmapSourceRef.current) {
            try {
              cesiumViewerRef.current.dataSources.remove(starlinkHeatmapSourceRef.current);
              starlinkHeatmapSourceRef.current = null;
              console.log('🗺️ Starlink heatmap removed');
            } catch (removeError) {
              console.error('❌ Error removing Starlink heatmap:', removeError);
              starlinkHeatmapSourceRef.current = null;
            }
          }
        }
      } catch (error) {
        console.error('❌ Failed to load Starlink heatmap:', error);
      }
    };

    loadStarlinkHeatmap();

    // Cleanup function
    return () => {
      if (starlinkHeatmapSourceRef.current && cesiumViewerRef.current) {
        try {
          cesiumViewerRef.current.dataSources.remove(starlinkHeatmapSourceRef.current);
          starlinkHeatmapSourceRef.current = null;
        } catch (error) {
          // Ignore cleanup errors
        }
      }
    };
  }, [selectedSessionId, starlinkHeatmap, heatmapStyle, selectedFlightId, hexagonResolution, hexagonAggregation, hexagonExtrusionHeight]);

  // Combined Heatmap 로드 및 토글
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    // Don't load if all heatmaps are disabled (prevent re-triggering after cleanup)
    const allHeatmapsDisabled = !lteHeatmap && !starlinkHeatmap && !combinedHeatmap;
    if (allHeatmapsDisabled) {
      return;
    }

    const loadCombinedHeatmap = async () => {
      if (!cesiumViewerRef.current) return;

      try {
        if (combinedHeatmap) {
          // Remove existing heatmap if present
          if (combinedHeatmapSourceRef.current) {
            cesiumViewerRef.current.dataSources.remove(combinedHeatmapSourceRef.current);
            combinedHeatmapSourceRef.current = null;
          }

          console.log(`🗺️ Loading Combined quality heatmap (${heatmapStyle})...`);
          const czmlData = await getHeatmapCZML(
            selectedSessionId,
            'combined',
            heatmapStyle,
            selectedFlightId !== null ? selectedFlightId : undefined,
            heatmapStyle === 'hexagon' ? {
              resolution: hexagonResolution,
              aggregation: hexagonAggregation,
              extrusion_height: hexagonExtrusionHeight
            } : undefined
          );

          // Extract heatmap metadata from CZML document header
          if (Array.isArray(czmlData) && czmlData.length > 0 && czmlData[0].heatmapMetadata) {
            setHeatmapMetadata({
              lteColumn: czmlData[0].heatmapMetadata.lteColumn || null,
              starlinkColumn: czmlData[0].heatmapMetadata.starlinkColumn || null
            });
            console.log('📊 Heatmap metadata:', czmlData[0].heatmapMetadata);
          }

          const Cesium = window.Cesium;
          const dataSource = await Cesium.CzmlDataSource.load(czmlData);
          combinedHeatmapSourceRef.current = dataSource;

          await cesiumViewerRef.current.dataSources.add(dataSource);
          console.log('✅ Combined heatmap loaded');
        } else {
          // Remove heatmap when disabled
          if (combinedHeatmapSourceRef.current) {
            try {
              cesiumViewerRef.current.dataSources.remove(combinedHeatmapSourceRef.current);
              combinedHeatmapSourceRef.current = null;
              console.log('🗺️ Combined heatmap removed');
            } catch (removeError) {
              console.error('❌ Error removing Combined heatmap:', removeError);
              combinedHeatmapSourceRef.current = null;
            }
          }
        }
      } catch (error) {
        console.error('❌ Failed to load Combined heatmap:', error);
      }
    };

    loadCombinedHeatmap();

    // Cleanup function
    return () => {
      if (combinedHeatmapSourceRef.current && cesiumViewerRef.current) {
        try {
          cesiumViewerRef.current.dataSources.remove(combinedHeatmapSourceRef.current);
          combinedHeatmapSourceRef.current = null;
        } catch (error) {
          // Ignore cleanup errors
        }
      }
    };
  }, [selectedSessionId, combinedHeatmap, heatmapStyle, selectedFlightId, hexagonResolution, hexagonAggregation, hexagonExtrusionHeight]);

  // Cleanup all heatmaps when all are disabled (with delay to handle race conditions)
  useEffect(() => {
    if (!cesiumViewerRef.current) return;

    const allHeatmapsDisabled = !lteHeatmap && !starlinkHeatmap && !combinedHeatmap;

    if (allHeatmapsDisabled) {
      // Use setTimeout to ensure async loading completes before cleanup
      const cleanupTimer = setTimeout(() => {
        if (!cesiumViewerRef.current) return;

        console.log('🧹 Cleaning up all heatmap data sources...');

        // Force remove ALL data sources that match heatmap pattern
        const viewer = cesiumViewerRef.current;
        const dataSources = viewer.dataSources;
        const sourcesToRemove: any[] = [];

        // Collect all heatmap data sources
        for (let i = 0; i < dataSources.length; i++) {
          const ds = dataSources.get(i);
          if (ds && ds.name && ds.name.includes('heatmap')) {
            sourcesToRemove.push(ds);
          }
        }

        // Remove collected sources
        sourcesToRemove.forEach((ds, index) => {
          try {
            dataSources.remove(ds);
            console.log(`  ✅ Heatmap data source ${index + 1} removed (${ds.name})`);
          } catch (error) {
            console.error(`  ❌ Error removing heatmap ${index + 1}:`, error);
          }
        });

        // Clear refs
        lteHeatmapSourceRef.current = null;
        starlinkHeatmapSourceRef.current = null;
        combinedHeatmapSourceRef.current = null;

        console.log(`✨ All heatmaps cleaned (${sourcesToRemove.length} sources removed)`);
      }, 100); // 100ms delay to allow async operations to complete

      return () => clearTimeout(cleanupTimer);
    }
  }, [lteHeatmap, starlinkHeatmap, combinedHeatmap]);

  // Cell Tower 데이터 로드
  useEffect(() => {
    if (!selectedSessionId || !showCellTowers) {
      setCellTowerData(null);
      return;
    }

    const loadCellTowers = async () => {
      try {
        console.log('📡 Loading cell tower data...');
        const data = await getCellTowers(selectedSessionId, {
          radio: 'LTE',
          use_cache: true,
          flight_id: selectedFlightId !== null ? selectedFlightId : undefined
        });
        setCellTowerData(data);
        console.log(`✅ Cell tower data loaded: ${data.features?.length || 0} towers`);
      } catch (error) {
        console.error('❌ Failed to load cell tower data:', error);
        setCellTowerData(null);
      }
    };

    loadCellTowers();
  }, [selectedSessionId, showCellTowers, selectedFlightId]);

  // Cell Tower 시각화
  useEffect(() => {
    if (!cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    const Cesium = window.Cesium;

    // 기존 기지국 엔티티 제거
    cellTowerEntitiesRef.current.forEach(entity => {
      cesiumViewerRef.current.entities.remove(entity);
    });
    cellTowerEntitiesRef.current = [];

    // 데이터가 없거나 표시 비활성화 시 종료
    if (!cellTowerData || !showCellTowers || !cellTowerData.features) {
      return;
    }

    console.log(`📡 Rendering ${cellTowerData.features.length} cell towers...`);

    // 각 기지국을 Cesium Entity로 추가
    cellTowerData.features.forEach((feature: any) => {
      const coords = feature.geometry.coordinates;
      const props = feature.properties;
      const lon = coords[0];
      const lat = coords[1];
      const height = 30; // 기지국 높이 (지면에서 30m)

      // Check if this tower was connected during flight
      const isConnected = props.is_connected === true;

      // Different colors for connected vs unconnected towers
      const iconColor = isConnected ? '#ff4444' : '#3498db'; // Red for connected, Blue for unconnected
      const iconSize = isConnected ? 40 : 28; // Larger for connected towers

      // Generate SVG with dynamic color
      const svgIcon = `data:image/svg+xml;base64,${btoa(`<svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="16" r="14" fill="${iconColor}" stroke="#fff" stroke-width="2"/>
  <path d="M16 8V24" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
  <path d="M12 12H16" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
  <path d="M16 12H20" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
  <path d="M12 16H16" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
  <path d="M16 16H20" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
  <path d="M12 20H16" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
  <path d="M16 20H20" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
</svg>`)}`;

      // 기지국 마커 (Billboard) with Label
      const towerEntity = cesiumViewerRef.current.entities.add({
        position: Cesium.Cartesian3.fromDegrees(lon, lat, height),
        billboard: {
          image: svgIcon,
          width: iconSize,
          height: iconSize,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND
        },
        label: {
          text: props.id || 'Unknown',
          font: '12px monospace',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.TOP,
          pixelOffset: new Cesium.Cartesian2(0, 10),
          heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND
        },
        description: `
          <div style="font-family: monospace; font-size: 12px;">
            <b>📡 Cell Tower</b><br/>
            ${isConnected ? '<b style="color: #ff4444;">✅ CONNECTED DURING FLIGHT</b><br/>' : ''}
            <b>Cell ID:</b> ${props.id}<br/>
            <b>Radio:</b> ${props.radio}<br/>
            <b>Operator:</b> ${props.operator || 'Unknown'}<br/>
            <b>MCC:</b> ${props.mcc} <b>MNC:</b> ${props.mnc}<br/>
            <b>Location:</b> ${lat.toFixed(5)}, ${lon.toFixed(5)}
          </div>
        `
      });

      cellTowerEntitiesRef.current.push(towerEntity);
    });

    console.log(`✅ ${cellTowerEntitiesRef.current.length} cell tower entities rendered`);
  }, [cellTowerData, showCellTowers]);

  // Load satellite direction arrows
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined' || !showSatelliteDirection) {
      // Remove satellite direction data source if exists
      if (satelliteDirectionSourceRef.current) {
        cesiumViewerRef.current.dataSources.remove(satelliteDirectionSourceRef.current);
        satelliteDirectionSourceRef.current = null;
      }
      return;
    }

    const Cesium = window.Cesium;

    const loadSatelliteDirection = async () => {
      try {
        console.log('🛰️ Loading satellite direction arrows...');

        // Remove existing data source
        if (satelliteDirectionSourceRef.current) {
          cesiumViewerRef.current.dataSources.remove(satelliteDirectionSourceRef.current);
          satelliteDirectionSourceRef.current = null;
        }

        // Get CZML data
        const czmlData = await getSatelliteDirectionCZML(selectedSessionId, {
          sample_rate: 0.2,  // 5 second intervals
          color_by: pathColorMode.startsWith('starlink') ?
            (pathColorMode === 'starlink_latency' ? 'starlink_latency' : 'starlink_snr') :
            'starlink_snr',
          arrow_length: 10,  // 10m arrows (just for direction indication)
          flight_id: selectedFlightId !== null ? selectedFlightId : undefined
        });

        console.log('📦 Satellite direction CZML data loaded');

        // Load CZML into Cesium
        const dataSource = await Cesium.CzmlDataSource.load(czmlData);
        cesiumViewerRef.current.dataSources.add(dataSource);
        satelliteDirectionSourceRef.current = dataSource;

        console.log('✅ Satellite direction arrows rendered');
      } catch (error) {
        console.error('❌ Failed to load satellite direction arrows:', error);
      }
    };

    loadSatelliteDirection();
  }, [selectedSessionId, selectedFlightId, showSatelliteDirection, pathColorMode]);

  // Load tower connections
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined' || !showTowerConnections) {
      // Remove tower connections data source if exists
      if (towerConnectionsSourceRef.current) {
        cesiumViewerRef.current.dataSources.remove(towerConnectionsSourceRef.current);
        towerConnectionsSourceRef.current = null;
      }
      return;
    }

    const Cesium = window.Cesium;

    const loadTowerConnections = async () => {
      try {
        console.log('📡 Loading tower connections...');

        // Remove existing data source
        if (towerConnectionsSourceRef.current) {
          cesiumViewerRef.current.dataSources.remove(towerConnectionsSourceRef.current);
          towerConnectionsSourceRef.current = null;
        }

        // Get CZML data
        const czmlData = await getTowerConnectionsCZML(selectedSessionId, {
          sample_rate: 0.2,  // 5 second intervals
          flight_id: selectedFlightId !== null ? selectedFlightId : undefined
        });

        console.log('📦 Tower connections CZML data loaded');

        // Load CZML into Cesium
        const dataSource = await Cesium.CzmlDataSource.load(czmlData);
        cesiumViewerRef.current.dataSources.add(dataSource);
        towerConnectionsSourceRef.current = dataSource;

        console.log('✅ Tower connections rendered');
      } catch (error) {
        console.error('❌ Failed to load tower connections:', error);
      }
    };

    loadTowerConnections();
  }, [selectedSessionId, selectedFlightId, showTowerConnections]);

  // Load and render signal loss 3D cylinder markers
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    const Cesium = window.Cesium;

    // Remove existing signal loss entities
    signalLossEntitiesRef.current.forEach(entity => {
      cesiumViewerRef.current.entities.remove(entity);
    });
    signalLossEntitiesRef.current = [];

    // If signal loss visualization is disabled, exit
    if (!showSignalLoss) {
      return;
    }

    const loadSignalLossSegments = async () => {
      try {
        console.log('🔴 Loading signal loss segments...');
        const data = await getSignalLossSegments(selectedSessionId);

        if (!data.segments || data.segments.length === 0) {
          console.log('✅ No signal loss segments detected');
          setSignalLossSegments([]);
          return;
        }

        console.log(`🔴 Rendering ${data.segments.length} signal loss cylinder markers...`);

        // Store segments for timeline markers
        setSignalLossSegments(data.segments);

        // Render each segment as a 3D cylinder
        data.segments.forEach((segment, index) => {
          const { center_lat, center_lon, center_altitude, duration_seconds, lte_poor, starlink_poor } = segment;

          // Color coding: Red if both systems poor, Orange if only one system poor
          let color: any;
          let label: string;

          if (lte_poor && starlink_poor) {
            color = Cesium.Color.RED.withAlpha(0.6);
            label = 'Both Systems Poor';
          } else if (lte_poor) {
            color = Cesium.Color.ORANGE.withAlpha(0.6);
            label = 'LTE Poor';
          } else if (starlink_poor) {
            color = Cesium.Color.ORANGE.withAlpha(0.6);
            label = 'Starlink Poor';
          } else {
            color = Cesium.Color.YELLOW.withAlpha(0.6);
            label = 'Signal Quality Issue';
          }

          // Cylinder dimensions
          const radius = 50; // 50m radius
          const cylinderLength = 100; // 100m height

          // Create cylinder entity
          const cylinderEntity = cesiumViewerRef.current.entities.add({
            position: Cesium.Cartesian3.fromDegrees(center_lon, center_lat, center_altitude),
            cylinder: {
              length: cylinderLength,
              topRadius: radius,
              bottomRadius: radius,
              material: color,
              outline: true,
              outlineColor: Cesium.Color.RED,
              outlineWidth: 2,
              heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND
            },
            label: {
              text: `Signal Loss\n${duration_seconds.toFixed(1)}s`,
              font: '14px monospace',
              fillColor: Cesium.Color.WHITE,
              outlineColor: Cesium.Color.BLACK,
              outlineWidth: 3,
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
              pixelOffset: new Cesium.Cartesian2(0, -60),
              heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND
            },
            description: `
              <div style="font-family: monospace; font-size: 12px;">
                <b>🔴 Signal Loss Segment #${index + 1}</b><br/>
                <b>Duration:</b> ${duration_seconds.toFixed(2)} seconds<br/>
                <b>Status:</b> ${label}<br/>
                <b>LTE Poor:</b> ${lte_poor ? 'Yes' : 'No'}${segment.avg_lte_rsrp !== null ? ` (${segment.avg_lte_rsrp.toFixed(1)} dBm)` : ''}<br/>
                <b>Starlink Poor:</b> ${starlink_poor ? 'Yes' : 'No'}${segment.avg_starlink_latency !== null ? ` (${segment.avg_starlink_latency.toFixed(1)} ms)` : ''}<br/>
                <b>Location:</b> ${center_lat.toFixed(5)}, ${center_lon.toFixed(5)}<br/>
                <b>Altitude:</b> ${center_altitude.toFixed(2)} m
              </div>
            `,
            // Store segment data for click handler
            properties: {
              segmentData: segment,
              isSignalLossCylinder: true
            }
          });

          signalLossEntitiesRef.current.push(cylinderEntity);
        });

        console.log(`✅ ${signalLossEntitiesRef.current.length} signal loss cylinders rendered`);
        console.log(`📊 Total signal loss: ${data.total_percentage.toFixed(2)}% (${data.total_segments} segments)`);
      } catch (error) {
        console.error('❌ Failed to load signal loss segments:', error);
      }
    };

    loadSignalLossSegments();
  }, [selectedSessionId, showSignalLoss]);

  // Add click handler for signal loss cylinders
  useEffect(() => {
    if (!cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    const Cesium = window.Cesium;
    const viewer = cesiumViewerRef.current;

    // Create screen space event handler for clicks
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

    handler.setInputAction((click: any) => {
      const pickedObject = viewer.scene.pick(click.position);

      if (Cesium.defined(pickedObject) && Cesium.defined(pickedObject.id)) {
        const entity = pickedObject.id;

        // Check if this is a signal loss cylinder
        if (entity.properties && entity.properties.isSignalLossCylinder && entity.properties.isSignalLossCylinder.getValue()) {
          const segmentData = entity.properties.segmentData.getValue();

          // Open drilldown modal with segment data
          setSelectedSegment(segmentData);
          setShowDrilldownModal(true);

          console.log('🔴 Signal loss cylinder clicked:', segmentData);
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    // Cleanup handler on unmount
    return () => {
      handler.destroy();
    };
  }, []);

  // Render signal loss markers on timeline
  useEffect(() => {
    if (!cesiumViewerRef.current || signalLossSegments.length === 0 || typeof window.Cesium === 'undefined') {
      return;
    }

    const Cesium = window.Cesium;
    const viewer = cesiumViewerRef.current;

    // Find timeline container
    const timelineContainer = document.querySelector('.cesium-viewer-timelineContainer');
    if (!timelineContainer) {
      console.warn('⚠️ Timeline container not found');
      return;
    }

    // Remove existing markers
    const existingMarkers = timelineContainer.querySelectorAll('.signal-loss-timeline-marker');
    existingMarkers.forEach(marker => marker.remove());

    if (!showSignalLoss) {
      return;
    }

    // Get clock time range
    const startTime = viewer.clock.startTime;
    const stopTime = viewer.clock.stopTime;
    const totalSeconds = Cesium.JulianDate.secondsDifference(stopTime, startTime);

    if (totalSeconds <= 0) {
      return;
    }

    console.log('📍 Adding signal loss markers to timeline...');

    // Calculate timeline width (approximate)
    const timelineRect = timelineContainer.getBoundingClientRect();
    const timelineWidth = timelineRect.width;

    // Add marker for each segment
    signalLossSegments.forEach((segment, index) => {
      const segmentStartTime = Cesium.JulianDate.fromIso8601(segment.start_time);
      const secondsFromStart = Cesium.JulianDate.secondsDifference(segmentStartTime, startTime);
      const positionRatio = secondsFromStart / totalSeconds;
      const leftPosition = positionRatio * timelineWidth;

      // Create marker element
      const marker = document.createElement('div');
      marker.className = 'signal-loss-timeline-marker';
      marker.style.position = 'absolute';
      marker.style.left = `${leftPosition}px`;
      marker.style.top = '0';
      marker.style.width = '3px';
      marker.style.height = '100%';
      marker.style.backgroundColor = segment.lte_poor && segment.starlink_poor ? '#ef4444' : '#f97316';
      marker.style.opacity = '0.8';
      marker.style.zIndex = '1000';
      marker.style.pointerEvents = 'none';
      marker.title = `Signal Loss: ${segment.duration_seconds.toFixed(1)}s`;

      timelineContainer.appendChild(marker);
    });

    console.log(`✅ Added ${signalLossSegments.length} timeline markers`);
  }, [signalLossSegments, showSignalLoss]);

  // Auto-enable cell towers when tower connections are enabled
  useEffect(() => {
    if (showTowerConnections && !showCellTowers) {
      console.log('📡 Auto-enabling cell towers for tower connections visualization');
      setShowCellTowers(true);
    }
  }, [showTowerConnections]);

  const toggleCameraMode = () => {
    setCameraMode((prev) => (prev === 'free' ? 'track' : 'free'));
  };

  return (
    <div className={className}>
      {/* Unified Control Panel */}
      <UnifiedControlPanel
        sessions={sessions}
        selectedSessionId={selectedSessionId}
        onSessionSelect={onSessionSelect}
        lteHeatmap={lteHeatmap}
        starlinkHeatmap={starlinkHeatmap}
        combinedHeatmap={combinedHeatmap}
        heatmapStyle={heatmapStyle}
        onLteHeatmapToggle={handleLteHeatmapToggle}
        onStarlinkHeatmapToggle={handleStarlinkHeatmapToggle}
        onCombinedHeatmapToggle={handleCombinedHeatmapToggle}
        onHeatmapStyleChange={setHeatmapStyle}
        hexagonResolution={hexagonResolution}
        hexagonAggregation={hexagonAggregation}
        hexagonExtrusionHeight={hexagonExtrusionHeight}
        onHexagonResolutionChange={setHexagonResolution}
        onHexagonAggregationChange={setHexagonAggregation}
        onHexagonExtrusionHeightChange={setHexagonExtrusionHeight}
        scenarios={flightScenarios}
        selectedFlightId={selectedFlightId}
        onFlightSelect={setSelectedFlightId}
        cameraMode={cameraMode}
        onCameraModeToggle={toggleCameraMode}
        pathColorMode={pathColorMode}
        onPathColorModeChange={setPathColorMode}
        onCustomMetricsChange={setCustomMetrics}
        colorMetadata={colorMetadata}
        heatmapMetadata={heatmapMetadata}
        showCellTowers={showCellTowers}
        onCellTowersToggle={setShowCellTowers}
        showSatelliteDirection={showSatelliteDirection}
        onSatelliteDirectionToggle={setShowSatelliteDirection}
        showTowerConnections={showTowerConnections}
        onTowerConnectionsToggle={setShowTowerConnections}
        showSignalLoss={showSignalLoss}
        onSignalLossToggle={setShowSignalLoss}
        isPlaying={isPlaying}
        playbackSpeed={playbackSpeed}
        currentTime={currentTime}
        onPlayPause={handlePlayPause}
        onSpeedChange={handleSpeedChange}
        showAnalytics={showAnalytics}
        onAnalyticsToggle={setShowAnalytics}
        showKPIDashboard={showKPIDashboard}
        onKPIDashboardToggle={setShowKPIDashboard}
        showRootCausePanel={showRootCausePanel}
        onRootCausePanelToggle={setShowRootCausePanel}
      />

      {/* KPI Dashboard */}
      {showKPIDashboard && selectedSessionId && (
        <KPIDashboard sessionId={selectedSessionId} />
      )}

      {/* Root Cause Analysis Panel */}
      {showRootCausePanel && selectedSessionId && (
        <RootCausePanel
          sessionId={selectedSessionId}
          isVisible={showRootCausePanel}
          onClose={() => setShowRootCausePanel(false)}
        />
      )}

      {/* Signal Loss Drilldown Modal */}
      <SignalLossDrilldownModal
        segment={selectedSegment}
        isOpen={showDrilldownModal}
        onClose={() => setShowDrilldownModal(false)}
        onJumpToLocation={handleJumpToLocation}
      />

      {/* Analytics Panel */}
      {showAnalytics && selectedSessionId && (
        <AnalyticsPanel
          sessionId={selectedSessionId}
          flightId={selectedFlightId}
          metric={pathColorMode}
        />
      )}

      <div ref={viewerRef} className="w-full h-full" />
    </div>
  );
}

// TypeScript global type declaration
declare global {
  interface Window {
    Cesium: any;
    CESIUM_BASE_URL: string;
  }
}
