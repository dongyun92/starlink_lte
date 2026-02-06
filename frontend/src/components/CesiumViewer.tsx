import { useEffect, useRef, useState } from 'react';
import { getCZMLData } from '@/services/api';
import { DataLayerControl } from './DataLayerControl';

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
  const lteEntityRef = useRef<any>(null);
  const starlinkEntityRef = useRef<any>(null);

  const [cameraMode, setCameraMode] = useState<CameraMode>('free');
  const [lteLayers, setLteLayers] = useState<boolean>(true);
  const [starlinkLayers, setStarlinkLayers] = useState<boolean>(true);

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

        // CZML 데이터 가져오기 (듀얼 모드)
        const czmlData = await getCZMLData(selectedSessionId, {
          sample_rate: 1,
          color_by: 'dual',
        });

        console.log('📦 CZML data loaded:', czmlData);

        // CZML 데이터 소스 생성 및 추가
        const Cesium = window.Cesium;
        const dataSource = await Cesium.CzmlDataSource.load(czmlData);
        czmlDataSourceRef.current = dataSource;

        await cesiumViewerRef.current.dataSources.add(dataSource);

        // CZML 데이터에서 엔티티 정보 추출
        // czmlData[0]: document header
        // czmlData[1]: lte_path (polyline)
        // czmlData[2]: starlink_path (polyline)
        // czmlData[3]: aircraft (position with animation)
        const lteEntityId = czmlData[1].id;
        const starlinkEntityId = czmlData[2].id;
        const aircraftEntityId = czmlData[3].id;
        const firstPosition = czmlData[3].position.cartographicDegrees;
        const lon = firstPosition[1];
        const lat = firstPosition[2];
        const alt = firstPosition[3];

        // Entity 참조 저장
        const entities = dataSource.entities.values;
        const lteEntity = entities.find((e: any) => e.id === lteEntityId);
        const starlinkEntity = entities.find((e: any) => e.id === starlinkEntityId);
        const aircraft = entities.find((e: any) => e.id === aircraftEntityId);

        lteEntityRef.current = lteEntity;
        starlinkEntityRef.current = starlinkEntity;
        aircraftEntityRef.current = aircraft;

        console.log(`📍 First position: lon=${lon}, lat=${lat}, alt=${alt}`);

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

        // 타임라인 정지 상태로 활성화 (사용자가 수동으로 재생)
        cesiumViewerRef.current.clock.shouldAnimate = false;

        console.log('✅ Flight path visualization complete');
        console.log('⏸️ Timeline ready (paused)');
      } catch (error) {
        console.error('❌ Failed to load flight data:', error);
      }
    };

    loadFlightData();
  }, [selectedSessionId]);

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

  // LTE 레이어 토글 효과
  useEffect(() => {
    if (!lteEntityRef.current) return;

    if (lteEntityRef.current.polyline) {
      lteEntityRef.current.polyline.show = lteLayers;
      console.log(`🔴 LTE layer: ${lteLayers ? 'visible' : 'hidden'}`);
    }
  }, [lteLayers]);

  // Starlink 레이어 토글 효과
  useEffect(() => {
    if (!starlinkEntityRef.current) return;

    if (starlinkEntityRef.current.polyline) {
      starlinkEntityRef.current.polyline.show = starlinkLayers;
      console.log(`🔵 Starlink layer: ${starlinkLayers ? 'visible' : 'hidden'}`);
    }
  }, [starlinkLayers]);

  const toggleCameraMode = () => {
    setCameraMode((prev) => (prev === 'free' ? 'track' : 'free'));
  };

  return (
    <div className={className}>
      {/* 데이터 레이어 컨트롤 */}
      <DataLayerControl
        lteLayers={lteLayers}
        starlinkLayers={starlinkLayers}
        onLteToggle={setLteLayers}
        onStarlinkToggle={setStarlinkLayers}
      />

      {/* 카메라 모드 전환 버튼 */}
      <div className="absolute top-20 right-4 z-10">
        <button
          onClick={toggleCameraMode}
          className={`px-4 py-2 rounded-lg shadow-lg font-medium transition-all ${
            cameraMode === 'track'
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-gray-800 hover:bg-gray-700 text-white'
          }`}
        >
          {cameraMode === 'track' ? '📹 추적 모드' : '🎮 자유 시점'}
        </button>
      </div>

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
