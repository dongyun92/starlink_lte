import React, { useState } from 'react';
import type { FlightScenario, FlightSession } from '@/types/flight';

// UTC ISO string → KST { date: 'MM/DD', time: 'HH:MM' } (UTC+9)
function toKST(isoStr: string): { date: string; time: string } | null {
  try {
    const d = new Date(isoStr.replace(' ', 'T'));
    if (isNaN(d.getTime())) return null;
    const kst = new Date(d.getTime() + 9 * 60 * 60 * 1000);
    const mo = String(kst.getUTCMonth() + 1).padStart(2, '0');
    const dy = String(kst.getUTCDate()).padStart(2, '0');
    const h  = String(kst.getUTCHours()).padStart(2, '0');
    const m  = String(kst.getUTCMinutes()).padStart(2, '0');
    return { date: `${mo}/${dy}`, time: `${h}:${m}` };
  } catch {
    return null;
  }
}

function formatTimeRange(timeRange: { start: string; end: string } | null): string {
  if (!timeRange) return '';
  const s = toKST(timeRange.start);
  const e = toKST(timeRange.end);
  if (!s || !e) return '';
  // 날짜가 같으면 날짜 한번만, 다르면 각각 표시
  if (s.date === e.date) {
    return ` ${s.date} ${s.time}~${e.time}`;
  }
  return ` ${s.date} ${s.time}~${e.date} ${e.time}`;
}
import { CustomQualityBuilder } from './CustomQualityBuilder';

interface UnifiedControlPanelProps {
  // Session controls
  sessions: FlightSession[];
  selectedSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;

  // Heatmap controls
  lteHeatmap: boolean;
  starlinkHeatmap: boolean;
  combinedHeatmap: boolean;
  heatmapStyle: 'point' | 'voxel' | 'hexagon';
  onLteHeatmapToggle: (enabled: boolean) => void;
  onStarlinkHeatmapToggle: (enabled: boolean) => void;
  onCombinedHeatmapToggle: (enabled: boolean) => void;
  onHeatmapStyleChange: (style: 'point' | 'voxel' | 'hexagon') => void;

  // Hexagon heatmap controls
  hexagonResolution: number;
  hexagonAggregation: 'mean' | 'max' | 'min' | 'median';
  hexagonAltitudeBinSize: number;
  onHexagonResolutionChange: (resolution: number) => void;
  onHexagonAggregationChange: (aggregation: 'mean' | 'max' | 'min' | 'median') => void;
  onHexagonAltitudeBinSizeChange: (size: number) => void;

  // Flight scenario controls
  scenarios: FlightScenario[];
  selectedFlightId: number | null;
  onFlightSelect: (flightId: number | null) => void;

  // Camera controls
  cameraMode: 'free' | 'track';
  onCameraModeToggle: () => void;

  // Path color controls
  pathColorMode: 'altitude' | 'speed' |
    'pitch' | 'roll' | 'pitch_performance' |
    'combined_connectivity' |
    'lte_quality_combined' | 'lte_rsrp' | 'lte_sinr' | 'lte_rsrq' | 'lte_band' |
    'starlink_quality_combined' | 'starlink_latency' |
    'starlink_packet_loss' | 'starlink_throughput_down' | 'starlink_throughput_up' |
    'starlink_obstruction' | 'starlink_uptime';
  onPathColorModeChange: (mode: 'altitude' | 'speed' |
    'pitch' | 'roll' | 'pitch_performance' |
    'combined_connectivity' |
    'lte_quality_combined' | 'lte_rsrp' | 'lte_sinr' | 'lte_rsrq' | 'lte_band' |
    'starlink_quality_combined' | 'starlink_latency' |
    'starlink_packet_loss' | 'starlink_throughput_down' | 'starlink_throughput_up' |
    'starlink_obstruction' | 'starlink_uptime') => void;
  onCustomMetricsChange: (metrics: Record<string, number> | null) => void;
  colorMetadata: {column: string; min: number; max: number; unit: string} | null;
  heatmapMetadata: {lteColumn: string | null; starlinkColumn: string | null};

  // Cell tower controls (GPS-based estimation, red)
  showCellTowers: boolean;
  onCellTowersToggle: (enabled: boolean) => void;


