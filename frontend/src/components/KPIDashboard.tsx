import React, { useState, useEffect, useRef } from 'react';
import { getKPISummary, type KPISummary } from '@/services/api';

interface KPIDashboardProps {
  sessionId: string | null;
}

interface Position {
  x: number;
  y: number;
}

// SVG Icons
const FlightIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M21 16V14L13 9V3.5C13 2.67 12.33 2 11.5 2C10.67 2 10 2.67 10 3.5V9L2 14V16L10 13.5V19L8 20.5V22L11.5 21L15 22V20.5L13 19V13.5L21 16Z" fill="currentColor"/>
  </svg>
);

const LTEIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M17 1H7C5.9 1 5 1.9 5 3V21C5 22.1 5.9 23 7 23H17C18.1 23 19 22.1 19 21V3C19 1.9 18.1 1 17 1ZM17 19H7V5H17V19Z" fill="currentColor"/>
    <rect x="8" y="7" width="2" height="6" fill="currentColor"/>
    <rect x="11" y="9" width="2" height="4" fill="currentColor"/>
    <rect x="14" y="11" width="2" height="2" fill="currentColor"/>
  </svg>
);

const StarlinkIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="2" fill="currentColor"/>
    <path d="M12 2L14 8L20 6L16 12L22 14L16 16L20 22L14 18L12 24L10 18L4 22L8 16L2 14L8 12L4 6L10 8L12 2Z" fill="currentColor"/>
  </svg>
);

const SignalLossIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M23.64 7C22.39 5.76 20.93 4.76 19.32 4.06L17.91 5.47C19.2 6 20.36 6.78 21.33 7.76L23.64 7Z" fill="currentColor"/>
    <path d="M3.41 1.86L2 3.27L4.68 5.95C3.06 6.65 1.61 7.65 0.36 8.89L2.05 10.58C3.06 9.57 4.27 8.76 5.59 8.21L8.97 11.59C7.85 12.05 6.85 12.73 6.03 13.56L7.72 15.25C8.29 14.68 8.97 14.24 9.72 13.95L18.73 22.96L20.14 21.55L3.41 1.86Z" fill="currentColor"/>
    <path d="M12 14C11.45 14 10.93 14.13 10.46 14.36L13.64 17.54C13.87 17.07 14 16.55 14 16C14 14.9 13.1 14 12 14Z" fill="currentColor"/>
  </svg>
);

const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
};

const formatQuality = (quality: string | null): string => {
  if (!quality) return 'N/A';
  return quality.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
};

export const KPIDashboard: React.FC<KPIDashboardProps> = ({ sessionId }) => {
  const [kpi, setKpi] = useState<KPISummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);

  // Draggable state - position from right side
  const [position, setPosition] = useState<Position>({ x: window.innerWidth - 420 - 320, y: 16 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState<Position>({ x: 0, y: 0 });
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) {
      setKpi(null);
      return;
    }

    const loadKPI = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getKPISummary(sessionId);
        setKpi(data);
        console.log(`📊 Loaded KPI summary for session ${sessionId}`);
      } catch (err) {
        console.error('Failed to load KPI summary:', err);
        setError('Failed to load KPI data');
      } finally {
        setLoading(false);
      }
    };

    loadKPI();
  }, [sessionId]);

  // Drag handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (panelRef.current) {
      const rect = panelRef.current.getBoundingClientRect();
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
      setIsDragging(true);
    }
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        setPosition({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffset]);

  if (!sessionId) return null;

  return (
    <div
      ref={panelRef}
      className="absolute bg-white rounded-lg shadow-xl z-[100] w-[320px] flex flex-col"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        cursor: isDragging ? 'grabbing' : 'default'
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-3 border-b bg-gray-50 rounded-t-lg flex-shrink-0 cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
      >
        <h3 className="text-sm font-bold text-gray-800 select-none">Flight KPI Summary</h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-gray-600 hover:text-gray-800 text-sm font-bold"
          onMouseDown={(e) => e.stopPropagation()}
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-4 space-y-3">
          {loading ? (
            <div className="text-center text-gray-500 text-sm py-4">Loading KPI data...</div>
          ) : error ? (
            <div className="text-center text-red-500 text-sm py-4">{error}</div>
          ) : kpi ? (
            <>
              {/* Flight Metrics */}
              <div className="bg-blue-50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="text-blue-600">
                    <FlightIcon />
                  </div>
                  <h4 className="text-xs font-bold text-gray-800">Flight Metrics</h4>
                </div>
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Duration:</span>
                    <span className="font-semibold text-gray-800">{formatDuration(kpi.flight.duration_seconds)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Distance:</span>
                    <span className="font-semibold text-gray-800">{typeof kpi.flight.distance_km === 'number' && !isNaN(kpi.flight.distance_km) ? kpi.flight.distance_km.toFixed(2) : 'N/A'} km</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Max Altitude:</span>
                    <span className="font-semibold text-gray-800">{typeof kpi.flight.max_altitude_m === 'number' && !isNaN(kpi.flight.max_altitude_m) ? kpi.flight.max_altitude_m.toFixed(0) : 'N/A'} m</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Avg Speed:</span>
                    <span className="font-semibold text-gray-800">{typeof kpi.flight.avg_speed_kmh === 'number' && !isNaN(kpi.flight.avg_speed_kmh) ? kpi.flight.avg_speed_kmh.toFixed(1) : 'N/A'} km/h</span>
                  </div>
                </div>
              </div>

              {/* LTE Quality */}
              <div className="bg-purple-50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="text-purple-600">
                    <LTEIcon />
                  </div>
                  <h4 className="text-xs font-bold text-gray-800">LTE Quality</h4>
                </div>
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Avg RSRP:</span>
                    <span className="font-semibold text-gray-800">
                      {kpi.lte.avg_rsrp !== null && typeof kpi.lte.avg_rsrp === 'number' && !isNaN(kpi.lte.avg_rsrp) ? `${kpi.lte.avg_rsrp.toFixed(1)} dBm` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Quality:</span>
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: kpi.lte.color }}
                      />
                      <span className="font-semibold text-gray-800">{formatQuality(kpi.lte.quality)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Starlink Quality */}
              <div className="bg-green-50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="text-green-600">
                    <StarlinkIcon />
                  </div>
                  <h4 className="text-xs font-bold text-gray-800">Starlink Quality</h4>
                </div>
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Avg Latency:</span>
                    <span className="font-semibold text-gray-800">
                      {kpi.starlink.avg_latency !== null && typeof kpi.starlink.avg_latency === 'number' && !isNaN(kpi.starlink.avg_latency) ? `${kpi.starlink.avg_latency.toFixed(1)} ms` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Quality:</span>
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: kpi.starlink.color }}
                      />
                      <span className="font-semibold text-gray-800">{formatQuality(kpi.starlink.quality)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Signal Loss */}
              <div className="bg-red-50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="text-red-600">
                    <SignalLossIcon />
                  </div>
                  <h4 className="text-xs font-bold text-gray-800">Signal Loss</h4>
                </div>
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Percentage:</span>
                    <span className="font-semibold text-gray-800">{typeof kpi.signal_loss.percentage === 'number' && !isNaN(kpi.signal_loss.percentage) ? kpi.signal_loss.percentage.toFixed(1) : 'N/A'}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Segments:</span>
                    <span className="font-semibold text-gray-800">{kpi.signal_loss.segment_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Duration:</span>
                    <span className="font-semibold text-gray-800">{formatDuration(kpi.signal_loss.total_duration_seconds)}</span>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
};
