import React from 'react';

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
  return (
    <div className="absolute top-4 left-4 bg-white rounded-lg shadow-lg p-4 z-10">
      <h3 className="text-lg font-bold mb-3">Data Layers</h3>

      {/* LTE Layer Control */}
      <div className="mb-4">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={lteLayers}
            onChange={(e) => onLteToggle(e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
          />
          <span className="font-medium">LTE Signal (RSRP)</span>
        </label>

        {lteLayers && (
          <div className="mt-2 ml-6 space-y-1">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-red-500 rounded"></div>
              <span className="text-sm text-gray-600">&lt; -110 dBm (Very Poor)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-orange-500 rounded"></div>
              <span className="text-sm text-gray-600">-110 ~ -100 dBm (Poor)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-yellow-500 rounded"></div>
              <span className="text-sm text-gray-600">-100 ~ -90 dBm (Fair)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-green-300 rounded"></div>
              <span className="text-sm text-gray-600">-90 ~ -80 dBm (Good)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span className="text-sm text-gray-600">&gt; -80 dBm (Excellent)</span>
            </div>
          </div>
        )}
      </div>

      {/* Starlink Layer Control */}
      <div className="mb-4">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={starlinkLayers}
            onChange={(e) => onStarlinkToggle(e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
          />
          <span className="font-medium">Starlink Signal (SNR)</span>
        </label>

        {starlinkLayers && (
          <div className="mt-2 ml-6 space-y-1">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 rounded" style={{ backgroundColor: 'rgb(0, 0, 139)' }}></div>
              <span className="text-sm text-gray-600">&lt; 3 dB (Very Poor)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span className="text-sm text-gray-600">3 ~ 5 dB (Poor)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 rounded" style={{ backgroundColor: 'rgb(135, 206, 235)' }}></div>
              <span className="text-sm text-gray-600">5 ~ 8 dB (Fair)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-cyan-500 rounded"></div>
              <span className="text-sm text-gray-600">8 ~ 12 dB (Good)</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-white border border-gray-300 rounded"></div>
              <span className="text-sm text-gray-600">&gt; 12 dB (Excellent)</span>
            </div>
          </div>
        )}
      </div>

      {/* Separator */}
      <div className="border-t border-gray-300 my-4"></div>

      {/* Quality Heatmaps Section */}
      <h3 className="text-lg font-bold mb-3">Quality Heatmaps</h3>

      {/* Heatmap Style Selector */}
      <div className="mb-4 ml-2">
        <p className="text-xs font-semibold text-gray-700 mb-2">Visualization Style:</p>
        <div className="space-y-2">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="radio"
              value="point"
              checked={heatmapStyle === 'point'}
              onChange={() => onHeatmapStyleChange('point')}
              className="w-3 h-3 text-blue-600"
            />
            <span className="text-sm text-gray-700">Points (Detailed)</span>
          </label>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="radio"
              value="voxel"
              checked={heatmapStyle === 'voxel'}
              onChange={() => onHeatmapStyleChange('voxel')}
              className="w-3 h-3 text-blue-600"
            />
            <span className="text-sm text-gray-700">Voxels (Clean Grid)</span>
          </label>
        </div>
      </div>

      {/* LTE Heatmap */}
      <div className="mb-3">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={lteHeatmap}
            onChange={(e) => onLteHeatmapToggle(e.target.checked)}
            className="w-4 h-4 text-red-600 rounded focus:ring-red-500"
          />
          <span className="font-medium">LTE Quality Heatmap</span>
        </label>
      </div>

      {/* Starlink Heatmap */}
      <div className="mb-3">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={starlinkHeatmap}
            onChange={(e) => onStarlinkHeatmapToggle(e.target.checked)}
            className="w-4 h-4 text-cyan-600 rounded focus:ring-cyan-500"
          />
          <span className="font-medium">Starlink Quality Heatmap</span>
        </label>
      </div>

      {/* Combined Heatmap */}
      <div className="mb-4">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={combinedHeatmap}
            onChange={(e) => onCombinedHeatmapToggle(e.target.checked)}
            className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
          />
          <span className="font-medium">Combined Quality (Redundancy)</span>
        </label>
      </div>

      {/* Unified Color Legend (shown if any heatmap is enabled) */}
      {(lteHeatmap || starlinkHeatmap || combinedHeatmap) && (
        <div className="mt-2 ml-6 space-y-1">
          <p className="text-xs font-semibold text-gray-700 mb-1">Quality Score Legend:</p>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-red-500 rounded"></div>
            <span className="text-sm text-gray-600">0-20 (Very Poor)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-orange-500 rounded"></div>
            <span className="text-sm text-gray-600">20-40 (Poor)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-yellow-500 rounded"></div>
            <span className="text-sm text-gray-600">40-60 (Fair)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-green-300 rounded"></div>
            <span className="text-sm text-gray-600">60-80 (Good)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-green-500 rounded"></div>
            <span className="text-sm text-gray-600">80-100 (Excellent)</span>
          </div>
        </div>
      )}
    </div>
  );
};
