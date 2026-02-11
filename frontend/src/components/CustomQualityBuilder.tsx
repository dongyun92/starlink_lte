import React, { useState, useEffect } from 'react';

export interface MetricOption {
  id: string;
  label: string;
  enabled: boolean;
  weight: number;
  description: string;
}

interface CustomQualityBuilderProps {
  type: 'lte' | 'starlink';
  onConfirm: (metrics: Record<string, number>) => void;
  onCancel: () => void;
}

export const CustomQualityBuilder: React.FC<CustomQualityBuilderProps> = ({
  type,
  onConfirm,
  onCancel
}) => {
  const [autoNormalize, setAutoNormalize] = useState(true);

  // Define metric options based on type
  const getDefaultMetrics = (): MetricOption[] => {
    if (type === 'lte') {
      return [
        { id: 'rsrp', label: 'RSRP', enabled: true, weight: 30, description: 'Signal Strength' },
        { id: 'sinr', label: 'SINR', enabled: true, weight: 50, description: 'Signal Quality' },
        { id: 'rsrq', label: 'RSRQ', enabled: true, weight: 20, description: 'Overall Quality' },
      ];
    } else {
      return [
        { id: 'latency', label: 'Latency', enabled: true, weight: 40, description: 'Round-trip Delay' },
        { id: 'packet_loss', label: 'Packet Loss', enabled: true, weight: 30, description: 'Drop Rate' },
        { id: 'obstruction', label: 'Obstruction', enabled: true, weight: 30, description: 'Blocked Signal' },
        { id: 'throughput_down', label: 'Download', enabled: false, weight: 0, description: 'Downlink Speed' },
        { id: 'throughput_up', label: 'Upload', enabled: false, weight: 0, description: 'Uplink Speed' },
        { id: 'uptime', label: 'Uptime', enabled: false, weight: 0, description: 'Connection Time' },
      ];
    }
  };

  const [metrics, setMetrics] = useState<MetricOption[]>(getDefaultMetrics());

  // Calculate total weight
  const totalWeight = metrics.reduce((sum, m) => m.enabled ? sum + m.weight : sum, 0);

  // Toggle metric enabled/disabled
  const handleToggle = (id: string) => {
    setMetrics(metrics.map(m =>
      m.id === id ? { ...m, enabled: !m.enabled } : m
    ));
  };

  // Update weight
  const handleWeightChange = (id: string, newWeight: number) => {
    if (autoNormalize) {
      // Auto-normalize: distribute remaining weight
      const targetMetric = metrics.find(m => m.id === id);
      if (!targetMetric) return;

      const otherEnabledMetrics = metrics.filter(m => m.id !== id && m.enabled);
      const otherTotalWeight = otherEnabledMetrics.reduce((sum, m) => sum + m.weight, 0);
      const remainingWeight = 100 - newWeight;

      setMetrics(metrics.map(m => {
        if (m.id === id) {
          return { ...m, weight: newWeight };
        } else if (m.enabled && otherTotalWeight > 0) {
          // Proportionally distribute remaining weight
          const proportion = m.weight / otherTotalWeight;
          return { ...m, weight: Math.round(proportion * remainingWeight) };
        }
        return m;
      }));
    } else {
      setMetrics(metrics.map(m =>
        m.id === id ? { ...m, weight: newWeight } : m
      ));
    }
  };

  // Handle confirm
  const handleConfirm = () => {
    const selectedMetrics = metrics
      .filter(m => m.enabled)
      .reduce((acc, m) => ({ ...acc, [m.id]: m.weight / 100 }), {});

    if (Object.keys(selectedMetrics).length === 0) {
      alert('Please select at least one metric');
      return;
    }

    onConfirm(selectedMetrics);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl p-6 max-w-md w-full max-h-[80vh] overflow-y-auto">
        {/* Header */}
        <div className="mb-4">
          <h3 className="text-lg font-bold text-gray-800">
            🎛️ Custom Quality Score Builder
          </h3>
          <p className="text-xs text-gray-600 mt-1">
            {type === 'lte' ? 'LTE Quality Metrics' : 'Starlink Quality Metrics'}
          </p>
        </div>

        {/* Metrics Selection */}
        <div className="space-y-3 mb-4">
          <p className="text-xs font-semibold text-gray-700">Select Metrics (at least 1):</p>

          {metrics.map(metric => (
            <div key={metric.id} className="space-y-1">
              {/* Checkbox + Label */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={metric.enabled}
                  onChange={() => handleToggle(metric.id)}
                  className="w-4 h-4"
                />
                <div className="flex-1">
                  <span className="text-sm font-medium">{metric.label}</span>
                  <span className="text-xs text-gray-500 ml-2">({metric.description})</span>
                </div>
                <span className="text-sm font-bold text-blue-600">{metric.weight}%</span>
              </label>

              {/* Slider */}
              {metric.enabled && (
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={metric.weight}
                  onChange={(e) => handleWeightChange(metric.id, parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
              )}
            </div>
          ))}
        </div>

        {/* Total Weight Display */}
        <div className="mb-4 p-3 bg-gray-100 rounded">
          <div className="flex justify-between items-center">
            <span className="text-sm font-semibold text-gray-700">Total Weight:</span>
            <span className={`text-lg font-bold ${totalWeight === 100 ? 'text-green-600' : 'text-orange-600'}`}>
              {totalWeight}%
            </span>
          </div>
          {totalWeight !== 100 && !autoNormalize && (
            <p className="text-xs text-orange-600 mt-1">⚠️ Total should be 100%</p>
          )}
        </div>

        {/* Auto-normalize Toggle */}
        <div className="mb-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoNormalize}
              onChange={(e) => setAutoNormalize(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm text-gray-700">
              Auto-normalize (자동으로 100%가 되도록 조정)
            </span>
          </label>
        </div>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded font-medium text-sm"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-sm"
          >
            Confirm ✓
          </button>
        </div>
      </div>
    </div>
  );
};
