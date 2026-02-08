import { useEffect, useRef, useState } from 'react';
import { getCZMLData, getHeatmapCZML, getFlightScenarios } from '@/services/api';
import type { FlightScenario } from '@/types/flight';
import { UnifiedControlPanel } from './UnifiedControlPanel';

interface CesiumViewerProps {
  className?: string;
  selectedSessionId: string | null;
}

type CameraMode = 'free' | 'track';

/**
 * CesiumViewer 컴포넌트
 * 3D 지구본과 지형, 건물을 렌더링하고 비행 경로를 표시하는 Cesium Viewer
 */
export default function CesiumViewer({ className = 'w-full h-screen', selectedSessionId }: CesiumViewerProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const cesiumViewerRef = useRef<any>(null);
  const czmlDataSourceRef = useRef<any>(null);
  const aircraftEntityRef = useRef<any>(null);
  const lteEntitiesRef = useRef<any[]>([]);
  const starlinkEntitiesRef = useRef<any[]>([]);

  // Heatmap data source refs
  const lteHeatmapSourceRef = useRef<any>(null);
  const starlinkHeatmapSourceRef = useRef<any>(null);
  const combinedHeatmapSourceRef = useRef<any>(null);

  const [cameraMode, setCameraMode] = useState<CameraMode>('free');
  const [lteLayers, setLteLayers] = useState<boolean>(true);
  const [starlinkLayers, setStarlinkLayers] = useState<boolean>(true);

  // Heatmap layer states
  const [lteHeatmap, setLteHeatmap] = useState<boolean>(false);
  const [starlinkHeatmap, setStarlinkHeatmap] = useState<boolean>(false);
  const [combinedHeatmap, setCombinedHeatmap] = useState<boolean>(false);
  const [heatmapStyle, setHeatmapStyle] = useState<'point' | 'voxel'>('point');

  // Flight scenario filtering
  const [flightScenarios, setFlightScenarios] = useState<FlightScenario[]>([]);
  const [selectedFlightId, setSelectedFlightId] = useState<number | null>(null);

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

        // CZML 데이터 가져오기 (듀얼 모드, 최적화된 샘플링)
        const czmlData = await getCZMLData(selectedSessionId, {
          sample_rate: 0.2,  // 5초마다 1개 포인트 (80% 빠름, 5배 적은 데이터)
          color_by: 'dual',
          flight_id: selectedFlightId !== null ? selectedFlightId : undefined,
        });

        console.log('📦 CZML data loaded:', czmlData);

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

        // Find LTE segments (gradient mode: multiple segments with 'lte_path_*_seg*')
        const lteSegments = entities.filter((e: any) => e.id.includes('lte_path_'));
        lteEntitiesRef.current = lteSegments;

        // Find Starlink segments (gradient mode: multiple segments with 'starlink_path_*_seg*')
        const starlinkSegments = entities.filter((e: any) => e.id.includes('starlink_path_'));
        starlinkEntitiesRef.current = starlinkSegments;

        // Determine mode based on entity count
        const isDualMode = lteSegments.length > 0 || starlinkSegments.length > 0;

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

        if (isDualMode) {
          console.log(`📊 Dual path mode: LTE segments=${lteSegments.length}, Starlink segments=${starlinkSegments.length}`);
        } else {
          console.log('⚠️ Single path mode (no LTE/Starlink data)');
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
          clock.shouldAnimate = true;

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
        console.log('▶️ Timeline playing automatically');
      } catch (error) {
        console.error('❌ Failed to load flight data:', error);
      }
    };

    loadFlightData();
  }, [selectedSessionId, selectedFlightId]);

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

  // LTE 레이어 토글 효과 (모든 segment에 적용)
  useEffect(() => {
    if (!lteEntitiesRef.current || lteEntitiesRef.current.length === 0) return;

    lteEntitiesRef.current.forEach((entity: any) => {
      if (entity.polyline) {
        entity.polyline.show = lteLayers;
      }
    });
    console.log(`🔴 LTE layer (${lteEntitiesRef.current.length} segments): ${lteLayers ? 'visible' : 'hidden'}`);
  }, [lteLayers]);

  // Starlink 레이어 토글 효과 (모든 segment에 적용)
  useEffect(() => {
    if (!starlinkEntitiesRef.current || starlinkEntitiesRef.current.length === 0) return;

    starlinkEntitiesRef.current.forEach((entity: any) => {
      if (entity.polyline) {
        entity.polyline.show = starlinkLayers;
      }
    });
    console.log(`🔵 Starlink layer (${starlinkEntitiesRef.current.length} segments): ${starlinkLayers ? 'visible' : 'hidden'}`);
  }, [starlinkLayers]);

  // LTE Heatmap 로드 및 토글
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    const loadLTEHeatmap = async () => {
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
            selectedFlightId !== null ? selectedFlightId : undefined
          );

          const Cesium = window.Cesium;
          const dataSource = await Cesium.CzmlDataSource.load(czmlData);
          lteHeatmapSourceRef.current = dataSource;

          await cesiumViewerRef.current.dataSources.add(dataSource);
          console.log('✅ LTE heatmap loaded');
        } else {
          // Remove heatmap when disabled
          if (lteHeatmapSourceRef.current) {
            cesiumViewerRef.current.dataSources.remove(lteHeatmapSourceRef.current);
            lteHeatmapSourceRef.current = null;
            console.log('🗺️ LTE heatmap removed');
          }
        }
      } catch (error) {
        console.error('❌ Failed to load LTE heatmap:', error);
      }
    };

    loadLTEHeatmap();
  }, [selectedSessionId, lteHeatmap, heatmapStyle, selectedFlightId]);

  // Starlink Heatmap 로드 및 토글
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    const loadStarlinkHeatmap = async () => {
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
            selectedFlightId !== null ? selectedFlightId : undefined
          );

          const Cesium = window.Cesium;
          const dataSource = await Cesium.CzmlDataSource.load(czmlData);
          starlinkHeatmapSourceRef.current = dataSource;

          await cesiumViewerRef.current.dataSources.add(dataSource);
          console.log('✅ Starlink heatmap loaded');
        } else {
          // Remove heatmap when disabled
          if (starlinkHeatmapSourceRef.current) {
            cesiumViewerRef.current.dataSources.remove(starlinkHeatmapSourceRef.current);
            starlinkHeatmapSourceRef.current = null;
            console.log('🗺️ Starlink heatmap removed');
          }
        }
      } catch (error) {
        console.error('❌ Failed to load Starlink heatmap:', error);
      }
    };

    loadStarlinkHeatmap();
  }, [selectedSessionId, starlinkHeatmap, heatmapStyle, selectedFlightId]);

  // Combined Heatmap 로드 및 토글
  useEffect(() => {
    if (!selectedSessionId || !cesiumViewerRef.current || typeof window.Cesium === 'undefined') {
      return;
    }

    const loadCombinedHeatmap = async () => {
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
            selectedFlightId !== null ? selectedFlightId : undefined
          );

          const Cesium = window.Cesium;
          const dataSource = await Cesium.CzmlDataSource.load(czmlData);
          combinedHeatmapSourceRef.current = dataSource;

          await cesiumViewerRef.current.dataSources.add(dataSource);
          console.log('✅ Combined heatmap loaded');
        } else {
          // Remove heatmap when disabled
          if (combinedHeatmapSourceRef.current) {
            cesiumViewerRef.current.dataSources.remove(combinedHeatmapSourceRef.current);
            combinedHeatmapSourceRef.current = null;
            console.log('🗺️ Combined heatmap removed');
          }
        }
      } catch (error) {
        console.error('❌ Failed to load Combined heatmap:', error);
      }
    };

    loadCombinedHeatmap();
  }, [selectedSessionId, combinedHeatmap, heatmapStyle, selectedFlightId]);

  const toggleCameraMode = () => {
    setCameraMode((prev) => (prev === 'free' ? 'track' : 'free'));
  };

  return (
    <div className={className}>
      {/* Unified Control Panel */}
      <UnifiedControlPanel
        lteLayers={lteLayers}
        starlinkLayers={starlinkLayers}
        onLteToggle={setLteLayers}
        onStarlinkToggle={setStarlinkLayers}
        lteHeatmap={lteHeatmap}
        starlinkHeatmap={starlinkHeatmap}
        combinedHeatmap={combinedHeatmap}
        heatmapStyle={heatmapStyle}
        onLteHeatmapToggle={setLteHeatmap}
        onStarlinkHeatmapToggle={setStarlinkHeatmap}
        onCombinedHeatmapToggle={setCombinedHeatmap}
        onHeatmapStyleChange={setHeatmapStyle}
        scenarios={flightScenarios}
        selectedFlightId={selectedFlightId}
        onFlightSelect={setSelectedFlightId}
        cameraMode={cameraMode}
        onCameraModeToggle={toggleCameraMode}
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
