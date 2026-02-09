import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';

interface AnalyticsPanelProps {
  sessionId: string | null;
  flightId: number | null;
  metric: string;
}

interface DataPoint {
  timestamp: string;
  value: number;
  azimuth?: number;
  elevation?: number;
}

interface Stats {
  mean: number;
  min: number;
  max: number;
  std: number;
  coverage: number;
}

export const AnalyticsPanel: React.FC<AnalyticsPanelProps> = ({
  sessionId,
  flightId,
  metric
}) => {
  const [timeSeriesData, setTimeSeriesData] = useState<DataPoint[]>([]);
  const [scatterData, setScatterData] = useState<Array<{azimuth: number; elevation: number; quality: number}>>([]);
  const [distributionData, setDistributionData] = useState<Array<{range: string; count: number}>>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionId || !metric) return;

    const loadAnalyticsData = async () => {
      setLoading(true);
      try {
        // For now, generate mock data
        // In production, this would fetch from API endpoint
        generateMockData();
      } catch (error) {
        console.error('Failed to load analytics data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadAnalyticsData();
  }, [sessionId, flightId, metric]);

  const generateMockData = () => {
    // Generate mock time series data (100 points)
    const timeSeries: DataPoint[] = [];
    const scatter: Array<{azimuth: number; elevation: number; quality: number}> = [];
    const values: number[] = [];

    for (let i = 0; i < 100; i++) {
      const timestamp = new Date(Date.now() - (100 - i) * 60000).toISOString();
      const value = Math.random() * 100;
      const azimuth = Math.random() * 360;
      const elevation = Math.random() * 90;

      timeSeries.push({ timestamp, value, azimuth, elevation });
      scatter.push({ azimuth, elevation, quality: value });
      values.push(value);
    }

    setTimeSeriesData(timeSeries);
    setScatterData(scatter);

    // Generate distribution (10 bins)
    const bins = 10;
    const distribution: Array<{range: string; count: number}> = [];
    const binSize = 100 / bins;

    for (let i = 0; i < bins; i++) {
      const min = i * binSize;
      const max = (i + 1) * binSize;
      const count = values.filter(v => v >= min && v < max).length;
      distribution.push({ range: `${min.toFixed(0)}-${max.toFixed(0)}`, count });
    }

    setDistributionData(distribution);

    // Calculate statistics
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
    const std = Math.sqrt(variance);
    const coverage = 100; // Mock 100% coverage

    setStats({ mean, min, max, std, coverage });
  };

  const getMetricLabel = (metricKey: string): string => {
    const labels: Record<string, string> = {
      'altitude': 'Altitude',
      'speed': 'Speed',
      'lte_quality_combined': 'LTE Quality',
      'lte_rsrp': 'LTE RSRP',
      'lte_sinr': 'LTE SINR',
      'lte_rsrq': 'LTE RSRQ',
      'starlink_quality_combined': 'Starlink Quality',
      'starlink_snr': 'Starlink SNR',
      'starlink_latency': 'Starlink Latency',
      'starlink_packet_loss': 'Packet Loss',
      'starlink_throughput_down': 'Download Speed',
      'starlink_throughput_up': 'Upload Speed',
      'starlink_obstruction': 'Obstruction',
      'starlink_uptime': 'Uptime'
    };
    return labels[metricKey] || metricKey;
  };

  const getMetricUnit = (metricKey: string): string => {
    const units: Record<string, string> = {
      'altitude': 'm',
      'speed': 'm/s',
      'lte_rsrp': 'dBm',
      'lte_sinr': 'dB',
      'lte_rsrq': 'dB',
      'starlink_snr': 'dB',
      'starlink_latency': 'ms',
      'starlink_packet_loss': '%',
      'starlink_throughput_down': 'Mbps',
      'starlink_throughput_up': 'Mbps',
      'starlink_obstruction': 'ratio',
      'starlink_uptime': 'hours'
    };
    return units[metricKey] || '';
  };

  const isStarlinkMetric = metric.startsWith('starlink_');

  return (
    <div className="absolute top-4 right-4 bg-white rounded-lg shadow-xl z-10 max-w-[500px]">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b bg-gray-50 rounded-t-lg">
        <h3 className="text-sm font-bold text-gray-800">📊 Analytics: {getMetricLabel(metric)}</h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-gray-600 hover:text-gray-800 text-sm font-bold"
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {isExpanded && (
        <div className="p-4 space-y-4 max-h-[calc(100vh-120px)] overflow-y-auto">
          {loading ? (
            <div className="text-center text-gray-500 text-sm py-8">Loading analytics...</div>
          ) : (
            <>
              {/* Statistics Summary */}
              {stats && (
                <div className="bg-blue-50 p-3 rounded border border-blue-200">
                  <h4 className="text-xs font-bold text-gray-700 mb-2">Statistics</h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div><span className="font-semibold">Mean:</span> {stats.mean.toFixed(2)} {getMetricUnit(metric)}</div>
                    <div><span className="font-semibold">Std Dev:</span> {stats.std.toFixed(2)}</div>
                    <div><span className="font-semibold">Min:</span> {stats.min.toFixed(2)} {getMetricUnit(metric)}</div>
                    <div><span className="font-semibold">Max:</span> {stats.max.toFixed(2)} {getMetricUnit(metric)}</div>
                    <div className="col-span-2"><span className="font-semibold">Coverage:</span> {stats.coverage.toFixed(1)}%</div>
                  </div>
                </div>
              )}

              {/* Time Series Chart */}
              <div>
                <h4 className="text-xs font-bold text-gray-700 mb-2">Time Series</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={timeSeriesData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tick={{ fontSize: 10 }}
                      tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                    />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                      formatter={(value: number) => [`${value.toFixed(2)} ${getMetricUnit(metric)}`, getMetricLabel(metric)]}
                    />
                    <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Distribution Chart */}
              <div>
                <h4 className="text-xs font-bold text-gray-700 mb-2">Distribution</h4>
                <ResponsiveContainer width="100%" height={150}>
                  <BarChart data={distributionData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="range" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Azimuth/Elevation Scatter (Starlink only) */}
              {isStarlinkMetric && scatterData.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-gray-700 mb-2">Satellite Direction vs Quality</h4>
                  <ResponsiveContainer width="100%" height={200}>
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="azimuth"
                        name="Azimuth"
                        unit="°"
                        tick={{ fontSize: 10 }}
                        domain={[0, 360]}
                      />
                      <YAxis
                        dataKey="elevation"
                        name="Elevation"
                        unit="°"
                        tick={{ fontSize: 10 }}
                        domain={[0, 90]}
                      />
                      <Tooltip
                        cursor={{ strokeDasharray: '3 3' }}
                        formatter={(value: number, name: string) => {
                          if (name === 'quality') return [`${value.toFixed(2)} ${getMetricUnit(metric)}`, 'Quality'];
                          return [value.toFixed(1) + '°', name];
                        }}
                      />
                      <Scatter
                        data={scatterData}
                        fill="#8b5cf6"
                        fillOpacity={0.6}
                      />
                    </ScatterChart>
                  </ResponsiveContainer>
                  <p className="text-xs text-gray-600 mt-1">
                    Shows relationship between satellite position (azimuth/elevation) and signal quality
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
