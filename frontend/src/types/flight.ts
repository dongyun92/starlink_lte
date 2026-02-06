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

export interface CZMLDocument extends Array<any> {
  // CZML is an array of packets
}
