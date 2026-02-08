import React, { useState } from 'react';
import type { FlightScenario } from '@/types/flight';

interface UnifiedControlPanelProps {
  // Layer controls
  lteLayers: boolean;
  starlinkLayers: boolean;
  onLteToggle: (enabled: boolean) => void;
  onStarlinkToggle: (enabled: boolean) => void;

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
}

export const UnifiedControlPanel: React.FC<UnifiedControlPanelProps> = ({
  lteLayers,
  starlinkLayers,
  onLteToggle,
  onStarlinkToggle,
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

          {/* Signal Layers */}
          <div className="space-y-2 pb-3 border-b">
            <div className="text-xs font-bold text-gray-700 mb-2">Signal Layers</div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={lteLayers}
                onChange={(e) => onLteToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs flex-1">LTE Signal</span>
              <button
                onClick={() => toggleSection('lte')}
                className="text-xs text-gray-500 hover:text-gray-700 px-1"
              >
                {expandedSection === 'lte' ? '▼' : '▶'}
              </button>
            </label>

            {expandedSection === 'lte' && (
              <div className="ml-5 space-y-0.5 text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 bg-red-500 rounded-sm"></div>
                  <span>&lt; -110 dBm</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 bg-orange-500 rounded-sm"></div>
                  <span>-110 ~ -100</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 bg-yellow-500 rounded-sm"></div>
                  <span>-100 ~ -90</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 bg-green-400 rounded-sm"></div>
                  <span>-90 ~ -80</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 bg-green-600 rounded-sm"></div>
                  <span>&gt; -80 dBm</span>
                </div>
              </div>
            )}

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={starlinkLayers}
                onChange={(e) => onStarlinkToggle(e.target.checked)}
                className="w-3 h-3"
              />
              <span className="text-xs flex-1">Starlink Signal</span>
              <button
                onClick={() => toggleSection('starlink')}
                className="text-xs text-gray-500 hover:text-gray-700 px-1"
              >
                {expandedSection === 'starlink' ? '▼' : '▶'}
              </button>
            </label>

            {expandedSection === 'starlink' && (
              <div className="ml-5 space-y-0.5 text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 bg-blue-900 rounded-sm"></div>
                  <span>&lt; 3 dB</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 bg-blue-500 rounded-sm"></div>
                  <span>3 ~ 5 dB</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 bg-sky-400 rounded-sm"></div>
                  <span>5 ~ 8 dB</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 bg-cyan-400 rounded-sm"></div>
                  <span>8 ~ 12 dB</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 bg-cyan-600 rounded-sm"></div>
                  <span>&gt; 12 dB</span>
                </div>
              </div>
            )}
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