  // Analytics controls
  showAnalytics: boolean;
  onAnalyticsToggle: (enabled: boolean) => void;

  // KPI Dashboard controls
  showKPIDashboard: boolean;
  onKPIDashboardToggle: (enabled: boolean) => void;

  // Root Cause Panel controls
  showRootCausePanel: boolean;
  onRootCausePanelToggle: (enabled: boolean) => void;

  // Satellite direction controls
  showSatelliteDirection: boolean;
  onSatelliteDirectionToggle: (enabled: boolean) => void;

  // Tower connections controls
  showTowerConnections: boolean;
  onTowerConnectionsToggle: (enabled: boolean) => void;

  // Signal loss controls
  showSignalLoss: boolean;
  onSignalLossToggle: (enabled: boolean) => void;

  // Timeline controls
  isPlaying: boolean;
  playbackSpeed: number;
  currentTime: string;
  onPlayPause: () => void;
  onSpeedChange: (speed: number) => void;
}

export const UnifiedControlPanel: React.FC<UnifiedControlPanelProps> = ({
  sessions,
  selectedSessionId,
  onSessionSelect,
  lteHeatmap,
  starlinkHeatmap,
  combinedHeatmap,
  heatmapStyle,
  onLteHeatmapToggle,
  onStarlinkHeatmapToggle,
  onCombinedHeatmapToggle,
  onHeatmapStyleChange,
  hexagonResolution,
  hexagonAggregation,
  hexagonAltitudeBinSize,
  onHexagonResolutionChange,
  onHexagonAggregationChange,
  onHexagonAltitudeBinSizeChange,
  scenarios,
  selectedFlightId,
  onFlightSelect,
  cameraMode,
  onCameraModeToggle,
  pathColorMode,
  onPathColorModeChange,
  onCustomMetricsChange,
  colorMetadata,
  heatmapMetadata,
  showCellTowers,
  onCellTowersToggle,
  showSatelliteDirection,
  onSatelliteDirectionToggle,
  showTowerConnections,
  onTowerConnectionsToggle,
  showSignalLoss,
  onSignalLossToggle,
  isPlaying,
  playbackSpeed,
  currentTime,
  onPlayPause,
  onSpeedChange,
  showAnalytics,
  onAnalyticsToggle,
  showKPIDashboard,
  onKPIDashboardToggle,
  showRootCausePanel,
  onRootCausePanelToggle,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showCustomBuilder, setShowCustomBuilder] = useState(false);
  const [customBuilderType, setCustomBuilderType] = useState<'lte' | 'starlink'>('starlink');

  // Determine main color category
  const isLteMode = pathColorMode.startsWith('lte_');
  const isStarlinkMode = pathColorMode.startsWith('starlink_');

  // Handle custom quality builder
  const handleCustomQualityConfirm = (metrics: Record<string, number>) => {
    console.log('Custom metrics selected:', metrics);
    setShowCustomBuilder(false);
    // Set custom metrics and trigger combined mode
    onCustomMetricsChange(metrics);
    if (customBuilderType === 'starlink') {
      onPathColorModeChange('starlink_quality_combined');
    } else {
      onPathColorModeChange('lte_quality_combined');
    }
  };

  return (
    <div className="absolute top-4 left-4 bg-white rounded-lg shadow-xl z-10 max-w-[300px]">
      {/* Header with collapse button */}
      <div className="flex items-center justify-between p-3 border-b bg-gray-50 rounded-t-lg">
        <h3 className="text-sm font-bold text-gray-800">Controls</h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-gray-600 hover:text-gray-800 text-sm font-bold"
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {isExpanded && (
        <div className="p-3 space-y-3 max-h-[calc(100vh-120px)] overflow-y-auto">
          {/* Session Selection */}
          <div className="pb-3 border-b">
            <label className="block">
              <span className="text-xs font-bold text-gray-700 mb-1 block">Session</span>
              <select
                value={selectedSessionId || ''}
                onChange={(e) => onSessionSelect(e.target.value)}
                className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
              >
                <option value="" disabled>세션을 선택하세요</option>
                {sessions.map((session) => (
                  <option key={session.id} value={session.id}>
                    {session.name}{formatTimeRange(session.time_range)} ({session.file_count.flight_logs}flights)
                  </option>
                ))}
              </select>
            </label>
          </div>

          {/* Flight Scenario Selection */}
          {scenarios.length > 1 && (
            <div className="pb-3 border-b">
              <label className="block">
                <span className="text-xs font-bold text-gray-700 mb-1 block">Flight Scenario</span>
                <select
                  value={selectedFlightId === null ? 'all' : selectedFlightId.toString()}
                  onChange={(e) => {
                    const value = e.target.value;
                    onFlightSelect(value === 'all' ? null : parseInt(value, 10));
                  }}
                  className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">
                    All Flights ({scenarios.reduce((sum, s) => sum + s.data_points, 0).toLocaleString()})
                  </option>
                  {scenarios.map((scenario) => (
                    <option key={scenario.flight_id} value={scenario.flight_id}>
                      Flight {scenario.flight_id + 1}: {scenario.scenario_name}{formatTimeRange(scenario.time_range)} ({scenario.data_points.toLocaleString()})
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {/* Path Color Mode */}
          <div className="pb-3 border-b">
            <div className="text-xs font-bold text-gray-700 mb-2">Path Color Mode</div>
            <div className="space-y-1.5">

              {/* Combined Connectivity Score */}
              <div className="bg-purple-50 border border-purple-200 rounded p-1.5 mb-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    value="combined_connectivity"
                    checked={pathColorMode === 'combined_connectivity'}
                    onChange={() => onPathColorModeChange('combined_connectivity')}
                    className="w-3 h-3"
                  />
                  <span className="text-xs font-semibold text-purple-800">통합 연결 품질 (LTE + Starlink)</span>
                </label>
                <div className="text-[10px] text-purple-600 mt-0.5 ml-5">LTE RSRP + Starlink DL 쓰루풋 평균</div>
              </div>

              {/* Altitude */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="altitude"
                  checked={pathColorMode === 'altitude'}
                  onChange={() => onPathColorModeChange('altitude')}
                  className="w-3 h-3"
                />
                <span className="text-xs">Altitude (High ↔ Low)</span>
              </label>

              {/* Speed */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="speed"
                  checked={pathColorMode === 'speed'}
                  onChange={() => onPathColorModeChange('speed')}
                  className="w-3 h-3"
                />
                <span className="text-xs">Speed (Fast ↔ Slow)</span>
              </label>

              {/* Aircraft Attitude - Expandable */}
              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={pathColorMode === 'pitch' || pathColorMode === 'roll' || pathColorMode === 'pitch_performance'}
                    onChange={() => onPathColorModeChange('pitch_performance')}
                    className="w-3 h-3"
                  />
                  <span className="text-xs font-semibold">Aircraft Attitude ▼</span>
                </label>
                {(pathColorMode === 'pitch' || pathColorMode === 'roll' || pathColorMode === 'pitch_performance') && (
                  <div className="ml-5 mt-1 space-y-1">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'pitch_performance'}
                        onChange={() => onPathColorModeChange('pitch_performance')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Pitch Performance (Level=Bad) ⭐</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'pitch'}
                        onChange={() => onPathColorModeChange('pitch')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Pitch Angle (Nose Up/Down)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'roll'}
                        onChange={() => onPathColorModeChange('roll')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Roll Angle (Left/Right Tilt)</span>
                    </label>
                  </div>
                )}
              </div>

              {/* LTE Quality - Expandable */}
              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={pathColorMode.startsWith('lte_')}
                    onChange={() => onPathColorModeChange('lte_quality_combined')}
                    className="w-3 h-3"
                  />
                  <span className="text-xs font-semibold">LTE Quality ▼</span>
                </label>
                {pathColorMode.startsWith('lte_') && (
                  <div className="ml-5 mt-1 space-y-1">
                    {/* Custom Combined Button */}
                    <button
                      onClick={() => {
                        setCustomBuilderType('lte');
                        setShowCustomBuilder(true);
                      }}
                      className="w-full text-left px-2 py-1 text-xs bg-blue-50 hover:bg-blue-100 rounded border border-blue-200 text-blue-700 font-medium"
                    >
                      🎛️ Custom Combined (Click to configure)
                    </button>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'lte_quality_combined'}
                        onChange={() => onPathColorModeChange('lte_quality_combined')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Combined (RSRP + SINR + RSRQ) ⭐</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'lte_rsrp'}
                        onChange={() => onPathColorModeChange('lte_rsrp')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">RSRP (Signal Strength)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'lte_sinr'}
                        onChange={() => onPathColorModeChange('lte_sinr')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">SINR (Signal Quality)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'lte_rsrq'}
                        onChange={() => onPathColorModeChange('lte_rsrq')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">RSRQ (Overall Quality)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'lte_band'}
                        onChange={() => onPathColorModeChange('lte_band')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">LTE Band (주파수 대역)</span>
                    </label>
                    {/* Band 범례 (lte_band 모드일 때만 표시) */}
                    {pathColorMode === 'lte_band' && (
                      <div className="ml-1 mt-1 p-1.5 bg-gray-50 rounded border border-gray-200 space-y-0.5">
                        <div className="text-[9px] font-semibold text-gray-500 mb-1">Band 색상 범례</div>
                        {[
                          { band: 'BAND 1', freq: '2100 MHz', color: '#2ecc71', label: '도심' },
                          { band: 'BAND 3', freq: '1800 MHz', color: '#9b59b6', label: '도심' },
                          { band: 'BAND 5', freq: '850 MHz',  color: '#3498db', label: '광역' },
                          { band: 'BAND 7', freq: '2600 MHz', color: '#f39c12', label: '고속' },
                          { band: 'BAND 8', freq: '900 MHz',  color: '#e74c3c', label: '광역' },
                        ].map(({ band, freq, color, label }) => (
                          <div key={band} className="flex items-center gap-1.5">
                            <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ backgroundColor: color }} />
                            <span className="text-[9px] text-gray-600 font-medium">{band}</span>
                            <span className="text-[9px] text-gray-400">{freq} {label}</span>
                          </div>
                        ))}
                        <div className="flex items-center gap-1.5">
                          <div className="w-3 h-3 rounded-sm flex-shrink-0 bg-gray-400" />
                          <span className="text-[9px] text-gray-600 font-medium">Unknown</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Starlink Quality - Expandable */}
              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={pathColorMode.startsWith('starlink_')}
                    onChange={() => onPathColorModeChange('starlink_quality_combined')}
                    className="w-3 h-3"
                  />
                  <span className="text-xs font-semibold">Starlink Quality ▼</span>
                </label>
                {pathColorMode.startsWith('starlink_') && (
                  <div className="ml-5 mt-1 space-y-1">
                    {/* Custom Combined Button */}
                    <button
                      onClick={() => {
                        setCustomBuilderType('starlink');
                        setShowCustomBuilder(true);
                      }}
                      className="w-full text-left px-2 py-1 text-xs bg-blue-50 hover:bg-blue-100 rounded border border-blue-200 text-blue-700 font-medium"
                    >
                      🎛️ Custom Combined (Click to configure)
                    </button>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_quality_combined'}
                        onChange={() => onPathColorModeChange('starlink_quality_combined')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Combined (Auto) ⭐</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_latency'}
                        onChange={() => onPathColorModeChange('starlink_latency')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Latency (Response Time)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_packet_loss'}
                        onChange={() => onPathColorModeChange('starlink_packet_loss')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">POP Ping Drop Rate (인터넷 연결)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_throughput_down'}
                        onChange={() => onPathColorModeChange('starlink_throughput_down')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Download Speed</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_throughput_up'}
                        onChange={() => onPathColorModeChange('starlink_throughput_up')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Upload Speed</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_connection_quality'}
                        onChange={() => onPathColorModeChange('starlink_connection_quality')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Connection Quality</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_roaming'}
                        onChange={() => onPathColorModeChange('starlink_roaming')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Roaming Status</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_alerts_any'}
                        onChange={() => onPathColorModeChange('starlink_alerts_any')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">⚠️ Alerts (All)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer ml-4">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_alert_roaming'}
                        onChange={() => onPathColorModeChange('starlink_alert_roaming')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs text-gray-600">↳ Roaming</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer ml-4">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_alert_install_pending'}
                        onChange={() => onPathColorModeChange('starlink_alert_install_pending')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs text-gray-600">↳ Install Pending</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_obstruction'}
                        onChange={() => onPathColorModeChange('starlink_obstruction')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Obstruction (Blocked)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        checked={pathColorMode === 'starlink_uptime'}
                        onChange={() => onPathColorModeChange('starlink_uptime')}
                        className="w-2.5 h-2.5"
                      />
                      <span className="text-xs">Connection Uptime</span>
                    </label>
                  </div>
                )}
              </div>
            </div>

            {/* Color Legend for selected mode */}
            <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
              <div className="font-semibold mb-1">Color Legend:</div>
              <div>
                {/* Altitude: Terrain colormap (Green → Brown → Gray/White) */}
                {pathColorMode === 'altitude' && (
                  <div className="h-3 rounded mb-1" style={{
                    background: 'linear-gradient(to right, rgb(51,153,51), rgb(102,153,0), rgb(153,153,0), rgb(204,153,51), rgb(204,153,102), rgb(204,204,153), rgb(224,224,224), rgb(245,245,245))'
                  }}></div>
                )}
                {/* Speed: Turbo colormap (Blue → Cyan → Green → Yellow → Red) */}
                {pathColorMode === 'speed' && (
                  <div className="h-3 rounded mb-1" style={{
                    background: 'linear-gradient(to right, rgb(48,18,59), rgb(62,73,137), rgb(33,145,140), rgb(53,183,121), rgb(144,215,67), rgb(253,231,37), rgb(246,173,59), rgb(229,109,61), rgb(189,48,57))'
                  }}></div>
                )}
                {/* Combined Connectivity: Red(bad) → Yellow → Green(good) */}
                {pathColorMode === 'combined_connectivity' && (
                  <div className="h-3 rounded mb-1" style={{
                    background: 'linear-gradient(to right, #d73027, #f46d43, #fdae61, #fee08b, #ffffbf, #d9ef8b, #a6d96a, #66bd63, #1a9850)'
                  }}></div>
                )}
                {/* LTE/Starlink Quality: Traffic Light (Red → Yellow → Green) */}
                {(pathColorMode.startsWith('lte_') || pathColorMode.startsWith('starlink_')) && pathColorMode !== 'lte_band' && (
                  <div className="h-3 rounded mb-1" style={{
                    background: 'linear-gradient(to right, rgb(215,25,28), rgb(253,174,97), rgb(255,255,191), rgb(166,217,106), rgb(26,150,65))'
                  }}></div>
                )}
                {/* LTE Band: 카테고리형 - 그라디언트 없음 */}
                {pathColorMode === 'lte_band' && (
                  <div className="flex gap-1 flex-wrap">
                    {[
                      { band: 'B1', color: '#2ecc71' },
                      { band: 'B3', color: '#9b59b6' },
                      { band: 'B5', color: '#3498db' },
                      { band: 'B7', color: '#f39c12' },
                      { band: 'B8', color: '#e74c3c' },
                    ].map(({ band, color }) => (
                      <div key={band} className="flex items-center gap-0.5">
                        <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color }} />
                        <span className="text-[9px] text-gray-600">{band}</span>
                      </div>
                    ))}
                  </div>
                )}
                {pathColorMode !== 'lte_band' && (
                <div className="flex justify-between text-[10px] text-gray-600">
                  {pathColorMode === 'combined_connectivity' ? (
                    <>
                      <span className="text-blue-600">◀ 불량 (LTE약+SL낮음)</span>
                      <span className="text-red-600">(LTE강+SL높음) 우수 ▶</span>
                    </>
                  ) : colorMetadata ? (
                    <>
                      <span>{colorMetadata.min.toFixed(1)} {colorMetadata.unit}</span>
                      <span>{colorMetadata.max.toFixed(1)} {colorMetadata.unit}</span>
                    </>
                  ) : (
                    <>
                      <span>Low</span>
                      <span>High</span>
                    </>
                  )}
                </div>
                )}
              </div>
            </div>
          </div>

          {/* Quality Heatmaps */}
          <div className="space-y-2">
            <div className="text-xs font-bold text-gray-700 mb-2">Quality Heatmaps</div>

            <div className="flex gap-2 mb-2">
              <label className="flex items-center gap-1 cursor-pointer text-xs">
                <input
                  type="radio"
                  value="point"
                  checked={heatmapStyle === 'point'}
                  onChange={() => onHeatmapStyleChange('point')}
                  className="w-3 h-3"
                />
                <span>Points</span>
              </label>
              <label className="flex items-center gap-1 cursor-pointer text-xs">
                <input
                  type="radio"
                  value="voxel"
                  checked={heatmapStyle === 'voxel'}
                  onChange={() => onHeatmapStyleChange('voxel')}
                  className="w-3 h-3"
                />
                <span>Voxels</span>
              </label>
              <label className="flex items-center gap-1 cursor-pointer text-xs">
                <input
                  type="radio"
                  value="hexagon"
                  checked={heatmapStyle === 'hexagon'}
                  onChange={() => onHeatmapStyleChange('hexagon')}
                  className="w-3 h-3"
                />
                <span>Hexagons</span>
              </label>
            </div>

            {/* Voxel & Hexagon controls */}
            {(heatmapStyle === 'voxel' || heatmapStyle === 'hexagon') && (
              <div className="bg-blue-50 p-2 rounded border border-blue-200 space-y-2">
                <div className="text-xs font-semibold text-blue-900">
                  {heatmapStyle === 'voxel' ? 'Voxel Settings' : 'Hexagon Settings'}
                </div>

                {/* Hexagon-only: Resolution Selector */}
                {heatmapStyle === 'hexagon' && (
                  <div>
                    <label className="block text-[10px] text-gray-700 mb-1">
                      Cell Size ({hexagonResolution === 7 ? '1.22km' : hexagonResolution === 8 ? '461m' : hexagonResolution === 9 ? '174m' : '66m'} edge)
                    </label>
                    <select
                      value={hexagonResolution}
                      onChange={(e) => onHexagonResolutionChange(parseInt(e.target.value, 10))}
                      className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                    >
                      <option value={7}>7 - Very Large (1.22km)</option>
                      <option value={8}>8 - Large (461m)</option>
                      <option value={9}>9 - Medium (174m) ⭐</option>
                      <option value={10}>10 - Small (66m)</option>
                    </select>
                    <div className="text-[9px] text-gray-500 mt-1">
                      Smaller = More cells, slower
                    </div>
                  </div>
                )}

                {/* Hexagon-only: Aggregation Selector */}
                {heatmapStyle === 'hexagon' && (
                  <div>
                    <label className="block text-[10px] text-gray-700 mb-1">
                      Aggregation Method
                    </label>
                    <select
                      value={hexagonAggregation}
                      onChange={(e) => onHexagonAggregationChange(e.target.value as 'mean' | 'max' | 'min' | 'median')}
                      className="w-full px-2 py-1 text-xs border border-gray-300 rounded"
                    >
                      <option value="mean">Mean (Average) ⭐</option>
                      <option value="max">Max (Best Quality)</option>
                      <option value="min">Min (Worst Quality)</option>
                      <option value="median">Median (Middle Value)</option>
                    </select>
                  </div>
                )}

                {/* Shared: Altitude Bin Size Slider */}
                <div>
                  <label className="block text-[10px] text-gray-700 mb-1">
                    Altitude Bin Size: {hexagonAltitudeBinSize}m (3D Voxel Layers)
                  </label>
                  <input
                    type="range"
                    min={10}
                    max={100}
                    step={5}
                    value={hexagonAltitudeBinSize}
                    onChange={(e) => onHexagonAltitudeBinSizeChange(parseInt(e.target.value, 10))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-[9px] text-gray-500">
                    <span>10m (Fine)</span>
                    <span>100m (Coarse)</span>
                  </div>
                  <div className="text-[9px] text-blue-700 mt-1">
                    ℹ️ Creates altitude layers (e.g., 0-25m, 25-50m, etc.)
                  </div>
                </div>
              </div>
            )}

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={lteHeatmap}
                onChange={(e) => onLteHeatmapToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs">LTE Heatmap</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={starlinkHeatmap}
                onChange={(e) => onStarlinkHeatmapToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs">Starlink Heatmap</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={combinedHeatmap}
                onChange={(e) => onCombinedHeatmapToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs">Combined Heatmap</span>
            </label>
          </div>

          {/* Cell Towers */}
          <div className="space-y-2 pt-3 border-t">
            <div className="text-xs font-bold text-gray-700 mb-2">📡 기지국 & Satellite</div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showCellTowers}
                onChange={(e) => onCellTowersToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs">📡 고흥 기지국 (과기부 공식)</span>
            </label>
            <p className="text-[10px] text-gray-500 ml-5">
              SKT·KT·LGU+ 341개 위치 — 과기부 공식
            </p>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showSatelliteDirection}
                onChange={(e) => onSatelliteDirectionToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs">🛰️ Satellite Direction Arrows</span>
            </label>
            <p className="text-[10px] text-gray-500 ml-5">
              3D arrows showing Starlink satellite direction with signal quality colors
            </p>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showTowerConnections}
                onChange={(e) => onTowerConnectionsToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs">📡 LTE Tower Connections</span>
            </label>
            <p className="text-[10px] text-gray-500 ml-5">
              Real-time connection lines to LTE towers, colored by signal strength
            </p>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showSignalLoss}
                onChange={(e) => onSignalLossToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs">🔴 Signal Loss Markers</span>
            </label>
            <p className="text-[10px] text-gray-500 ml-5">
              3D cylinder markers highlighting poor signal quality segments
            </p>
          </div>

          {/* Timeline Controls */}
          <div className="space-y-2 pt-3 border-t">
            <div className="text-xs font-bold text-gray-700 mb-2">⏱️ Timeline Controls</div>

            {/* Camera Mode Toggle */}
            <button
              onClick={onCameraModeToggle}
              className={`w-full px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                cameraMode === 'track'
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-gray-800 hover:bg-gray-700 text-white'
              }`}
            >
              {cameraMode === 'track' ? '추적 모드' : '자유 시점'}
            </button>

            {/* Current Time Display */}
            <div className="text-xs text-gray-600 mb-2">
              <span className="font-mono bg-gray-100 px-2 py-1 rounded">
                {currentTime}
              </span>
            </div>

            {/* Play/Pause Button */}
            <button
              onClick={onPlayPause}
              className="w-full px-3 py-2 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors font-semibold"
            >
              {isPlaying ? 'Pause' : 'Play'}
            </button>

            {/* Playback Speed Controls */}
            <div className="space-y-1">
              <label className="text-[10px] text-gray-600 block">Playback Speed:</label>
              <div className="flex gap-1 flex-wrap">
                {[1, 5, 10, 20, 50].map((speed) => (
                  <button
                    key={speed}
                    onClick={() => onSpeedChange(speed)}
                    className={`px-2 py-1 text-[10px] rounded transition-colors ${
                      playbackSpeed === speed
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                    }`}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
            </div>

            <p className="text-[10px] text-gray-500">
              Control flight path animation playback speed and progress
            </p>
          </div>

          {/* KPI Dashboard */}
          <div className="space-y-2 pt-3 border-t">
            <div className="text-xs font-bold text-gray-700 mb-2">Dashboards</div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showKPIDashboard}
                onChange={(e) => onKPIDashboardToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs">Show KPI Dashboard</span>
            </label>
            <p className="text-[10px] text-gray-500 ml-5">
              Flight metrics, LTE/Starlink quality, signal loss summary
            </p>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showAnalytics}
                onChange={(e) => onAnalyticsToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs">Show Analytics Panel</span>
            </label>
            <p className="text-[10px] text-gray-500 ml-5">
              Time series, distribution, and satellite direction charts
            </p>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showRootCausePanel}
                onChange={(e) => onRootCausePanelToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs">Show Root Cause Analysis</span>
            </label>
            <p className="text-[10px] text-gray-500 ml-5">
              Signal loss by cause, altitude, and flight period analysis
            </p>
          </div>

          {/* Signal Quality Legend */}
          {(lteHeatmap || starlinkHeatmap || combinedHeatmap) && (
            <div className="space-y-2 pt-3 border-t">
              <div className="text-xs font-bold text-gray-700 mb-2">Signal Quality Legend</div>

              {/* LTE Heatmap Legend (Dynamic: RSRP or RSSI based on actual data) */}
              {lteHeatmap && heatmapMetadata.lteColumn === 'lte_rsrp' && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-semibold text-gray-600">LTE Signal Quality (RSRP)</div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#1a9850' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Excellent</div>
                        <div className="text-[9px] text-gray-500">-44 ~ -70 dBm</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#91cf60' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Good</div>
                        <div className="text-[9px] text-gray-500">-70 ~ -85 dBm</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#fee08b' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Fair</div>
                        <div className="text-[9px] text-gray-500">-85 ~ -100 dBm</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#fc8d59' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Poor</div>
                        <div className="text-[9px] text-gray-500">-100 ~ -110 dBm</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#d73027' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Very Poor</div>
                        <div className="text-[9px] text-gray-500">-110 ~ -120 dBm</div>
                      </div>
                    </div>
                  </div>
                  <div className="text-[9px] text-gray-500 mt-2 pt-2 border-t border-gray-200">
                    LTE network quality (RSRP)
                  </div>
                </div>
              )}

              {lteHeatmap && heatmapMetadata.lteColumn === 'lte_rssi' && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-semibold text-gray-600">LTE Signal Quality (RSSI)</div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#1a9850' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Excellent</div>
                        <div className="text-[9px] text-gray-500">-51 ~ -65 dBm</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#91cf60' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Good</div>
                        <div className="text-[9px] text-gray-500">-65 ~ -75 dBm</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#fee08b' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Fair</div>
                        <div className="text-[9px] text-gray-500">-75 ~ -85 dBm</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#fc8d59' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Poor</div>
                        <div className="text-[9px] text-gray-500">-85 ~ -95 dBm</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#d73027' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Very Poor</div>
                        <div className="text-[9px] text-gray-500">-95 ~ -113 dBm</div>
                      </div>
                    </div>
                  </div>
                  <div className="text-[9px] text-gray-500 mt-2 pt-2 border-t border-gray-200">
                    LTE network quality (RSSI)
                  </div>
                </div>
              )}

              {/* Starlink Heatmap Legend (Latency based) */}
              {starlinkHeatmap && heatmapMetadata.starlinkColumn === 'starlink_latency' && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-semibold text-gray-600">Starlink Signal Quality (Latency)</div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#1a9850' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Excellent</div>
                        <div className="text-[9px] text-gray-500">0 - 40 ms</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#91cf60' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Good</div>
                        <div className="text-[9px] text-gray-500">40 - 80 ms</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#fee08b' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Fair</div>
                        <div className="text-[9px] text-gray-500">80 - 120 ms</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#fc8d59' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Poor</div>
                        <div className="text-[9px] text-gray-500">120 - 160 ms</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#d73027' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Very Poor</div>
                        <div className="text-[9px] text-gray-500">160+ ms</div>
                      </div>
                    </div>
                  </div>
                  <div className="text-[9px] text-gray-500 mt-2 pt-2 border-t border-gray-200">
                    Starlink satellite quality (Latency)
                  </div>
                </div>
              )}

              {/* Combined Heatmap Legend */}
              {combinedHeatmap && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-semibold text-gray-600">Combined Signal Quality</div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#1a9850' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Excellent</div>
                        <div className="text-[9px] text-gray-500">Best signal quality</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#91cf60' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Good</div>
                        <div className="text-[9px] text-gray-500">Strong signal</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#fee08b' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Fair</div>
                        <div className="text-[9px] text-gray-500">Moderate signal</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#fc8d59' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Poor</div>
                        <div className="text-[9px] text-gray-500">Weak signal</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded border border-gray-600" style={{ backgroundColor: '#d73027' }} />
                      <div className="flex-1">
                        <div className="text-[10px] font-semibold text-gray-800">Very Poor</div>
                        <div className="text-[9px] text-gray-500">Very weak signal</div>
                      </div>
                    </div>
                  </div>
                  <div className="text-[9px] text-gray-500 mt-2 pt-2 border-t border-gray-200">
                    Best available signal (LTE or Starlink)
                    {heatmapMetadata.lteColumn && heatmapMetadata.starlinkColumn && (
                      <div className="mt-1">
                        Using: {heatmapMetadata.lteColumn.replace('lte_', '').toUpperCase()} + {heatmapMetadata.starlinkColumn.replace('starlink_', '').toUpperCase()}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Custom Quality Builder Modal */}
      {showCustomBuilder && (
        <CustomQualityBuilder
          type={customBuilderType}
          onConfirm={handleCustomQualityConfirm}
          onCancel={() => setShowCustomBuilder(false)}
        />
      )}
    </div>
  );
};
