import React, { useState } from 'react';
import type { FlightScenario, FlightSession } from '@/types/flight';

interface UnifiedControlPanelProps {
  // Session controls
  sessions: FlightSession[];
  selectedSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;

  // Heatmap controls
  lteHeatmap: boolean;
  starlinkHeatmap: boolean;
  combinedHeatmap: boolean;
  heatmapStyle: 'point' | 'voxel';
  onLteHeatmapToggle: (enabled: boolean) => void;
  onStarlinkHeatmapToggle: (enabled: boolean) => void;
  onCombinedHeatmapToggle: (enabled: boolean) => void;
  onHeatmapStyleChange: (style: 'point' | 'voxel') => void;

  // Flight scenario controls
  scenarios: FlightScenario[];
  selectedFlightId: number | null;
  onFlightSelect: (flightId: number | null) => void;

  // Camera controls
  cameraMode: 'free' | 'track';
  onCameraModeToggle: () => void;

  // Path color controls
  pathColorMode: 'altitude' | 'lte' | 'starlink' | 'speed';
  onPathColorModeChange: (mode: 'altitude' | 'lte' | 'starlink' | 'speed') => void;
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
  scenarios,
  selectedFlightId,
  onFlightSelect,
  cameraMode,
  onCameraModeToggle,
  pathColorMode,
  onPathColorModeChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
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
                {sessions.map((session) => (
                  <option key={session.id} value={session.id}>
                    {session.name} ({session.file_count.flight_logs} flights)
                  </option>
                ))}
              </select>
            </label>
          </div>

          {/* Camera Mode */}
          <div className="pb-3 border-b">
            <button
              onClick={onCameraModeToggle}
              className={`w-full px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                cameraMode === 'track'
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-gray-800 hover:bg-gray-700 text-white'
              }`}
            >
              {cameraMode === 'track' ? '📹 추적 모드' : '🎮 자유 시점'}
            </button>
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
                      Flight {scenario.flight_id + 1}: {scenario.scenario_name} ({scenario.data_points.toLocaleString()})
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
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="lte"
                  checked={pathColorMode === 'lte'}
                  onChange={() => onPathColorModeChange('lte')}
                  className="w-3 h-3"
                />
                <span className="text-xs">LTE Signal (Strong ↔ Weak)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="starlink"
                  checked={pathColorMode === 'starlink'}
                  onChange={() => onPathColorModeChange('starlink')}
                  className="w-3 h-3"
                />
                <span className="text-xs">Starlink Signal (Strong ↔ Weak)</span>
              </label>
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
            </div>

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
        </div>
      )}
    </div>
  );
};
