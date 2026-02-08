/**
 * API service for 3D visualization backend
 */

import type { FlightSession, FlightMetadata, CZMLDocument } from '@/types/flight';

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
 * Get CZML data for a specific flight session
 */
export async function getCZMLData(
  sessionId: string,
  options?: {
    sample_rate?: number;
    color_by?: 'altitude' | 'speed' | 'quality';
  }
): Promise<CZMLDocument> {
  const params = new URLSearchParams();

  if (options?.sample_rate) {
    params.append('sample_rate', options.sample_rate.toString());
  }

  if (options?.color_by) {
    params.append('color_by', options.color_by);
  }

  const url = `${API_BASE_URL}/api/3d/czml/${sessionId}${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch CZML data: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get heatmap CZML data for data quality visualization
 */
export async function getHeatmapCZML(
  sessionId: string,
  mode: 'lte' | 'starlink' | 'combined',
  style: 'point' | 'voxel' = 'point'
): Promise<CZMLDocument> {
  const params = new URLSearchParams({ mode, style });
  const url = `${API_BASE_URL}/api/3d/heatmap/${sessionId}?${params.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch heatmap CZML: ${response.statusText}`);
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
