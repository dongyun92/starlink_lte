"""
CZML Generator for Flight Data Visualization
Converts flight data from database to CZML format for Cesium.js
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))


class CZMLGenerator:
    """Generate CZML data from flight sessions"""

    def __init__(self, session_id: str):
        """
        Initialize CZML generator

        Args:
            session_id: Session identifier
        """
        self.session_id = session_id
        self.analyzer = None

    def generate(self, sample_rate: int = 1, color_by: str = 'altitude') -> list:
        """
        Generate CZML data for the flight session

        Args:
            sample_rate: Sampling rate in Hz (1 = 1 point per second)
            color_by: What to color by ('altitude', 'speed', 'quality')

        Returns:
            CZML data as list of dictionaries
        """
        # Load merged data from results directory
        results_dir = Path(__file__).parent.parent.parent / 'results' / self.session_id
        merged_data_path = results_dir / 'merged_data.csv'

        if not merged_data_path.exists():
            raise ValueError(f"No merged data found for session {self.session_id}")

        # Read CSV with timestamp as index
        df = pd.read_csv(merged_data_path, parse_dates=['timestamp'])
        df.set_index('timestamp', inplace=True)

        if df.empty:
            raise ValueError("No flight data available")

        # Sample data
        if sample_rate > 0:
            sample_interval = max(1, int(len(df) / (len(df) * sample_rate)))
            df = df.iloc[::sample_interval].copy()

        # Generate CZML document
        czml = []

        # Document header
        czml.append(self._create_document_header(df))

        # Flight path entities
        if color_by == 'dual':
            # Dual path mode: LTE + Starlink
            czml.extend(self._create_dual_path_entities(df))
        else:
            # Single path mode (altitude, speed, etc.)
            czml.extend(self._create_flight_path_entity(df, color_by))

        return czml

    def _create_document_header(self, df) -> dict:
        """
        Create CZML document header with clock configuration

        Args:
            df: Flight data DataFrame

        Returns:
            CZML document header dictionary
        """
        start_time = df.index.min()
        end_time = df.index.max()

        # Convert to ISO 8601 format
        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()

        return {
            "id": "document",
            "version": "1.0",
            "name": f"Flight Visualization - Session {self.session_id}",
            "clock": {
                "interval": f"{start_iso}/{end_iso}",
                "currentTime": start_iso,
                "multiplier": 1,
                "range": "LOOP_STOP",
                "step": "SYSTEM_CLOCK_MULTIPLIER"
            }
        }

    def _create_flight_path_entity(self, df, color_by: str) -> list:
        """
        Create flight path entity with position and path

        Args:
            df: Flight data DataFrame
            color_by: What to color by ('altitude', 'speed', 'quality')

        Returns:
            CZML entity dictionary
        """
        # Calculate colors based on parameter
        colors = self._calculate_colors(df, color_by)

        # Build position property (time-tagged samples)
        positions = self._build_position_samples(df)

        # Build path material (gradient colors)
        path_material = self._build_path_material(colors)

        # 전체 경로를 Cartesian3 좌표로 변환 (시간 오프셋 제거)
        polyline_positions = []
        for i in range(0, len(positions), 4):
            lon = positions[i+1]
            lat = positions[i+2]
            alt = positions[i+3]
            polyline_positions.extend([lon, lat, alt])

        # Entity 1: 고정된 polyline (전체 경로)
        polyline_entity = {
            "id": f"flight_path_{self.session_id}",
            "name": f"Flight Path - Session {self.session_id}",
            "polyline": {
                "positions": {
                    "cartographicDegrees": polyline_positions
                },
                "show": True,
                "width": 8,
                "material": path_material,
                "clampToGround": False
            }
        }

        # Entity 2: 움직이는 point (비행기)
        aircraft_entity = {
            "id": f"aircraft_{self.session_id}",
            "name": f"Aircraft - Session {self.session_id}",
            "availability": f"{df.index.min().isoformat()}/{df.index.max().isoformat()}",
            "position": {
                "epoch": df.index.min().isoformat(),
                "cartographicDegrees": positions
            },
            "point": {
                "pixelSize": 10,
                "color": {
                    "rgba": [255, 0, 0, 255]
                },
                "outlineColor": {
                    "rgba": [255, 255, 255, 255]
                },
                "outlineWidth": 2
            }
        }

        return [polyline_entity, aircraft_entity]

    def _create_dual_path_entities(self, df) -> list:
        """
        Create dual flight path entities (LTE + Starlink) with offset

        Args:
            df: Flight data DataFrame

        Returns:
            List of CZML entities [lte_polyline, starlink_polyline, aircraft]
        """
        # Longitude offset for parallel paths (approximately 20 meters at equator)
        LON_OFFSET = 0.0002

        # Calculate colors for each data type
        lte_colors = self._calculate_lte_colors(df)
        starlink_colors = self._calculate_starlink_colors(df)

        # Build position samples for aircraft (center path)
        aircraft_positions = self._build_position_samples(df)

        # Build LTE path (offset left)
        lte_positions = []
        for i in range(0, len(aircraft_positions), 4):
            lon = aircraft_positions[i+1] - LON_OFFSET
            lat = aircraft_positions[i+2]
            alt = aircraft_positions[i+3]
            lte_positions.extend([lon, lat, alt])

        # Build Starlink path (offset right)
        starlink_positions = []
        for i in range(0, len(aircraft_positions), 4):
            lon = aircraft_positions[i+1] + LON_OFFSET
            lat = aircraft_positions[i+2]
            alt = aircraft_positions[i+3]
            starlink_positions.extend([lon, lat, alt])

        # LTE path material (average red-yellow-green gradient)
        lte_material = self._build_path_material(lte_colors)

        # Starlink path material (average blue-cyan-white gradient)
        starlink_material = self._build_path_material(starlink_colors)

        # Entity 1: LTE polyline (left path)
        lte_entity = {
            "id": f"lte_path_{self.session_id}",
            "name": f"LTE Signal Path - Session {self.session_id}",
            "polyline": {
                "positions": {
                    "cartographicDegrees": lte_positions
                },
                "show": True,
                "width": 6,
                "material": lte_material,
                "clampToGround": False
            }
        }

        # Entity 2: Starlink polyline (right path)
        starlink_entity = {
            "id": f"starlink_path_{self.session_id}",
            "name": f"Starlink Signal Path - Session {self.session_id}",
            "polyline": {
                "positions": {
                    "cartographicDegrees": starlink_positions
                },
                "show": True,
                "width": 6,
                "material": starlink_material,
                "clampToGround": False
            }
        }

        # Entity 3: Aircraft (center, animated)
        aircraft_entity = {
            "id": f"aircraft_{self.session_id}",
            "name": f"Aircraft - Session {self.session_id}",
            "availability": f"{df.index.min().isoformat()}/{df.index.max().isoformat()}",
            "position": {
                "epoch": df.index.min().isoformat(),
                "cartographicDegrees": aircraft_positions
            },
            "point": {
                "pixelSize": 10,
                "color": {
                    "rgba": [255, 0, 0, 255]
                },
                "outlineColor": {
                    "rgba": [255, 255, 255, 255]
                },
                "outlineWidth": 2
            }
        }

        return [lte_entity, starlink_entity, aircraft_entity]

    def _calculate_colors(self, df, color_by: str) -> np.ndarray:
        """
        Calculate colors for each position based on parameter

        Args:
            df: Flight data DataFrame
            color_by: What to color by ('altitude', 'speed', 'quality')

        Returns:
            Array of RGBA color values (0-255)
        """
        if color_by == 'altitude':
            values = df['altitude'].values
        elif color_by == 'speed':
            values = df.get('speed_mps', df['altitude']).values
        else:
            # Default to altitude
            values = df['altitude'].values

        # Normalize values to 0-1 range
        vmin, vmax = np.nanmin(values), np.nanmax(values)
        if vmax > vmin:
            normalized = (values - vmin) / (vmax - vmin)
        else:
            normalized = np.zeros_like(values)

        # Apply viridis colormap
        colors = self._viridis_colormap(normalized)

        return colors

    def _viridis_colormap(self, values: np.ndarray) -> np.ndarray:
        """
        Apply viridis colormap to normalized values

        Args:
            values: Normalized values (0-1)

        Returns:
            RGBA colors (0-255)
        """
        # Simplified viridis colormap (5 control points)
        viridis_colors = np.array([
            [68, 1, 84],      # Purple (low)
            [59, 82, 139],    # Blue
            [33, 145, 140],   # Teal
            [94, 201, 98],    # Green
            [253, 231, 37]    # Yellow (high)
        ])

        # Interpolate colors
        n = len(values)
        colors = np.zeros((n, 4), dtype=np.uint8)

        for i, val in enumerate(values):
            if np.isnan(val):
                colors[i] = [128, 128, 128, 255]  # Gray for NaN
                continue

            # Find interpolation indices
            idx = val * (len(viridis_colors) - 1)
            idx0 = int(np.floor(idx))
            idx1 = min(idx0 + 1, len(viridis_colors) - 1)
            frac = idx - idx0

            # Interpolate RGB
            rgb = viridis_colors[idx0] * (1 - frac) + viridis_colors[idx1] * frac
            colors[i] = [int(rgb[0]), int(rgb[1]), int(rgb[2]), 255]

        return colors

    def _calculate_lte_colors(self, df) -> np.ndarray:
        """
        Calculate colors based on LTE RSRP values

        RSRP Color Mapping:
        - Red (< -110 dBm): Very poor signal
        - Orange (-110 ~ -100 dBm): Poor signal
        - Yellow (-100 ~ -90 dBm): Fair signal
        - Light Green (-90 ~ -80 dBm): Good signal
        - Green (> -80 dBm): Excellent signal

        Args:
            df: Flight data DataFrame with 'lte_rsrp' column

        Returns:
            Array of RGBA color values (0-255)
        """
        if 'lte_rsrp' not in df.columns:
            # Return gray if no LTE data
            n = len(df)
            return np.full((n, 4), [128, 128, 128, 255], dtype=np.uint8)

        rsrp_values = df['lte_rsrp'].values
        n = len(rsrp_values)
        colors = np.zeros((n, 4), dtype=np.uint8)

        for i, rsrp in enumerate(rsrp_values):
            if np.isnan(rsrp):
                # Gray for missing data
                colors[i] = [128, 128, 128, 255]
            elif rsrp < -110:
                # Red - Very poor
                colors[i] = [255, 0, 0, 255]
            elif rsrp < -100:
                # Orange - Poor
                colors[i] = [255, 165, 0, 255]
            elif rsrp < -90:
                # Yellow - Fair
                colors[i] = [255, 255, 0, 255]
            elif rsrp < -80:
                # Light Green - Good
                colors[i] = [144, 238, 144, 255]
            else:
                # Green - Excellent
                colors[i] = [0, 255, 0, 255]

        return colors

    def _calculate_starlink_colors(self, df) -> np.ndarray:
        """
        Calculate colors based on Starlink SNR values

        SNR Color Mapping:
        - Dark Blue (< 3 dB): Very poor signal
        - Blue (3 ~ 5 dB): Poor signal
        - Sky Blue (5 ~ 8 dB): Fair signal
        - Cyan (8 ~ 12 dB): Good signal
        - White (> 12 dB): Excellent signal

        Args:
            df: Flight data DataFrame with 'starlink_snr' column

        Returns:
            Array of RGBA color values (0-255)
        """
        if 'starlink_snr' not in df.columns:
            # Return gray if no Starlink data
            n = len(df)
            return np.full((n, 4), [128, 128, 128, 255], dtype=np.uint8)

        snr_values = df['starlink_snr'].values
        n = len(snr_values)
        colors = np.zeros((n, 4), dtype=np.uint8)

        for i, snr in enumerate(snr_values):
            if np.isnan(snr):
                # Gray for missing data
                colors[i] = [128, 128, 128, 255]
            elif snr < 3:
                # Dark Blue - Very poor
                colors[i] = [0, 0, 139, 255]
            elif snr < 5:
                # Blue - Poor
                colors[i] = [0, 0, 255, 255]
            elif snr < 8:
                # Sky Blue - Fair
                colors[i] = [135, 206, 235, 255]
            elif snr < 12:
                # Cyan - Good
                colors[i] = [0, 255, 255, 255]
            else:
                # White - Excellent
                colors[i] = [255, 255, 255, 255]

        return colors

    def _build_position_samples(self, df) -> list:
        """
        Build time-tagged position samples for CZML

        Args:
            df: Flight data DataFrame

        Returns:
            List of [time_offset, lon, lat, alt, ...]
        """
        positions = []
        start_time = df.index.min()

        for timestamp, row in df.iterrows():
            # Position: longitude, latitude, altitude (in meters)
            lon = row['longitude']
            lat = row['latitude']
            alt = row['altitude']

            # Skip invalid positions (NaN, Infinity)
            if np.isnan(lon) or np.isnan(lat) or np.isnan(alt):
                continue
            if np.isinf(lon) or np.isinf(lat) or np.isinf(alt):
                continue

            # Time offset in seconds
            time_offset = (timestamp - start_time).total_seconds()

            positions.extend([time_offset, lon, lat, alt])

        return positions

    def _build_path_material(self, colors: np.ndarray) -> dict:
        """
        Build path material with gradient colors

        Args:
            colors: Array of RGBA colors

        Returns:
            CZML material dictionary
        """
        # For simplicity, use solid color (average of all colors)
        avg_color = np.mean(colors, axis=0).astype(int)

        return {
            "solidColor": {
                "color": {
                    "rgba": avg_color.tolist()
                }
            }
        }
