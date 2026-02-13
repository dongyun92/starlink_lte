import React, { useEffect, useState } from 'react';
import { getAttitudeAnalysis, type AttitudeAnalysis, type PitchElevationMatrixItem } from '@/services/api';

interface AttitudeAnalysisPanelProps {
  sessionId: string | null;
  flightId: number | null;
  isVisible: boolean;
  onClose: () => void;
}

// Color helper: success rate to color
const getSuccessColor = (rate: number): string => {
  if (rate >= 70) return 'bg-green-500 text-white';
  if (rate >= 50) return 'bg-yellow-400 text-gray-800';
  if (rate >= 30) return 'bg-orange-400 text-white';
  return 'bg-red-500 text-white';
};

// Color helper: success rate to background color for matrix
const getMatrixCellColor = (rate: number): string => {
  if (rate >= 80) return '#22c55e'; // green-500
  if (rate >= 70) return '#4ade80'; // green-400
  if (rate >= 60) return '#86efac'; // green-300
  if (rate >= 50) return '#fde047'; // yellow-300
  if (rate >= 40) return '#fdba74'; // orange-300
  if (rate >= 30) return '#fb923c'; // orange-400
  if (rate >= 20) return '#f97316'; // orange-500
  return '#ef4444'; // red-500
};

export const AttitudeAnalysisPanel: React.FC<AttitudeAnalysisPanelProps> = ({
  sessionId,
  flightId,
  isVisible,
  onClose,
}) => {
  const [data, setData] = useState<AttitudeAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'matrix' | 'pitch' | 'azimuth'>('matrix');

  useEffect(() => {
    if (!isVisible || !sessionId) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getAttitudeAnalysis(sessionId, {
          flight_id: flightId ?? undefined
        });
        setData(result);
      } catch (err: any) {
        setError(err.message || 'Failed to load attitude analysis');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [sessionId, flightId, isVisible]);

  if (!isVisible) return null;

  // Build matrix grid
  const buildMatrix = () => {
    if (!data?.pitch_elevation_matrix?.length) return null;

    // Get unique pitch and elevation values
    const pitchLabels = ['<-5°', '-5~-2°', '-2~0°', '0~2°', '2~5°', '>5°'];
    const elevLabels = ['<75°', '75-80°', '80-85°', '85-90°', '>90°'];

    // Build lookup map
    const matrixMap = new Map<string, PitchElevationMatrixItem>();
    data.pitch_elevation_matrix.forEach(item => {
      const key = `${item.pitch}|${item.elevation}`;
      matrixMap.set(key, item);
    });

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              <th className="border border-gray-300 bg-gray-100 p-1 text-center font-bold">
                Pitch \ Elev
              </th>
              {elevLabels.map(elev => (
                <th key={elev} className="border border-gray-300 bg-gray-100 p-1 text-center font-medium min-w-[60px]">
                  {elev}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pitchLabels.map(pitch => (
              <tr key={pitch}>
                <td className="border border-gray-300 bg-gray-100 p-1 text-center font-medium">
                  {pitch}
                </td>
                {elevLabels.map(elev => {
                  const key = `${pitch}|${elev}`;
                  const cell = matrixMap.get(key);
                  if (!cell || cell.count < 10) {
                    return (
                      <td key={elev} className="border border-gray-300 bg-gray-50 p-1 text-center text-gray-400">
                        -
                      </td>
                    );
                  }
                  return (
                    <td
                      key={elev}
                      className="border border-gray-300 p-1 text-center font-bold"
                      style={{ backgroundColor: getMatrixCellColor(cell.success_rate) }}
                      title={`Count: ${cell.count}, Avg: ${cell.avg_upload_mbps.toFixed(2)} Mbps`}
                    >
                      <span className="text-white text-shadow">
                        {cell.success_rate.toFixed(0)}%
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-2 text-xs text-gray-500">
          * Values show success rate (% of good connection). Hover for details.
        </div>
      </div>
    );
  };

  // Render pitch/roll stats as horizontal bar chart
  const renderBarChart = (items: { label: string; success_rate: number; count: number }[]) => {
    const maxRate = Math.max(...items.map(i => i.success_rate), 1);

    return (
      <div className="space-y-1">
        {items.map((item, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <div className="w-16 text-xs text-right font-medium text-gray-700">
              {item.label}
            </div>
            <div className="flex-1 h-5 bg-gray-200 rounded relative">
              <div
                className="h-full rounded transition-all"
                style={{
                  width: `${(item.success_rate / 100) * 100}%`,
                  backgroundColor: getMatrixCellColor(item.success_rate)
                }}
              />
              <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-gray-800">
                {item.success_rate.toFixed(0)}%
              </span>
            </div>
            <div className="w-16 text-xs text-gray-500">
              ({item.count.toLocaleString()})
            </div>
          </div>
        ))}
      </div>
    );
  };

  // Render azimuth polar chart (simplified bar chart by direction)
  const renderAzimuthChart = () => {
    if (!data?.azimuth_stats?.length) {
      return <div className="text-gray-500 text-sm">No azimuth data available</div>;
    }

    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const statsMap = new Map(data.azimuth_stats.map(s => [s.direction, s]));

    return (
      <div className="space-y-1">
        {directions.map(dir => {
          const stat = statsMap.get(dir);
          if (!stat || stat.count < 10) {
            return (
              <div key={dir} className="flex items-center gap-2">
                <div className="w-8 text-xs text-right font-medium text-gray-700">{dir}</div>
                <div className="flex-1 h-5 bg-gray-100 rounded" />
                <div className="w-12 text-xs text-gray-400">-</div>
              </div>
            );
          }
          return (
            <div key={dir} className="flex items-center gap-2">
              <div className="w-8 text-xs text-right font-medium text-gray-700">{dir}</div>
              <div className="flex-1 h-5 bg-gray-200 rounded relative">
                <div
                  className="h-full rounded transition-all"
                  style={{
                    width: `${stat.success_rate}%`,
                    backgroundColor: getMatrixCellColor(stat.success_rate)
                  }}
                />
                <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-gray-800">
                  {stat.success_rate.toFixed(0)}%
                </span>
              </div>
              <div className="w-12 text-xs text-gray-500">
                {stat.avg_upload_mbps.toFixed(2)}
              </div>
            </div>
          );
        })}
        <div className="mt-1 text-xs text-gray-500">
          * Bar width = success rate, Right column = avg upload (Mbps)
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-blue-600 to-indigo-600">
          <h2 className="text-lg font-bold text-white">
            Starlink Performance by Aircraft Attitude
          </h2>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-200 text-2xl font-bold"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 120px)' }}>
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
              <span className="ml-2 text-gray-600">Loading analysis...</span>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-4 text-red-700">
              {error}
            </div>
          )}

          {data && !loading && (
            <>
              {/* Summary Stats - Comprehensive Multi-Metric */}
              <div className="grid grid-cols-4 gap-3 mb-4">
                {/* Total Points */}
                <div className="bg-gray-50 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-gray-700">
                    {data.total_points.toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-600">Total Points</div>
                </div>

                {/* Upload Stats */}
                <div className="bg-blue-50 rounded-lg p-3 text-center border-l-4 border-blue-500">
                  <div className="text-lg font-bold text-blue-700">
                    {data.overall_success_rate.toFixed(1)}%
                  </div>
                  <div className="text-xs text-blue-600 font-medium">Upload Success</div>
                  <div className="text-xs text-blue-500 mt-1">
                    avg {data.avg_upload_mbps?.toFixed(2) || '0.00'} / max {data.max_upload_mbps?.toFixed(2) || '0.00'} Mbps
                  </div>
                </div>

                {/* Download Stats */}
                <div className="bg-green-50 rounded-lg p-3 text-center border-l-4 border-green-500">
                  <div className="text-lg font-bold text-green-700">
                    {data.download_success_rate?.toFixed(1) || '0.0'}%
                  </div>
                  <div className="text-xs text-green-600 font-medium">Download Success</div>
                  <div className="text-xs text-green-500 mt-1">
                    avg {data.avg_download_mbps?.toFixed(2) || '0.00'} / max {data.max_download_mbps?.toFixed(2) || '0.00'} Mbps
                  </div>
                </div>

                {/* Latency Stats */}
                <div className="bg-purple-50 rounded-lg p-3 text-center border-l-4 border-purple-500">
                  <div className="text-lg font-bold text-purple-700">
                    {data.latency_success_rate?.toFixed(1) || '0.0'}%
                  </div>
                  <div className="text-xs text-purple-600 font-medium">Latency &lt;50ms</div>
                  <div className="text-xs text-purple-500 mt-1">
                    avg {data.avg_latency_ms?.toFixed(0) || '0'}ms / min {data.min_latency_ms?.toFixed(0) || '0'}ms
                  </div>
                </div>
              </div>

              {/* Optimal Conditions Banner */}
              {data.optimal_conditions.pitch && (
                <div className="bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg p-3 mb-4 text-white">
                  <div className="text-sm font-bold mb-1">Optimal Conditions Found</div>
                  <div className="text-xs">
                    Pitch: <span className="font-bold">{data.optimal_conditions.pitch}</span> +
                    Elevation: <span className="font-bold">{data.optimal_conditions.elevation}</span> =
                    <span className="font-bold ml-1">{data.optimal_conditions.success_rate.toFixed(1)}% success</span>
                  </div>
                </div>
              )}

              {/* Tabs */}
              <div className="flex gap-2 mb-4 border-b">
                <button
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'matrix'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                  onClick={() => setActiveTab('matrix')}
                >
                  Pitch+Elevation Matrix
                </button>
                <button
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'pitch'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                  onClick={() => setActiveTab('pitch')}
                >
                  Pitch & Roll Stats
                </button>
                <button
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'azimuth'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                  onClick={() => setActiveTab('azimuth')}
                >
                  Satellite Direction
                </button>
              </div>

              {/* Tab Content */}
              {activeTab === 'matrix' && (
                <div>
                  <h3 className="font-bold text-gray-800 mb-2">
                    Pitch + Elevation Success Rate Matrix
                  </h3>
                  <p className="text-xs text-gray-600 mb-3">
                    Shows success rate (%) for each combination of pitch angle and satellite elevation.
                    Green = good, Red = bad. Key finding: Level flight (0~2 pitch) + high elevation (85-90) has worst performance!
                  </p>
                  {buildMatrix()}
                </div>
              )}

              {activeTab === 'pitch' && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="font-bold text-gray-800 mb-2">Pitch Angle Performance</h3>
                    <p className="text-xs text-gray-600 mb-2">
                      Tilted flight (nose up/down) performs better than level.
                    </p>
                    {renderBarChart(
                      data.pitch_stats.map(s => ({
                        label: s.pitch || '',
                        success_rate: s.success_rate,
                        count: s.count
                      }))
                    )}
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-800 mb-2">Roll Angle Performance</h3>
                    <p className="text-xs text-gray-600 mb-2">
                      Slight bank angle is beneficial for signal reception.
                    </p>
                    {renderBarChart(
                      data.roll_stats.map(s => ({
                        label: s.roll || '',
                        success_rate: s.success_rate,
                        count: s.count
                      }))
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'azimuth' && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="font-bold text-gray-800 mb-2">Satellite Azimuth (Direction)</h3>
                    <p className="text-xs text-gray-600 mb-2">
                      Performance by compass direction of satellite.
                    </p>
                    {renderAzimuthChart()}
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-800 mb-2">Satellite Elevation</h3>
                    <p className="text-xs text-gray-600 mb-2">
                      Performance by satellite angle above horizon.
                    </p>
                    {data.elevation_stats?.length > 0 ? renderBarChart(
                      data.elevation_stats.map(s => ({
                        label: s.elevation || '',
                        success_rate: s.success_rate,
                        count: s.count
                      }))
                    ) : (
                      <div className="text-gray-500 text-sm">No elevation data available</div>
                    )}
                  </div>
                </div>
              )}

              {/* Key Findings */}
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <h4 className="font-bold text-yellow-800 mb-1 text-sm">Key Findings</h4>
                <ul className="text-xs text-yellow-700 space-y-1 list-disc list-inside">
                  <li><strong>Level flight is BAD:</strong> Pitch 0~2 + Elev 85-90 = lowest success rate</li>
                  <li><strong>Tilted is GOOD:</strong> Pitch &gt;5 or &lt;-5 significantly improves performance</li>
                  <li><strong>North/Northwest direction:</strong> Best satellite connection</li>
                  <li><strong>Optimal:</strong> Slight pitch + stable roll + elevation 80-85</li>
                </ul>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AttitudeAnalysisPanel;
