import { useEffect, useRef, useState } from 'react';
import { getCZMLData, getHeatmapCZML, getFlightScenarios, getCellTowers, getCellTowersOpenCellID, getSatelliteDirectionCZML, getTowerConnectionsCZML, getSignalLossSegments } from '@/services/api';
import type { FlightScenario, FlightSession } from '@/types/flight';
import { UnifiedControlPanel } from './UnifiedControlPanel';
import { AnalyticsPanel } from './AnalyticsPanel';
import { KPIDashboard } from './KPIDashboard';
import RootCausePanel from './RootCausePanel';
import { SignalLossDrilldownModal } from './SignalLossDrilldownModal';
import { AttitudeAnalysisPanel } from './AttitudeAnalysisPanel';

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

  // OpenCellID tower refs
  const openCellIDTowerEntitiesRef = useRef<any[]>([]);

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

  // Hexagon heatmap parameters (updated defaults for 3D voxel grid)
  const [hexagonResolution, setHexagonResolution] = useState<number>(9);  // 174m edge (better for <1km paths)
  const [hexagonAggregation, setHexagonAggregation] = useState<'mean' | 'max' | 'min' | 'median'>('mean');
  const [hexagonAltitudeBinSize, setHexagonAltitudeBinSize] = useState<number>(25);  // 25m altitude bins

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
    'pitch' | 'roll' | 'pitch_performance' |
    'lte_quality_combined' | 'lte_rsrp' | 'lte_sinr' | 'lte_rsrq' |
    'starlink_quality_combined' | 'starlink_latency' |
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

  // Cell tower states (GPS-based estimation, red)
  const [showCellTowers, setShowCellTowers] = useState<boolean>(false);
  const [cellTowerData, setCellTowerData] = useState<any>(null);

  // OpenCellID tower states (blue)
  const [showOpenCellIDTowers, setShowOpenCellIDTowers] = useState<boolean>(false);
  const [openCellIDTowerData, setOpenCellIDTowerData] = useState<any>(null);

  // Analytics panel state
  const [showAnalytics, setShowAnalytics] = useState<boolean>(false);

  // KPI Dashboard state
  const [showKPIDashboard, setShowKPIDashboard] = useState<boolean>(false);

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

  // Attitude analysis panel state
  const [showAttitudeAnalysis, setShowAttitudeAnalysis] = useState<boolean>(false);

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
        // 🛡️ CRITICAL: Silently ignore errors to prevent UI crashes
        // Invalid GPS data, network errors, or malformed data should not break the visualization
        console.error('❌ Failed to load flight data (silently ignored):', error);

        const errorMessage = error instanceof Error ? error.message : 'Unknown error';

        // Only log to console, do NOT show alert() or error page
        if (errorMessage.includes('Insufficient data')) {
          console.warn('⚠️ Insufficient data for selected color mode, try a different mode');
        } else {
          console.error('❌ Flight data loading error:', errorMessage);
        }

        // Continue execution without breaking the UI
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

    // 체크 해제 시 즉시 cleanup (동기적으로)
    if (!lteHeatmap) {
      if (lteHeatmapSourceRef.current && cesiumViewerRef.current) {
        try {
          cesiumViewerRef.current.dataSources.remove(lteHeatmapSourceRef.current);
          lteHeatmapSourceRef.current = null;
          console.log('🗑️ LTE heatmap removed (unchecked)');
        } catch (error) {
          console.error('❌ Error removing LTE heatmap:', error);
          lteHeatmapSourceRef.current = null;
        }
      }
      return; // 로딩하지 않음
    }

    // 체크 활성화 시: 기존 제거 후 새로 로딩
    const loadLTEHeatmap = async () => {
      if (!cesiumViewerRef.current) return;

      try {
        // CRITICAL: Remove existing heatmap BEFORE loading new style (synchronous removal)
        if (lteHeatmapSourceRef.current) {
          cesiumViewerRef.current.dataSources.remove(lteHeatmapSourceRef.current);
          lteHeatmapSourceRef.current = null;
          console.log('🗑️ LTE heatmap removed (style change)');
        }

        console.log(`🗺️ Loading LTE quality heatmap (${heatmapStyle})...`);
        const czmlData = await getHeatmapCZML(
          selectedSessionId,
          'lte',
          heatmapStyle,
          selectedFlightId !== null ? selectedFlightId : undefined,
          (heatmapStyle === 'hexagon' || heatmapStyle === 'voxel') ? {
            resolution: hexagonResolution,
            aggregation: hexagonAggregation,
            altitude_bin_size: hexagonAltitudeBinSize
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
      } catch (error) {
        // 🛡️ Silently ignore heatmap errors (bad data should not crash UI)
        console.error('❌ Failed to load LTE heatmap (silently ignored):', error);
      }
    };

    loadLTEHeatmap();

    // Cleanup function (컴포넌트 unmount 또는 dependency 변경 시)
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
  }, [selectedSessionId, lteHeatmap, heatmapStyle, selectedFlightId, hexagonResolution, hexagonAggregation, hexagonAltitudeBinSize]);

  // Starlink Heatmap 로드 및 토글
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    // 체크 해제 시 즉시 cleanup (동기적으로)
    if (!starlinkHeatmap) {
      if (starlinkHeatmapSourceRef.current && cesiumViewerRef.current) {
        try {
          cesiumViewerRef.current.dataSources.remove(starlinkHeatmapSourceRef.current);
          starlinkHeatmapSourceRef.current = null;
          console.log('🗑️ Starlink heatmap removed (unchecked)');
        } catch (error) {
          console.error('❌ Error removing Starlink heatmap:', error);
          starlinkHeatmapSourceRef.current = null;
        }
      }
      return; // 로딩하지 않음
    }

    // 체크 활성화 시: 기존 제거 후 새로 로딩
    const loadStarlinkHeatmap = async () => {
      if (!cesiumViewerRef.current) return;

      try {
        // CRITICAL: Remove existing heatmap BEFORE loading new style (synchronous removal)
        if (starlinkHeatmapSourceRef.current) {
          cesiumViewerRef.current.dataSources.remove(starlinkHeatmapSourceRef.current);
          starlinkHeatmapSourceRef.current = null;
          console.log('🗑️ Starlink heatmap removed (style change)');
        }

        console.log(`🗺️ Loading Starlink quality heatmap (${heatmapStyle})...`);
        const czmlData = await getHeatmapCZML(
          selectedSessionId,
          'starlink',
          heatmapStyle,
          selectedFlightId !== null ? selectedFlightId : undefined,
          (heatmapStyle === 'hexagon' || heatmapStyle === 'voxel') ? {
            resolution: hexagonResolution,
            aggregation: hexagonAggregation,
            altitude_bin_size: hexagonAltitudeBinSize
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
      } catch (error) {
        // 🛡️ Silently ignore heatmap errors (bad data should not crash UI)
        console.error('❌ Failed to load Starlink heatmap (silently ignored):', error);
      }
    };

    loadStarlinkHeatmap();

    // Cleanup function (컴포넌트 unmount 또는 dependency 변경 시)
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
  }, [selectedSessionId, starlinkHeatmap, heatmapStyle, selectedFlightId, hexagonResolution, hexagonAggregation, hexagonAltitudeBinSize]);

  // Combined Heatmap 로드 및 토글
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    // 체크 해제 시 즉시 cleanup (동기적으로)
    if (!combinedHeatmap) {
      if (combinedHeatmapSourceRef.current && cesiumViewerRef.current) {
        try {
          cesiumViewerRef.current.dataSources.remove(combinedHeatmapSourceRef.current);
          combinedHeatmapSourceRef.current = null;
          console.log('🗑️ Combined heatmap removed (unchecked)');
        } catch (error) {
          console.error('❌ Error removing Combined heatmap:', error);
          combinedHeatmapSourceRef.current = null;
        }
      }
      return; // 로딩하지 않음
    }

    // 체크 활성화 시: 기존 제거 후 새로 로딩
    const loadCombinedHeatmap = async () => {
      if (!cesiumViewerRef.current) return;

      try {
        // CRITICAL: Remove existing heatmap BEFORE loading new style (synchronous removal)
        if (combinedHeatmapSourceRef.current) {
          cesiumViewerRef.current.dataSources.remove(combinedHeatmapSourceRef.current);
          combinedHeatmapSourceRef.current = null;
          console.log('🗑️ Combined heatmap removed (style change)');
        }

        console.log(`🗺️ Loading Combined quality heatmap (${heatmapStyle})...`);
        const czmlData = await getHeatmapCZML(
          selectedSessionId,
          'combined',
          heatmapStyle,
          selectedFlightId !== null ? selectedFlightId : undefined,
          (heatmapStyle === 'hexagon' || heatmapStyle === 'voxel') ? {
            resolution: hexagonResolution,
            aggregation: hexagonAggregation,
            altitude_bin_size: hexagonAltitudeBinSize
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
      } catch (error) {
        // 🛡️ Silently ignore heatmap errors (bad data should not crash UI)
        console.error('❌ Failed to load Combined heatmap (silently ignored):', error);
      }
    };

    loadCombinedHeatmap();

    // Cleanup function (컴포넌트 unmount 또는 dependency 변경 시)
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
  }, [selectedSessionId, combinedHeatmap, heatmapStyle, selectedFlightId, hexagonResolution, hexagonAggregation, hexagonAltitudeBinSize]);

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
        // 🛡️ Silently ignore cell tower errors
        console.error('❌ Failed to load cell tower data (silently ignored):', error);
        setCellTowerData(null);
      }
    };

    loadCellTowers();
  }, [selectedSessionId, showCellTowers, selectedFlightId]);

  // OpenCellID 기지국 데이터 로드
  useEffect(() => {
    if (!selectedSessionId || !showOpenCellIDTowers) {
      setOpenCellIDTowerData(null);
      return;
    }

    const loadOpenCellIDTowers = async () => {
      try {
        console.log('🔵 Loading OpenCellID tower data...');
        const data = await getCellTowersOpenCellID(selectedSessionId, {
          radio: 'LTE',
          use_cache: true,
          flight_id: selectedFlightId !== null ? selectedFlightId : undefined
        });
        setOpenCellIDTowerData(data);
        console.log(`✅ OpenCellID tower data loaded: ${data.features?.length || 0} towers`);
      } catch (error) {
        console.error('❌ Failed to load OpenCellID tower data (silently ignored):', error);
        setOpenCellIDTowerData(null);
      }
    };

    loadOpenCellIDTowers();
  }, [selectedSessionId, showOpenCellIDTowers, selectedFlightId]);

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

      // Check if this tower is GPS-based estimation (vs OpenCellID)
      const isGPSBased = props.id?.startsWith('GPS-') || false;
      const isConnected = props.is_connected === true;
      const isLGUPlus = props.operator === 'LG U+' || props.mnc === 6;

      // Color by operator: LG U+ = yellow, GPS-based = red, OpenCellID = blue
      const iconColor = isLGUPlus ? '#f1c40f' : (isGPSBased ? '#ff4444' : '#3498db');
      const iconSize = isGPSBased ? 40 : 28; // Larger for GPS-based towers

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
            ${isLGUPlus ? '<b style="color: #f1c40f;">🟡 LG U+</b><br/>' : (isGPSBased ? '<b style="color: #ff4444;">🔴 GPS-BASED ESTIMATION</b><br/>' : '<b style="color: #3498db;">🔵 OpenCellID Data</b><br/>')}
            ${isConnected ? '<b style="color: #00ff00;">✅ CONNECTED DURING FLIGHT</b><br/>' : ''}
            <b>Cell ID:</b> ${props.id}<br/>
            <b>Radio:</b> ${props.radio}<br/>
            <b>Operator:</b> ${props.operator || 'Unknown'}<br/>
            <b>MCC:</b> ${props.mcc} <b>MNC:</b> ${props.mnc}<br/>
            <b>Location:</b> ${typeof lat === 'number' && !isNaN(lat) ? lat.toFixed(5) : 'N/A'}, ${typeof lon === 'number' && !isNaN(lon) ? lon.toFixed(5) : 'N/A'}
          </div>
        `
      });

      cellTowerEntitiesRef.current.push(towerEntity);
    });

    console.log(`✅ ${cellTowerEntitiesRef.current.length} cell tower entities rendered`);
  }, [cellTowerData, showCellTowers]);

  // OpenCellID 기지국 시각화 (파란색)
  useEffect(() => {
    if (!cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    const Cesium = window.Cesium;

    // 기존 OpenCellID 기지국 엔티티 제거
    openCellIDTowerEntitiesRef.current.forEach(entity => {
      cesiumViewerRef.current.entities.remove(entity);
    });
    openCellIDTowerEntitiesRef.current = [];

    if (!openCellIDTowerData || !showOpenCellIDTowers || !openCellIDTowerData.features) {
      return;
    }

    console.log(`🔵 Rendering ${openCellIDTowerData.features.length} OpenCellID towers...`);

    openCellIDTowerData.features.forEach((feature: any) => {
      const coords = feature.geometry.coordinates;
      const props = feature.properties;
      const lon = coords[0];
      const lat = coords[1];
      const isLGUPlus = props.operator === 'LG U+' || props.mnc === 6;

      // Color by operator: LG U+ = yellow, others = blue
      const iconColor = isLGUPlus ? '#f1c40f' : '#3498db';

      const svgIcon = `data:image/svg+xml;base64,${btoa(`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="10" fill="${iconColor}" stroke="#fff" stroke-width="1.5"/>
  <path d="M12 6V18" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M9 9H12" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M12 9H15" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M9 12H12" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M12 12H15" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
</svg>`)}`;

      const towerEntity = cesiumViewerRef.current.entities.add({
        position: Cesium.Cartesian3.fromDegrees(lon, lat, 10),
        billboard: {
          image: svgIcon,
          width: 24,
          height: 24,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND
        },
        description: `
          <div style="font-family: monospace; font-size: 12px;">
            <b>📡 OpenCellID Tower</b><br/>
            ${isLGUPlus ? '<b style="color: #f1c40f;">🟡 LG U+</b><br/>' : '<b style="color: #3498db;">🔵 OpenCellID Database</b><br/>'}
            <b>Radio:</b> ${props.radio || 'LTE'}<br/>
            <b>Operator:</b> ${props.operator || 'Unknown'}<br/>
            <b>MCC:</b> ${props.mcc} <b>MNC:</b> ${props.mnc}<br/>
            <b>LAC:</b> ${props.lac} <b>CID:</b> ${props.cid}<br/>
            <b>Range:</b> ${props.range ? Math.round(props.range) + 'm' : 'N/A'}<br/>
            <b>Samples:</b> ${props.samples || 0}<br/>
            <b>Location:</b> ${typeof lat === 'number' && !isNaN(lat) ? lat.toFixed(5) : 'N/A'}, ${typeof lon === 'number' && !isNaN(lon) ? lon.toFixed(5) : 'N/A'}
          </div>
        `
      });

      openCellIDTowerEntitiesRef.current.push(towerEntity);
    });

    console.log(`✅ ${openCellIDTowerEntitiesRef.current.length} OpenCellID tower entities rendered`);
  }, [openCellIDTowerData, showOpenCellIDTowers]);

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
          color_by: 'starlink_latency',  // Always use latency (SNR no longer provided by Starlink API)
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
        // 🛡️ Silently ignore satellite direction errors
        console.error('❌ Failed to load satellite direction arrows (silently ignored):', error);
      }
    };

    loadSatelliteDirection();
  }, [selectedSessionId, selectedFlightId, showSatelliteDirection, pathColorMode]);

  // Load tower connections
  useEffect(() => {
    // 🚨 DEBUG: Check why useEffect is not loading tower connections
    console.log('🔍 Tower connections useEffect triggered:', {
      selectedSessionId,
      hasCesiumViewer: !!cesiumViewerRef.current,
      hasCesiumGlobal: typeof window.Cesium !== 'undefined',
      showTowerConnections
    });

    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined' || !showTowerConnections) {
      console.warn('⚠️ Tower connections skipped due to conditions:', {
        noSessionId: !selectedSessionId,
        noCesiumViewer: !cesiumViewerRef.current,
        noCesiumGlobal: typeof window.Cesium === 'undefined',
        toggleOff: !showTowerConnections
      });

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

        console.log('📦 Tower connections CZML data loaded:', czmlData ? `${czmlData.length} items` : 'empty');

        if (!czmlData || czmlData.length === 0) {
          console.warn('⚠️ No tower connections data returned from API');
          return;
        }

        // Load CZML into Cesium
        console.log('🔄 Loading CZML into Cesium...');
        const dataSource = await Cesium.CzmlDataSource.load(czmlData);
        console.log('✅ CZML loaded, adding to data sources...');

        cesiumViewerRef.current.dataSources.add(dataSource);
        towerConnectionsSourceRef.current = dataSource;

        console.log('✅ Tower connections rendered successfully');
      } catch (error) {
        // 🛡️ CRITICAL: Show detailed error for debugging
        console.error('❌ Failed to load tower connections:', error);
        console.error('Error details:', {
          message: error instanceof Error ? error.message : 'Unknown error',
          stack: error instanceof Error ? error.stack : undefined
        });
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
              text: `Signal Loss\n${typeof duration_seconds === 'number' && !isNaN(duration_seconds) ? duration_seconds.toFixed(1) : 'N/A'}s`,
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
                <b>Duration:</b> ${typeof duration_seconds === 'number' && !isNaN(duration_seconds) ? duration_seconds.toFixed(2) : 'N/A'} seconds<br/>
                <b>Status:</b> ${label}<br/>
                <b>LTE Poor:</b> ${lte_poor ? 'Yes' : 'No'}${segment.avg_lte_rsrp !== null && typeof segment.avg_lte_rsrp === 'number' && !isNaN(segment.avg_lte_rsrp) ? ` (${segment.avg_lte_rsrp.toFixed(1)} dBm)` : ''}<br/>
                <b>Starlink Poor:</b> ${starlink_poor ? 'Yes' : 'No'}${segment.avg_starlink_latency !== null && typeof segment.avg_starlink_latency === 'number' && !isNaN(segment.avg_starlink_latency) ? ` (${segment.avg_starlink_latency.toFixed(1)} ms)` : ''}<br/>
                <b>Location:</b> ${typeof center_lat === 'number' && !isNaN(center_lat) ? center_lat.toFixed(5) : 'N/A'}, ${typeof center_lon === 'number' && !isNaN(center_lon) ? center_lon.toFixed(5) : 'N/A'}<br/>
                <b>Altitude:</b> ${typeof center_altitude === 'number' && !isNaN(center_altitude) ? center_altitude.toFixed(2) : 'N/A'} m
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
        // 🛡️ Silently ignore signal loss segment errors
        console.error('❌ Failed to load signal loss segments (silently ignored):', error);
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
      marker.title = `Signal Loss: ${typeof segment.duration_seconds === 'number' && !isNaN(segment.duration_seconds) ? segment.duration_seconds.toFixed(1) : 'N/A'}s`;

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
        hexagonAltitudeBinSize={hexagonAltitudeBinSize}
        onHexagonResolutionChange={setHexagonResolution}
        onHexagonAggregationChange={setHexagonAggregation}
        onHexagonAltitudeBinSizeChange={setHexagonAltitudeBinSize}
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
        showOpenCellIDTowers={showOpenCellIDTowers}
        onOpenCellIDTowersToggle={setShowOpenCellIDTowers}
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

      {/* Attitude Analysis Button */}
      {selectedSessionId && (
        <button
          onClick={() => setShowAttitudeAnalysis(true)}
          className="absolute bottom-4 left-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-2 rounded-lg shadow-lg hover:from-blue-700 hover:to-indigo-700 transition-all z-10 text-sm font-medium flex items-center gap-2"
        >
          <span>Attitude Analysis</span>
          <span className="text-xs opacity-80">(Pitch+Elevation)</span>
        </button>
      )}

      {/* Attitude Analysis Panel */}
      <AttitudeAnalysisPanel
        sessionId={selectedSessionId}
        flightId={selectedFlightId}
        isVisible={showAttitudeAnalysis}
        onClose={() => setShowAttitudeAnalysis(false)}
      />

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
