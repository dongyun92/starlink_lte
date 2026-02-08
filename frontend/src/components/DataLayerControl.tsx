import React, { useState } from 'react';

interface DataLayerControlProps {
  lteLayers: boolean;
  starlinkLayers: boolean;
  lteHeatmap: boolean;
  starlinkHeatmap: boolean;
  combinedHeatmap: boolean;
  heatmapStyle: 'point' | 'voxel';
  onLteToggle: (enabled: boolean) => void;
  onStarlinkToggle: (enabled: boolean) => void;
  onLteHeatmapToggle: (enabled: boolean) => void;
  onStarlinkHeatmapToggle: (enabled: boolean) => void;
  onCombinedHeatmapToggle: (enabled: boolean) => void;
  onHeatmapStyleChange: (style: 'point' | 'voxel') => void;
}

export const DataLayerControl: React.FC<DataLayerControlProps> = ({
  lteLayers,
  starlinkLayers,
  lteHeatmap,
  starlinkHeatmap,
  combinedHeatmap,
  heatmapStyle,
  onLteToggle,
  onStarlinkToggle,
  onLteHeatmapToggle,
  onStarlinkHeatmapToggle,
  onCombinedHeatmapToggle,
  onHeatmapStyleChange,
}) => {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div className="absolute top-4 left-4 bg-white rounded-lg shadow-lg p-3 z-10 max-w-[280px]">
      <h3 className="text-sm font-bold mb-2">Data Layers</h3>

      {/* LTE Layer Control */}
      <div className="mb-2 border-b pb-2">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={lteLayers}
            onChange={(e) => onLteToggle(e.target.checked)}
            className="w-3 h-3 text-blue-600 rounded"
          />
          <span className="text-sm font-medium flex-1">LTE Signal</span>
          <button
            onClick={() => toggleSection('lte')}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {expandedSection === 'lte' ? '▼' : '▶'}
          </button>
        </label>

        {expandedSection === 'lte' && (
          <div className="mt-2 ml-5 space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded"></div>
              <span className="text-gray-700">&lt; -110 dBm</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-orange-500 rounded"></div>
              <span className="text-gray-700">-110 ~ -100</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-500 rounded"></div>
              <span className="text-gray-700">-100 ~ -90</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-400 rounded"></div>
              <span className="text-gray-700">-90 ~ -80</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-600 rounded"></div>
              <span className="text-gray-700">&gt; -80 dBm</span>
            </div>
          </div>
        )}
      </div>

      {/* Starlink Layer Control */}
      <div className="mb-2 border-b pb-2">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={starlinkLayers}
            onChange={(e) => onStarlinkToggle(e.target.checked)}
            className="w-3 h-3 text-blue-600 rounded"
          />
          <span className="text-sm font-medium flex-1">Starlink Signal</span>
          <button
            onClick={() => toggleSection('starlink')}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {expandedSection === 'starlink' ? '▼' : '▶'}
          </button>
        </label>

        {expandedSection === 'starlink' && (
          <div className="mt-2 ml-5 space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-900 rounded"></div>
              <span className="text-gray-700">&lt; 3 dB</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded"></div>
              <span className="text-gray-700">3 ~ 5 dB</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-sky-400 rounded"></div>
              <span className="text-gray-700">5 ~ 8 dB</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-cyan-400 rounded"></div>
              <span className="text-gray-700">8 ~ 12 dB</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-cyan-600 rounded"></div>
              <span className="text-gray-700">&gt; 12 dB</span>
            </div>
          </div>
        )}
      </div>

      {/* Quality Heatmaps Section */}
      <div className="mb-2">
        <button
          onClick={() => toggleSection('heatmaps')}
          className="flex items-center justify-between w-full text-sm font-bold text-gray-700 hover:text-gray-900"
        >
          <span>Quality Heatmaps</span>
          <span className="text-xs">{expandedSection === 'heatmaps' ? '▼' : '▶'}</span>
        </button>

        {expandedSection === 'heatmaps' && (
          <div className="mt-2 space-y-2">
            {/* Heatmap Style Selector */}
            <div className="mb-2 pb-2 border-b">
              <p className="text-xs font-semibold text-gray-600 mb-1">Style:</p>
              <div className="flex gap-2">
                <label className="flex items-center space-x-1 cursor-pointer text-xs">
                  <input
                    type="radio"
                    value="point"
                    checked={heatmapStyle === 'point'}
                    onChange={() => onHeatmapStyleChange('point')}
                    className="w-3 h-3"
                  />
                  <span>Points</span>
                </label>
                <label className="flex items-center space-x-1 cursor-pointer text-xs">
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
            </div>

            {/* Heatmap Toggles */}
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={lteHeatmap}
                onChange={(e) => onLteHeatmapToggle(e.target.checked)}
                className="w-3 h-3 text-blue-600 rounded"
              />
              <span className="text-xs">LTE Heatmap</span>
            </label>

            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={starlinkHeatmap}
                onChange={(e) => onStarlinkHeatmapToggle(e.target.checked)}
                className="w-3 h-3 text-blue-600 rounded"
              />
              <span className="text-xs">Starlink Heatmap</span>
            </label>

            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={combinedHeatmap}
                onChange={(e) => onCombinedHeatmapToggle(e.target.checked)}
                className="w-3 h-3 text-blue-600 rounded"
              />
              <span className="text-xs">Combined Heatmap</span>
            </label>
          </div>
        )}
      </div>
    </div>
  );
};
