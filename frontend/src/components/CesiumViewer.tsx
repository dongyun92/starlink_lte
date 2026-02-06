import { useEffect, useRef } from 'react';
import { getCZMLData } from '@/services/api';

interface CesiumViewerProps {
  className?: string;
  selectedSessionId: string | null;
}

/**
 * CesiumViewer 컴포넌트
 * 3D 지구본과 지형, 건물을 렌더링하고 비행 경로를 표시하는 Cesium Viewer
 */
export default function CesiumViewer({ className = 'w-full h-screen', selectedSessionId }: CesiumViewerProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const cesiumViewerRef = useRef<any>(null);
  const czmlDataSourceRef = useRef<any>(null);

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

        // CZML 데이터 가져오기
        const czmlData = await getCZMLData(selectedSessionId, {
          sample_rate: 1,
          color_by: 'altitude',
        });

        console.log('📦 CZML data loaded:', czmlData);

        // CZML 데이터 소스 생성 및 추가
        const Cesium = window.Cesium;
        const dataSource = await Cesium.CzmlDataSource.load(czmlData);
        czmlDataSourceRef.current = dataSource;

        await cesiumViewerRef.current.dataSources.add(dataSource);

        // CZML 데이터에서 첫 번째 좌표 추출
        // czmlData[0]: document header
        // czmlData[1]: flight_path (polyline)
        // czmlData[2]: aircraft (position with animation)
        const aircraftEntity = czmlData[2];
        const firstPosition = aircraftEntity.position.cartographicDegrees;
        const lon = firstPosition[1];
        const lat = firstPosition[2];
        const alt = firstPosition[3];

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

        console.log('✅ Flight path visualization complete');
      } catch (error) {
        console.error('❌ Failed to load flight data:', error);
      }
    };

    loadFlightData();
  }, [selectedSessionId]);

  return (
    <div className={className}>
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
