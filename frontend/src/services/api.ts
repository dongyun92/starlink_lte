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
                'lte_quality_combined' | 'lte_rsrp' | 'lte_sinr' | 'lte_rsrq' | 'lte_rssi' |
                'starlink_quality_combined' | 'starlink_snr' | 'starlink_latency' |
                'starlink_packet_loss' | 'starlink_throughput_down' | 'starlink_throughput_up' |
                'starlink_obstruction' | 'starlink_uptime';
    flight_id?: number;
    custom_metrics?: Record<string, number>;
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

  if (options?.custom_metrics) {
    params.append('custom_metrics', JSON.stringify(options.custom_metrics));
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
  style: 'point' | 'voxel' = 'point',
  flight_id?: number
): Promise<CZMLDocument> {
  const params = new URLSearchParams({ mode, style });
  if (flight_id !== undefined) {
    params.append('flight_id', flight_id.toString());
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
    color_by?: 'starlink_snr' | 'starlink_latency';
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
  } = {}
): Promise<any> {
  const { radio = 'LTE', use_cache = true } = options;

  const params = new URLSearchParams({
    radio,
    use_cache: use_cache.toString(),
  });

  const response = await fetch(`${API_BASE_URL}/api/3d/cell-towers/${sessionId}?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch cell towers: ${response.statusText}`);
  }

  return response.json();
}
