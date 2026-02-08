/**
 * Flight session types
 */

export interface FlightSession {
  id: string;
  name: string;
  created_at: string;
  file_count: {
    flight_logs: number;
    lte_data: number;
    starlink_data: number;
  };
}

export interface FlightMetadata {
  id: string;
  name: string;
  created_at: string;
  status: string;
  files: {
    flight_logs: number;
    lte_data: number;
    starlink_data: number;
  };
}

export interface FlightScenario {
  flight_id: number;
  flight_name: string;
  scenario_name: string;
  data_points: number;
  time_range: {
    start: string;
    end: string;
  };
  coordinates: {
    lat_min: number;
    lat_max: number;
    lon_min: number;
    lon_max: number;
    alt_min: number;
    alt_max: number;
  };
}

export interface CZMLDocument extends Array<any> {
  // CZML is an array of packets
}
