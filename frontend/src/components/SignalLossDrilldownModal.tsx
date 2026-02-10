import React from 'react';
import type { SignalLossSegment } from '@/services/api';

interface SignalLossDrilldownModalProps {
  segment: SignalLossSegment | null;
  isOpen: boolean;
  onClose: () => void;
  onJumpToLocation: (lat: number, lon: number, altitude: number) => void;
}

export const SignalLossDrilldownModal: React.FC<SignalLossDrilldownModalProps> = ({
  segment,
  isOpen,
  onClose,
  onJumpToLocation,
}) => {
  if (!isOpen || !segment) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(1)}s`;
  };

  const formatDateTime = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getStatusLabel = (): string => {
    if (segment.lte_poor && segment.starlink_poor) {
      return 'Both Systems Poor';
    } else if (segment.lte_poor) {
      return 'LTE Poor';
    } else if (segment.starlink_poor) {
      return 'Starlink Poor';
    }
    return 'Signal Quality Issue';
  };

  const getStatusColor = (): string => {
    if (segment.lte_poor && segment.starlink_poor) {
      return 'bg-red-500';
    } else if (segment.lte_poor || segment.starlink_poor) {
      return 'bg-orange-500';
    }
    return 'bg-yellow-500';
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[200]"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-red-500 to-orange-500 text-white px-6 py-4 rounded-t-lg flex justify-between items-center">
          <h2 className="text-xl font-bold">Signal Loss Details</h2>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-200 text-2xl font-bold leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Status Badge */}
          <div className="flex items-center gap-3">
            <div className={`${getStatusColor()} text-white px-4 py-2 rounded-full text-sm font-bold`}>
              {getStatusLabel()}
            </div>
            <div className="text-gray-600 text-sm">
              Duration: <span className="font-bold text-gray-900">{formatDuration(segment.duration_seconds)}</span>
            </div>
          </div>

          {/* Time Information */}
          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 mb-3">⏱️ Time Information</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Start Time:</span>
                <span className="font-mono text-gray-900">{formatDateTime(segment.start_time)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">End Time:</span>
                <span className="font-mono text-gray-900">{formatDateTime(segment.end_time)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Duration:</span>
                <span className="font-bold text-gray-900">{formatDuration(segment.duration_seconds)}</span>
              </div>
            </div>
          </div>

          {/* Signal Quality */}
          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 mb-3">📊 Signal Quality</h3>
            <div className="grid grid-cols-2 gap-4">
              {/* LTE Quality */}
              <div className={`border-l-4 ${segment.lte_poor ? 'border-red-500 bg-red-50' : 'border-green-500 bg-green-50'} p-3 rounded`}>
                <div className="text-xs font-semibold text-gray-600 mb-1">LTE Status</div>
                <div className={`text-lg font-bold ${segment.lte_poor ? 'text-red-700' : 'text-green-700'}`}>
                  {segment.lte_poor ? 'Poor' : 'Good'}
                </div>
                {segment.avg_lte_rsrp !== null && (
                  <div className="text-xs text-gray-600 mt-1">
                    RSRP: <span className="font-mono font-semibold">{segment.avg_lte_rsrp.toFixed(1)} dBm</span>
                  </div>
                )}
              </div>

              {/* Starlink Quality */}
              <div className={`border-l-4 ${segment.starlink_poor ? 'border-red-500 bg-red-50' : 'border-green-500 bg-green-50'} p-3 rounded`}>
                <div className="text-xs font-semibold text-gray-600 mb-1">Starlink Status</div>
                <div className={`text-lg font-bold ${segment.starlink_poor ? 'text-red-700' : 'text-green-700'}`}>
                  {segment.starlink_poor ? 'Poor' : 'Good'}
                </div>
                {segment.avg_starlink_latency !== null && (
                  <div className="text-xs text-gray-600 mt-1">
                    Latency: <span className="font-mono font-semibold">{segment.avg_starlink_latency.toFixed(1)} ms</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Location Information */}
          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 mb-3">📍 Location</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Latitude:</span>
                <span className="font-mono text-gray-900">{segment.center_lat.toFixed(6)}°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Longitude:</span>
                <span className="font-mono text-gray-900">{segment.center_lon.toFixed(6)}°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Altitude:</span>
                <span className="font-mono text-gray-900">{segment.center_altitude.toFixed(2)} m</span>
              </div>
            </div>
          </div>

          {/* Data Points */}
          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-bold text-gray-700 mb-3">📈 Data Points</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Start Index:</span>
                <span className="font-mono text-gray-900">{segment.start_index}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">End Index:</span>
                <span className="font-mono text-gray-900">{segment.end_index}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Total Data Points:</span>
                <span className="font-bold text-gray-900">{segment.end_index - segment.start_index + 1}</span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4 border-t">
            <button
              onClick={() => onJumpToLocation(segment.center_lat, segment.center_lon, segment.center_altitude)}
              className="flex-1 bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              Jump to Location
            </button>
            <button
              onClick={onClose}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
