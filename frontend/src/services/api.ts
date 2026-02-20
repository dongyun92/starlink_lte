/**
 * API service for 3D visualization backend
 */

import type { FlightSession, FlightMetadata, FlightScenario, CZMLDocument } from '@/types/flight';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5002';

/**
 * Get list of all flight sessions
 */
export async function getFlightSessions(): Promise<FlightSession[]> {
  const response = await fetch(`${API_BASE_URL}/api/3d/flights`);

  if (!response.ok) {
    throw new Error(`Failed to fetch flight sessions: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get metadata for a specific flight session
 */
export async function getFlightMetadata(sessionId: string): Promise<FlightMetadata> {
  const response = await fetch(`${API_BASE_URL}/api/3d/flights/${sessionId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch flight metadata: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get list of flight scenarios for a specific session
 */
export async function getFlightScenarios(sessionId: string): Promise<FlightScenario[]> {
  const response = await fetch(`${API_BASE_URL}/api/3d/flights/${sessionId}/scenarios`);

  if (!response.ok) {
    throw new Error(`Failed to fetch flight scenarios: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get CZML data for a specific flight session
 */
export async function getCZMLData(
  sessionId: string,
  options?: {
    sample_rate?: number;
    color_by?: 'altitude' | 'speed' |
                'pitch' | 'roll' | 'pitch_performance' |
                'lte_quality_combined' | 'lte_rsrp' | 'lte_sinr' | 'lte_rsrq' | 'lte_rssi' | 'lte_band' | 'lte_outage' |
                'starlink_quality_combined' | 'starlink_latency' |
                'starlink_packet_loss' | 'starlink_throughput_down' | 'starlink_throughput_up' |
                'starlink_obstruction' | 'starlink_uptime' | 'lap_number' | 'combined_connectivity';
    flight_id?: number;
    lap?: number;
    custom_metrics?: Record<string, number>;
    heading_offset?: number;
    pitch_offset?: number;
    roll_offset?: number;
  }
): Promise<CZMLDocument> {
  const params = new URLSearchParams();

  if (options?.sample_rate) {
    params.append('sample_rate', options.sample_rate.toString());
  }

  if (options?.color_by) {
    params.append('color_by', options.color_by);
  }

  if (options?.flight_id !== undefined) {
    params.append('flight_id', options.flight_id.toString());
  }

  if (options?.lap !== undefined && options.lap !== 0) {
    params.append('lap', options.lap.toString());
  }

  if (options?.custom_metrics) {
    params.append('custom_metrics', JSON.stringify(options.custom_metrics));
  }

  if (options?.heading_offset !== undefined) {
    params.append('heading_offset', options.heading_offset.toString());
  }

  if (options?.pitch_offset !== undefined) {
    params.append('pitch_offset', options.pitch_offset.toString());
  }

  if (options?.roll_offset !== undefined) {
    params.append('roll_offset', options.roll_offset.toString());
  }

  const url = `${API_BASE_URL}/api/3d/czml/${sessionId}${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    // Try to parse error message from server
    try {
      const errorData = await response.json();
      throw new Error(errorData.error || `Failed to fetch CZML data: ${response.statusText}`);
    } catch (parseError) {
      throw new Error(`Failed to fetch CZML data: ${response.statusText}`);
    }
  }

  return response.json();
}

/**
 * Get heatmap CZML data for data quality visualization
 */
export async function getHeatmapCZML(
  sessionId: string,
  mode: 'lte' | 'starlink' | 'combined',
  style: 'point' | 'voxel' | 'hexagon' = 'point',
  flight_id?: number,
  hexagonOptions?: {
    resolution?: number;
    aggregation?: 'mean' | 'max' | 'min' | 'median';
    altitude_bin_size?: number;
  }
): Promise<CZMLDocument> {
  const params = new URLSearchParams({ mode, style });
  if (flight_id !== undefined) {
    params.append('flight_id', flight_id.toString());
  }

  // Add hexagon/voxel-specific parameters
  if ((style === 'hexagon' || style === 'voxel') && hexagonOptions) {
    // Hexagon-only parameters
    if (style === 'hexagon') {
      if (hexagonOptions.resolution !== undefined) {
        params.append('resolution', hexagonOptions.resolution.toString());
      }
      if (hexagonOptions.aggregation) {
        params.append('aggregation', hexagonOptions.aggregation);
      }
    }
    // Shared parameter for both hexagon and voxel
    if (hexagonOptions.altitude_bin_size !== undefined) {
      params.append('altitude_bin_size', hexagonOptions.altitude_bin_size.toString());
    }
  }

  const url = `${API_BASE_URL}/api/3d/heatmap/${sessionId}?${params.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch heatmap CZML: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get satellite direction CZML data for Starlink visualization
 */
export async function getSatelliteDirectionCZML(
  sessionId: string,
  options: {
    sample_rate?: number;
    color_by?: 'starlink_latency';
    arrow_length?: number;
    flight_id?: number;
  } = {}
): Promise<CZMLDocument> {
  const params = new URLSearchParams();

  if (options.sample_rate !== undefined) {
    params.append('sample_rate', options.sample_rate.toString());
  }

  if (options.color_by) {
    params.append('color_by', options.color_by);
  }

  if (options.arrow_length !== undefined) {
    params.append('arrow_length', options.arrow_length.toString());
  }

  if (options.flight_id !== undefined) {
    params.append('flight_id', options.flight_id.toString());
  }

  const url = `${API_BASE_URL}/api/3d/satellite-direction/${sessionId}${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    try {
      const errorData = await response.json();
      throw new Error(errorData.error || `Failed to fetch satellite direction CZML: ${response.statusText}`);
    } catch (parseError) {
      throw new Error(`Failed to fetch satellite direction CZML: ${response.statusText}`);
    }
  }

  return response.json();
}

/**
 * Get tower connections CZML data for a session
 */
export async function getTowerConnectionsCZML(
  sessionId: string,
  options: {
    sample_rate?: number;
    flight_id?: number;
  } = {}
): Promise<CZMLDocument> {
  const params = new URLSearchParams();

  if (options.sample_rate !== undefined) {
    params.append('sample_rate', options.sample_rate.toString());
  }

  if (options.flight_id !== undefined) {
    params.append('flight_id', options.flight_id.toString());
  }

  const url = `${API_BASE_URL}/api/3d/tower-connections/${sessionId}${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    try {
      const errorData = await response.json();
      throw new Error(errorData.error || `Failed to fetch tower connections CZML: ${response.statusText}`);
    } catch (parseError) {
      throw new Error(`Failed to fetch tower connections CZML: ${response.statusText}`);
    }
  }

  return response.json();
}

/**
 * Health check for 3D API
 */
export async function checkAPIHealth(): Promise<{ status: string; service: string; version: string }> {
  const response = await fetch(`${API_BASE_URL}/api/3d/health`);

  if (!response.ok) {
    throw new Error(`API health check failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get cell tower data for a specific flight session
 */
export async function getCellTowers(
  sessionId: string,
  options: {
    radio?: string;
    use_cache?: boolean;
    flight_id?: number;
  } = {}
): Promise<any> {
  const { radio = 'LTE', use_cache = true, flight_id } = options;

  const params = new URLSearchParams({
    radio,
    use_cache: use_cache.toString(),
  });

  if (flight_id !== undefined) {
    params.append('flight_id', flight_id.toString());
  }

  const response = await fetch(`${API_BASE_URL}/api/3d/cell-towers/${sessionId}?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch cell towers: ${response.statusText}`);
  }

  return response.json();
}


/**
 * Chart information interface
 */
export interface ChartInfo {
  name: string;
  title: string;
  url: string;
}

/**
 * Session results interface
 */
export interface SessionResults {
  session_id: string;
  metadata: any;
  key_findings: any[];
  statistics: any;
  analysis_results: any;
  charts: ChartInfo[];
  downloads: {
    report: string;
    charts_zip: string;
    map_data: string;
  };
}

/**
 * Get all charts for a specific session
 */
export async function getSessionCharts(sessionId: string): Promise<ChartInfo[]> {
  const response = await fetch(`${API_BASE_URL}/api/session/${sessionId}/results`);

  if (!response.ok) {
    throw new Error(`Failed to fetch session charts: ${response.statusText}`);
  }

  const results: SessionResults = await response.json();
  return results.charts;
}

export async function retryAnalysis(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/retry/${sessionId}`, {
    method: 'POST'
  });

  if (!response.ok) {
    throw new Error(`Failed to retry analysis: ${response.statusText}`);
  }
}

export interface SessionStatus {
  session_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  current_step: string;
}

export async function getSessionStatus(sessionId: string): Promise<SessionStatus> {
  const response = await fetch(`${API_BASE_URL}/api/session/${sessionId}/status`);

  if (!response.ok) {
    throw new Error(`Failed to fetch session status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * KPI Summary interface
 */
export interface KPISummary {
  flight: {
    duration_seconds: number;
    distance_km: number;
    max_altitude_m: number;
    avg_speed_kmh: number;
  };
  lte: {
    avg_rsrp: number | null;
    quality: string | null;
    color: string;
  };
  starlink: {
    avg_latency: number | null;
    quality: string | null;
    color: string;
  };
  signal_loss: {
    percentage: number;
    segment_count: number;
    total_duration_seconds: number;
  };
}

/**
 * Get KPI summary for a specific session
 */
export async function getKPISummary(sessionId: string): Promise<KPISummary> {
  const response = await fetch(`${API_BASE_URL}/api/3d/kpi/${sessionId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch KPI summary: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Signal Loss Segment interface
 */
export interface SignalLossSegment {
  start_index: number;
  end_index: number;
  start_time: string;
  end_time: string;
  duration_seconds: number;
  center_lat: number;
  center_lon: number;
  center_altitude: number;
  lte_poor: boolean;
  starlink_poor: boolean;
  avg_lte_rsrp: number | null;
  avg_starlink_latency: number | null;
}

export interface SignalLossData {
  segments: SignalLossSegment[];
  total_percentage: number;
  total_segments: number;
}

/**
 * Get signal loss segments for a specific session
 */
export async function getSignalLossSegments(sessionId: string): Promise<SignalLossData> {
  const response = await fetch(`${API_BASE_URL}/api/3d/signal-loss/${sessionId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch signal loss segments: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Root Cause Analysis interfaces
 */
export interface CauseBreakdown {
  lte_only: {
    count: number;
    percentage: number;
    total_duration: number;
  };
  starlink_only: {
    count: number;
    percentage: number;
    total_duration: number;
  };
  both: {
    count: number;
    percentage: number;
    total_duration: number;
  };
}

export interface AltitudeDistribution {
  range: string;
  count: number;
  percentage: number;
  avg_duration: number;
}

export interface TimeDistribution {
  period: string;
  count: number;
  percentage: number;
}

export interface RootCauseAnalysis {
  cause_breakdown: CauseBreakdown;
  altitude_distribution: AltitudeDistribution[];
  time_distribution: TimeDistribution[];
  summary: {
    total_segments: number;
    avg_duration: number;
    total_impact_time: number;
  };
}

/**
 * Get root cause analysis for signal loss segments
 */
export async function getRootCauseAnalysis(sessionId: string): Promise<RootCauseAnalysis> {
  const response = await fetch(`${API_BASE_URL}/api/3d/root-cause/${sessionId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch root cause analysis: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Attitude analysis data interfaces
 */
export interface PitchElevationMatrixItem {
  pitch: string;
  elevation: string;
  success_rate: number;
  count: number;
  avg_upload_mbps: number;
  // Download metrics (optional)
  download_success_rate?: number;
  avg_download_mbps?: number;
  // Latency metrics (optional)
  latency_success_rate?: number;
  avg_latency_ms?: number;
}

export interface AttitudeStatItem {
  pitch?: string;
  roll?: string;
  direction?: string;
  elevation?: string;
  success_rate: number;
  count: number;
  avg_upload_mbps: number;
  // Download metrics (optional)
  download_success_rate?: number;
  avg_download_mbps?: number;
  // Latency metrics (optional)
  latency_success_rate?: number;
  avg_latency_ms?: number;
}

export interface AttitudeAnalysis {
  session_id: string;
  total_points: number;

  // Upload metrics (primary)
  good_points: number;
  overall_success_rate: number;
  avg_upload_mbps: number;
  max_upload_mbps: number;

  // Download metrics
  good_download_points: number;
  download_success_rate: number;
  avg_download_mbps: number;
  max_download_mbps: number;

  // Latency metrics
  good_latency_points: number;
  latency_success_rate: number;
  avg_latency_ms: number;
  min_latency_ms: number;

  // Detailed stats
  pitch_elevation_matrix: PitchElevationMatrixItem[];
  pitch_stats: AttitudeStatItem[];
  roll_stats: AttitudeStatItem[];
  azimuth_stats: AttitudeStatItem[];
  elevation_stats: AttitudeStatItem[];
  optimal_conditions: {
    pitch: string | null;
    elevation: string | null;
    success_rate: number;
  };
}

/**
 * Get attitude analysis for a session (Pitch+Elevation matrix, etc.)
 */
export async function getAttitudeAnalysis(
  sessionId: string,
  options?: { flight_id?: number }
): Promise<AttitudeAnalysis> {
  const params = new URLSearchParams();

  if (options?.flight_id !== undefined) {
    params.append('flight_id', options.flight_id.toString());
  }

  const url = `${API_BASE_URL}/api/3d/attitude-analysis/${sessionId}${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    try {
      const errorData = await response.json();
      throw new Error(errorData.error || `Failed to fetch attitude analysis: ${response.statusText}`);
    } catch (parseError) {
      throw new Error(`Failed to fetch attitude analysis: ${response.statusText}`);
    }
  }

  return response.json();
}
