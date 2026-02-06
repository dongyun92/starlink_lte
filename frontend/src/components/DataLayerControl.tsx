import React from 'react';

interface DataLayerControlProps {
  lteLayers: boolean;
  starlinkLayers: boolean;
  onLteToggle: (enabled: boolean) => void;
  onStarlinkToggle: (enabled: boolean) => void;
}

export const DataLayerControl: React.FC<DataLayerControlProps> = ({
  lteLayers,
  starlinkLayers,
  onLteToggle,
  onStarlinkToggle,
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
      <div>
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
    </div>
  );
};
