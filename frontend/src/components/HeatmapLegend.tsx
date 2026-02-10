import React from 'react';

interface HeatmapLegendProps {
  mode: 'lte' | 'starlink' | 'combined' | null;
  lteColumn?: string;
  starlinkColumn?: string;
}

export const HeatmapLegend: React.FC<HeatmapLegendProps> = ({
  mode,
  lteColumn,
  starlinkColumn
}) => {
  if (!mode) return null;

  // Define legend data for each mode
  const getLegendData = () => {
    if (mode === 'lte' || mode === 'combined') {
      if (lteColumn === 'lte_rsrp') {
        return {
          title: 'LTE Signal Quality (RSRP)',
          unit: 'dBm',
          ranges: [
            { color: '#1a9850', label: 'Excellent', range: '-44 ~ -70 dBm' },
            { color: '#91cf60', label: 'Good', range: '-70 ~ -85 dBm' },
            { color: '#fee08b', label: 'Fair', range: '-85 ~ -100 dBm' },
            { color: '#fc8d59', label: 'Poor', range: '-100 ~ -110 dBm' },
            { color: '#d73027', label: 'Very Poor', range: '-110 ~ -120 dBm' }
          ]
        };
      } else if (lteColumn === 'lte_rssi') {
        return {
          title: 'LTE Signal Quality (RSSI)',
          unit: 'dBm',
          ranges: [
            { color: '#1a9850', label: 'Excellent', range: '-51 ~ -65 dBm' },
            { color: '#91cf60', label: 'Good', range: '-65 ~ -75 dBm' },
            { color: '#fee08b', label: 'Fair', range: '-75 ~ -85 dBm' },
            { color: '#fc8d59', label: 'Poor', range: '-85 ~ -95 dBm' },
            { color: '#d73027', label: 'Very Poor', range: '-95 ~ -113 dBm' }
          ]
        };
      }
    }

    if (mode === 'starlink' || mode === 'combined') {
      if (starlinkColumn === 'starlink_snr') {
        return {
          title: 'Starlink Signal Quality (SNR)',
          unit: 'dB',
          ranges: [
            { color: '#1a9850', label: 'Excellent', range: '10+ dB' },
            { color: '#91cf60', label: 'Good', range: '7 - 10 dB' },
            { color: '#fee08b', label: 'Fair', range: '3 - 7 dB' },
            { color: '#fc8d59', label: 'Poor', range: '1 - 3 dB' },
            { color: '#d73027', label: 'Very Poor', range: '0 - 1 dB' }
          ]
        };
      } else if (starlinkColumn === 'starlink_latency') {
        return {
          title: 'Starlink Signal Quality (Latency)',
          unit: 'ms',
          ranges: [
            { color: '#1a9850', label: 'Excellent', range: '0 - 40 ms' },
            { color: '#91cf60', label: 'Good', range: '40 - 80 ms' },
            { color: '#fee08b', label: 'Fair', range: '80 - 120 ms' },
            { color: '#fc8d59', label: 'Poor', range: '120 - 160 ms' },
            { color: '#d73027', label: 'Very Poor', range: '160+ ms' }
          ]
        };
      }
    }

    return null;
  };

  const legendData = getLegendData();
  if (!legendData) return null;

  return (
    <div className="absolute bottom-4 left-4 bg-gray-900/95 backdrop-blur-sm rounded-lg shadow-xl p-3 z-10 min-w-[260px] border border-gray-700">
      <h3 className="text-xs font-bold text-white mb-2.5 flex items-center gap-2">
        <span className="text-base">📊</span>
        {legendData.title}
      </h3>
      <div className="space-y-1.5">
        {legendData.ranges.map((item, idx) => (
          <div key={idx} className="flex items-center gap-2.5">
            <div
              className="w-5 h-5 rounded border border-gray-600 flex-shrink-0"
              style={{ backgroundColor: item.color }}
            />
            <div className="flex-1">
              <div className="text-xs font-semibold text-white">{item.label}</div>
              <div className="text-xs text-gray-400">{item.range}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2.5 pt-2.5 border-t border-gray-700">
        <p className="text-xs text-gray-400">
          {mode === 'combined'
            ? 'Best available signal (LTE or Starlink)'
            : mode === 'lte'
            ? 'LTE network quality'
            : 'Starlink satellite quality'}
        </p>
      </div>
    </div>
  );
};
