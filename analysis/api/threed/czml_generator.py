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

    def generate(self, sample_rate: int = 1, color_by: str = 'altitude', flight_id: int = None) -> list:
        """
        Generate CZML data for the flight session

        Args:
            sample_rate: Sampling rate in Hz (1 = 1 point per second)
            color_by: What to color by ('altitude', 'speed', 'quality')
            flight_id: Optional flight ID to filter by (for multi-flight sessions)

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

        # Filter by flight_id if specified
        if flight_id is not None and 'flight_id' in df.columns:
            df = df[df['flight_id'] == flight_id].copy()
            if df.empty:
                raise ValueError(f"No data found for flight_id {flight_id}")
            print(f"🎯 Filtered to flight_id {flight_id}: {len(df)} data points")

        df.set_index('timestamp', inplace=True)

        if df.empty:
            raise ValueError("No flight data available")

        # Sample data (e.g., sample_rate=0.5 means 1 point every 2 seconds)
        if sample_rate > 0 and sample_rate < 1:
            sample_interval = max(1, int(1 / sample_rate))
            original_len = len(df)
            df = df.iloc[::sample_interval].copy()
            print(f"🎯 Sampling: {len(df)} points from {original_len} (interval={sample_interval}, rate={sample_rate})")
        elif sample_rate >= 1:
            print(f"📊 No sampling: {len(df)} points (rate={sample_rate})")

        # Generate CZML document
        czml = []

        # Document header
        czml.append(self._create_document_header(df))

        # Flight path entity (single path only, colored by user selection)
        czml.extend(self._create_flight_path_entity(df, color_by))

        # Signal layer entities (LTE/Starlink points at actual flight path position)
        czml.extend(self._create_signal_layer_entities(df))

        return czml

    def _create_document_header(self, df) -> dict:
        """
        Create CZML document header with clock configuration

        Args:
            df: Flight data DataFrame

        Returns:
            CZML document header dictionary
        """
        import sys
        import pandas as pd

        start_time = df.index.min()
        end_time = df.index.max()

        # Convert to datetime if string
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time, utc=True)
        if isinstance(end_time, str):
            end_time = pd.to_datetime(end_time, utc=True)

        # Convert to ISO 8601 format (Cesium compatible: YYYY-MM-DDTHH:MM:SS.sssZ)
        start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        end_iso = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        print(f"\n{'='*60}", flush=True)
        print(f"🕐 CZML CLOCK CONFIGURATION", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"   Start time: {start_iso}", flush=True)
        print(f"   End time: {end_iso}", flush=True)
        print(f"   DataFrame index type: {type(df.index[0])}", flush=True)
        print(f"   DataFrame length: {len(df)}", flush=True)
        sys.stdout.flush()

        header = {
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

        return header

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
        import pandas as pd
        start_time = df.index.min()
        end_time = df.index.max()

        # Convert to datetime if string
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time, utc=True)
        if isinstance(end_time, str):
            end_time = pd.to_datetime(end_time, utc=True)

        # Convert to ISO 8601 format (Cesium compatible)
        start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        end_iso = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        aircraft_entity = {
            "id": f"aircraft_{self.session_id}",
            "name": f"Aircraft - Session {self.session_id}",
            "availability": f"{start_iso}/{end_iso}",
            "position": {
                "epoch": start_iso,
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
        Create dual flight path entities (LTE + Starlink) with offset and gradient colors

        Args:
            df: Flight data DataFrame

        Returns:
            List of CZML entities [lte_segments..., starlink_segments..., aircraft]
        """
        # Longitude offset for parallel paths (approximately 20 meters at equator)
        LON_OFFSET = 0.0002

        # Build position samples for aircraft (center path)
        aircraft_positions = self._build_position_samples(df)

        # Create entities list
        entities = []

        # Auto-detect available LTE column (prefer lte_rsrp, fallback to lte_rssi)
        lte_column = None
        if 'lte_rsrp' in df.columns and not df['lte_rsrp'].isna().all():
            lte_column = 'lte_rsrp'
        elif 'lte_rssi' in df.columns and not df['lte_rssi'].isna().all():
            lte_column = 'lte_rssi'

        # Auto-detect available Starlink column (prefer starlink_snr, fallback to starlink_latency)
        starlink_column = None
        if 'starlink_snr' in df.columns and not df['starlink_snr'].isna().all():
            starlink_column = 'starlink_snr'
        elif 'starlink_latency' in df.columns and not df['starlink_latency'].isna().all():
            starlink_column = 'starlink_latency'

        print(f"📊 Auto-detected data columns: LTE={lte_column}, Starlink={starlink_column}", flush=True)

        # Create LTE gradient path segments (left side)
        lte_segments = self._create_gradient_path_segments(
            df, aircraft_positions, -LON_OFFSET, 'lte', lte_column
        )
        entities.extend(lte_segments)

        # Create Starlink gradient path segments (right side)
        starlink_segments = self._create_gradient_path_segments(
            df, aircraft_positions, LON_OFFSET, 'starlink', starlink_column
        )
        entities.extend(starlink_segments)

        # Convert aircraft_positions to polyline format (remove time_offset)
        polyline_positions = []
        for i in range(0, len(aircraft_positions), 4):
            lon = aircraft_positions[i+1]
            lat = aircraft_positions[i+2]
            alt = aircraft_positions[i+3]
            polyline_positions.extend([lon, lat, alt])

        # Entity: White center flight path (solid line showing complete trajectory)
        center_path_entity = {
            "id": f"center_path_{self.session_id}",
            "name": f"Flight Path - Session {self.session_id}",
            "polyline": {
                "positions": {
                    "cartographicDegrees": polyline_positions
                },
                "material": {
                    "solidColor": {
                        "color": {
                            "rgba": [255, 255, 255, 255]  # White solid color
                        }
                    }
                },
                "width": 3,
                "clampToGround": False
            }
        }
        entities.append(center_path_entity)

        # Entity: Aircraft (center, animated)
        # Handle both datetime and string timestamps
        import pandas as pd
        start_time = df.index.min()
        end_time = df.index.max()

        # Convert to datetime if string
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time, utc=True)
        if isinstance(end_time, str):
            end_time = pd.to_datetime(end_time, utc=True)

        # Convert to ISO 8601 format (Cesium compatible)
        start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        end_iso = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        aircraft_entity = {
            "id": f"aircraft_{self.session_id}",
            "name": f"Aircraft - Session {self.session_id}",
            "availability": f"{start_iso}/{end_iso}",
            "position": {
                "epoch": start_iso,
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
        entities.append(aircraft_entity)

        return entities

    def _create_signal_layer_entities(self, df) -> list:
        """
        Create signal layer entities (LTE + Starlink points) at actual flight path position
        No offset - all points displayed at real GPS coordinates

        Args:
            df: Flight data DataFrame

        Returns:
            List of CZML entities [lte_segments..., starlink_segments...]
        """
        # No offset - display at actual flight path position
        LON_OFFSET = 0

        # Build position samples for aircraft (center path)
        aircraft_positions = self._build_position_samples(df)

        # Create entities list
        entities = []

        # Auto-detect available LTE column (prefer lte_rsrp, fallback to lte_rssi)
        lte_column = None
        if 'lte_rsrp' in df.columns and not df['lte_rsrp'].isna().all():
            lte_column = 'lte_rsrp'
        elif 'lte_rssi' in df.columns and not df['lte_rssi'].isna().all():
            lte_column = 'lte_rssi'

        # Auto-detect available Starlink column (prefer starlink_snr, fallback to starlink_latency)
        starlink_column = None
        if 'starlink_snr' in df.columns and not df['starlink_snr'].isna().all():
            starlink_column = 'starlink_snr'
        elif 'starlink_latency' in df.columns and not df['starlink_latency'].isna().all():
            starlink_column = 'starlink_latency'

        print(f"📊 Signal layers: LTE={lte_column}, Starlink={starlink_column} (offset=0)", flush=True)

        # Create LTE gradient path segments (at actual position)
        if lte_column:
            lte_segments = self._create_gradient_path_segments(
                df, aircraft_positions, LON_OFFSET, 'lte', lte_column
            )
            entities.extend(lte_segments)
            print(f"  ├─ LTE segments: {len(lte_segments)}", flush=True)

        # Create Starlink gradient path segments (at actual position)
        if starlink_column:
            starlink_segments = self._create_gradient_path_segments(
                df, aircraft_positions, LON_OFFSET, 'starlink', starlink_column
            )
            entities.extend(starlink_segments)
            print(f"  └─ Starlink segments: {len(starlink_segments)}", flush=True)

        return entities

    def _create_gradient_path_segments(self, df, aircraft_positions, lon_offset, data_type, value_column):
        """
        Create multiple polyline segments with gradient colors based on signal quality

        Args:
            df: Flight data DataFrame
            aircraft_positions: List of time-tagged positions
            lon_offset: Longitude offset for parallel paths
            data_type: 'lte' or 'starlink'
            value_column: Column name for signal values ('lte_rsrp', 'lte_rssi', 'starlink_snr', or 'starlink_latency')

        Returns:
            List of polyline entities with gradient colors
        """
        entities = []

        # Get signal values
        if value_column is None or value_column not in df.columns:
            # No data, return single gray path
            positions = []
            for i in range(0, len(aircraft_positions), 4):
                lon = aircraft_positions[i+1] + lon_offset
                lat = aircraft_positions[i+2]
                alt = aircraft_positions[i+3]
                positions.extend([lon, lat, alt])

            entity = {
                "id": f"{data_type}_path_{self.session_id}",
                "name": f"{data_type.upper()} Path - No Data",
                "polyline": {
                    "positions": {"cartographicDegrees": positions},
                    "show": True,
                    "width": 6,
                    "material": {"solidColor": {"color": {"rgba": [128, 128, 128, 255]}}},
                    "clampToGround": False
                }
            }
            entities.append(entity)
            return entities

        # CRITICAL FIX: aircraft_positions length = df length * 4
        # Each row has: [time_offset, lon, lat, alt]
        num_points = len(aircraft_positions) // 4

        # DEBUG: Log data dimensions
        import sys
        print(f"\n{'='*60}", flush=True)
        print(f"🔍 DEBUG {data_type.upper()} SEGMENT GENERATION", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"   df length: {len(df)}", flush=True)
        print(f"   aircraft_positions length: {len(aircraft_positions)}", flush=True)
        print(f"   num_points: {num_points}", flush=True)
        print(f"   lon_offset: {lon_offset}", flush=True)
        print(f"   Sample aircraft_positions[0:12]: {aircraft_positions[0:12]}", flush=True)
        if num_points > 0:
            print(f"   Sample df.iloc[0]['{value_column}']: {df.iloc[0][value_column]}", flush=True)
        sys.stdout.flush()

        # Create segments by consecutive points with same color category
        segment_id = 0
        current_segment = []
        current_color = None

        for idx in range(num_points):
            # Get position from aircraft_positions
            pos_idx = idx * 4
            lon = aircraft_positions[pos_idx + 1] + lon_offset
            lat = aircraft_positions[pos_idx + 2]
            alt = aircraft_positions[pos_idx + 3]

            # Get signal value from DataFrame (same index, df is already sampled)
            signal_val = df.iloc[idx][value_column]

            # Determine color category based on signal value and column type
            if data_type == 'lte':
                color = self._get_lte_color_category(signal_val, value_column)
            else:  # starlink
                color = self._get_starlink_color_category(signal_val, value_column)

            # If color changed, save current segment and start new one
            if current_color is None:
                current_color = color
                current_segment = [lon, lat, alt]
            elif color != current_color:
                # Add last point to complete segment
                current_segment.extend([lon, lat, alt])

                # Create entity for completed segment
                if len(current_segment) >= 6:  # At least 2 points
                    entity = {
                        "id": f"{data_type}_path_{self.session_id}_seg{segment_id}",
                        "name": f"{data_type.upper()} Path Segment {segment_id}",
                        "polyline": {
                            "positions": {"cartographicDegrees": current_segment},
                            "show": True,
                            "width": 6,
                            "material": {"solidColor": {"color": {"rgba": current_color}}},
                            "clampToGround": False
                        }
                    }
                    entities.append(entity)

                    # DEBUG: Print first 3 segments coordinates
                    if segment_id < 3:
                        import sys
                        print(f"   Segment {segment_id}: {len(current_segment)//3} points, color={current_color}", flush=True)
                        print(f"      First 9 coords: {current_segment[:9]}", flush=True)
                        print(f"      Last 9 coords: {current_segment[-9:]}", flush=True)
                        sys.stdout.flush()

                    segment_id += 1

                # Start new segment with current point
                current_segment = [lon, lat, alt]
                current_color = color
            else:
                # Same color, continue segment
                current_segment.extend([lon, lat, alt])

        # Add final segment
        if len(current_segment) >= 6:
            entity = {
                "id": f"{data_type}_path_{self.session_id}_seg{segment_id}",
                "name": f"{data_type.upper()} Path Segment {segment_id}",
                "polyline": {
                    "positions": {"cartographicDegrees": current_segment},
                    "show": True,
                    "width": 6,
                    "material": {"solidColor": {"color": {"rgba": current_color}}},
                    "clampToGround": False
                }
            }
            entities.append(entity)

        # DEBUG: Summary
        import sys
        print(f"\n✅ {data_type.upper()} Summary: {len(entities)} segments created", flush=True)
        print(f"{'='*60}\n", flush=True)
        sys.stdout.flush()

        return entities

    def _get_lte_color_category(self, value, column_name):
        """
        Get LTE color category based on signal value

        Args:
            value: Signal value
            column_name: 'lte_rsrp' or 'lte_rssi'

        Returns:
            RGBA color [R, G, B, A]
        """
        if np.isnan(value):
            return [128, 128, 128, 255]  # Gray

        if column_name == 'lte_rsrp':
            # RSRP: -120 ~ -44 dBm (lower is worse)
            if value < -110:
                return [255, 0, 0, 255]  # Red - Very poor
            elif value < -100:
                return [255, 165, 0, 255]  # Orange - Poor
            elif value < -90:
                return [255, 255, 0, 255]  # Yellow - Fair
            elif value < -80:
                return [144, 238, 144, 255]  # Light Green - Good
            else:
                return [0, 255, 0, 255]  # Green - Excellent

        elif column_name == 'lte_rssi':
            # RSSI: -113 ~ -51 dBm (lower is worse)
            if value < -100:
                return [255, 0, 0, 255]  # Red - Very poor
            elif value < -90:
                return [255, 165, 0, 255]  # Orange - Poor
            elif value < -80:
                return [255, 255, 0, 255]  # Yellow - Fair
            elif value < -70:
                return [144, 238, 144, 255]  # Light Green - Good
            else:
                return [0, 255, 0, 255]  # Green - Excellent

        else:
            # Unknown column, use gray
            return [128, 128, 128, 255]

    def _get_starlink_color_category(self, value, column_name):
        """
        Get Starlink color category based on signal value

        Args:
            value: Signal value
            column_name: 'starlink_snr' or 'starlink_latency'

        Returns:
            RGBA color [R, G, B, A]
        """
        if np.isnan(value):
            return [128, 128, 128, 255]  # Gray

        if column_name == 'starlink_snr':
            # SNR: 0 ~ 15+ dB (higher is better)
            if value < 3:
                return [0, 0, 139, 255]  # Dark Blue - Very poor
            elif value < 5:
                return [0, 0, 255, 255]  # Blue - Poor
            elif value < 8:
                return [135, 206, 235, 255]  # Sky Blue - Fair
            elif value < 12:
                return [0, 255, 255, 255]  # Cyan - Good
            else:
                return [255, 255, 255, 255]  # White - Excellent

        elif column_name == 'starlink_latency':
            # Latency: 0 ~ 200+ ms (lower is better)
            if value > 150:
                return [255, 0, 0, 255]  # Red - Very poor
            elif value > 100:
                return [255, 165, 0, 255]  # Orange - Poor
            elif value > 60:
                return [255, 255, 0, 255]  # Yellow - Fair
            elif value > 30:
                return [135, 206, 235, 255]  # Sky Blue - Good
            else:
                return [0, 255, 255, 255]  # Cyan - Excellent

        else:
            # Unknown column, use gray
            return [128, 128, 128, 255]

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
        import pandas as pd

        positions = []
        start_time = df.index.min()

        # Convert to datetime if string
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)

        for timestamp, row in df.iterrows():
            # Convert timestamp to datetime if string
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)

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

    def create_heatmap_czml(self, mode: str = 'lte', style: str = 'point', flight_id: int = None) -> list:
        """
        Generate heatmap CZML for data quality visualization

        Args:
            mode: 'lte', 'starlink', or 'combined'
            style: 'point' or 'voxel' (default: 'point')
            flight_id: Optional flight ID to filter by (for multi-flight sessions)

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

        # Filter by flight_id if specified
        if flight_id is not None and 'flight_id' in df.columns:
            df = df[df['flight_id'] == flight_id].copy()
            if df.empty:
                raise ValueError(f"No data found for flight_id {flight_id}")
            print(f"🎯 Filtered heatmap to flight_id {flight_id}: {len(df)} data points")

        df.set_index('timestamp', inplace=True)

        if df.empty:
            raise ValueError("No flight data available")

        # Apply aggressive sampling for point heatmaps (every 5th point)
        if style == 'point' and len(df) > 1000:
            sample_interval = 5
            original_len = len(df)
            df = df.iloc[::sample_interval].copy()
            print(f"🗺️ Heatmap sampling: {len(df)} points from {original_len} (interval={sample_interval})")

        # Generate CZML document
        czml = []

        # Document header
        czml.append(self._create_document_header(df))

        # Generate heatmap entities based on style
        if style == 'voxel':
            heatmap_entities = self._create_voxel_heatmap_entities(df, mode)
        else:  # point (default)
            heatmap_entities = self._create_heatmap_point_entities(df, mode)

        czml.extend(heatmap_entities)

        return czml

    def _create_heatmap_point_entities(self, df, mode: str) -> list:
        """
        Create point entities for heatmap visualization

        Args:
            df: Flight data DataFrame
            mode: 'lte', 'starlink', or 'combined'

        Returns:
            List of CZML point entities
        """
        entities = []

        # Auto-detect available columns
        lte_column = None
        if 'lte_rsrp' in df.columns and not df['lte_rsrp'].isna().all():
            lte_column = 'lte_rsrp'
        elif 'lte_rssi' in df.columns and not df['lte_rssi'].isna().all():
            lte_column = 'lte_rssi'

        starlink_column = None
        if 'starlink_snr' in df.columns and not df['starlink_snr'].isna().all():
            starlink_column = 'starlink_snr'
        elif 'starlink_latency' in df.columns and not df['starlink_latency'].isna().all():
            starlink_column = 'starlink_latency'

        print(f"🗺️ Generating {mode.upper()} heatmap: LTE={lte_column}, Starlink={starlink_column}", flush=True)

        # Create point entity for each GPS coordinate
        point_count = 0
        for idx, row in df.iterrows():
            lon = row['longitude']
            lat = row['latitude']
            alt = row['altitude']

            # Skip invalid positions
            if np.isnan(lon) or np.isnan(lat) or np.isnan(alt):
                continue

            # Calculate quality score (0-100)
            quality_score = None

            if mode == 'lte' and lte_column:
                quality_score = self._normalize_lte_quality(row[lte_column], lte_column)
            elif mode == 'starlink' and starlink_column:
                quality_score = self._normalize_starlink_quality(row[starlink_column], starlink_column)
            elif mode == 'combined':
                # Redundancy logic: Use whichever signal is available (LTE OR Starlink)
                # If both exist, use the better one (max)
                lte_score = self._normalize_lte_quality(row[lte_column], lte_column) if lte_column else np.nan
                starlink_score = self._normalize_starlink_quality(row[starlink_column], starlink_column) if starlink_column else np.nan
                # np.nanmax: Ignores NaN, returns max of valid values
                quality_score = np.nanmax([lte_score, starlink_score])

            # Skip if no quality data
            if quality_score is None or np.isnan(quality_score):
                continue

            # Get unified color based on quality score
            color = self._get_unified_quality_color(quality_score)

            # Create point entity
            point_id = f"heatmap_{mode}_{self.session_id}_{point_count}"
            entity = {
                "id": point_id,
                "position": {
                    "cartographicDegrees": [lon, lat, alt]
                },
                "point": {
                    "pixelSize": 15,
                    "color": {
                        "rgba": color
                    },
                    "outlineWidth": 0,
                    "heightReference": "NONE"
                }
            }
            entities.append(entity)
            point_count += 1

        print(f"✅ Created {len(entities)} heatmap points for {mode.upper()} mode", flush=True)
        return entities

    def _normalize_lte_quality(self, value, column_name: str) -> float:
        """
        Normalize LTE signal value to 0-100 quality score

        Args:
            value: Signal value
            column_name: 'lte_rsrp' or 'lte_rssi'

        Returns:
            Quality score (0-100)
        """
        if np.isnan(value):
            return np.nan

        if column_name == 'lte_rsrp':
            # RSRP: -120 ~ -44 dBm (lower is worse)
            # Map to 0-100 scale
            vmin, vmax = -120, -44
            score = ((value - vmin) / (vmax - vmin)) * 100
        elif column_name == 'lte_rssi':
            # RSSI: -113 ~ -51 dBm (lower is worse)
            vmin, vmax = -113, -51
            score = ((value - vmin) / (vmax - vmin)) * 100
        else:
            return np.nan

        # Clamp to 0-100
        return max(0, min(100, score))

    def _normalize_starlink_quality(self, value, column_name: str) -> float:
        """
        Normalize Starlink signal value to 0-100 quality score

        Args:
            value: Signal value
            column_name: 'starlink_snr' or 'starlink_latency'

        Returns:
            Quality score (0-100)
        """
        if np.isnan(value):
            return np.nan

        if column_name == 'starlink_snr':
            # SNR: 0 ~ 15+ dB (higher is better)
            vmin, vmax = 0, 15
            score = ((value - vmin) / (vmax - vmin)) * 100
        elif column_name == 'starlink_latency':
            # Latency: 0 ~ 200 ms (lower is better, invert)
            vmin, vmax = 200, 0  # Inverted range
            score = ((value - vmin) / (vmax - vmin)) * 100
        else:
            return np.nan

        # Clamp to 0-100
        return max(0, min(100, score))

    def _get_unified_quality_color(self, quality_score: float) -> list:
        """
        Get unified color based on quality score (0-100)

        Unified Color Scheme:
        - Red (0-20): Very poor
        - Orange (20-40): Poor
        - Yellow (40-60): Fair
        - Light Green (60-80): Good
        - Green (80-100): Excellent

        Args:
            quality_score: Quality score (0-100)

        Returns:
            RGBA color [R, G, B, A]
        """
        if quality_score < 20:
            return [255, 0, 0, 255]  # Red
        elif quality_score < 40:
            return [255, 165, 0, 255]  # Orange
        elif quality_score < 60:
            return [255, 255, 0, 255]  # Yellow
        elif quality_score < 80:
            return [144, 238, 144, 255]  # Light Green
        else:
            return [0, 255, 0, 255]  # Green

    def _create_voxel_heatmap_entities(self, df, mode: str) -> list:
        """
        Create voxel (3D grid box) entities for heatmap visualization

        Args:
            df: Flight data DataFrame
            mode: 'lte', 'starlink', or 'combined'

        Returns:
            List of CZML box entities
        """
        entities = []

        # Auto-detect available columns
        lte_column = None
        if 'lte_rsrp' in df.columns and not df['lte_rsrp'].isna().all():
            lte_column = 'lte_rsrp'
        elif 'lte_rssi' in df.columns and not df['lte_rssi'].isna().all():
            lte_column = 'lte_rssi'

        starlink_column = None
        if 'starlink_snr' in df.columns and not df['starlink_snr'].isna().all():
            starlink_column = 'starlink_snr'
        elif 'starlink_latency' in df.columns and not df['starlink_latency'].isna().all():
            starlink_column = 'starlink_latency'

        print(f"🔲 Generating {mode.upper()} voxel heatmap: LTE={lte_column}, Starlink={starlink_column}", flush=True)

        # Calculate bounding box
        lon_min, lon_max = df['longitude'].min(), df['longitude'].max()
        lat_min, lat_max = df['latitude'].min(), df['latitude'].max()
        alt_min, alt_max = df['altitude'].min(), df['altitude'].max()

        # Voxel size configuration (in meters, converted to degrees for lat/lon)
        # Aviation visualization standard: 50m horizontal, 15m vertical for clean grid
        voxel_size_horizontal = 50  # 50 meters
        voxel_size_vertical = 15    # 15 meters

        # Approximate conversion: 1 degree latitude ≈ 111,000 meters
        # Longitude varies by latitude, but use average for simplicity
        avg_lat = (lat_min + lat_max) / 2
        meters_per_degree_lon = 111000 * np.cos(np.radians(avg_lat))
        meters_per_degree_lat = 111000

        voxel_lon_size = voxel_size_horizontal / meters_per_degree_lon
        voxel_lat_size = voxel_size_horizontal / meters_per_degree_lat

        # Create voxel grid
        lon_bins = np.arange(lon_min, lon_max + voxel_lon_size, voxel_lon_size)
        lat_bins = np.arange(lat_min, lat_max + voxel_lat_size, voxel_lat_size)
        alt_bins = np.arange(alt_min, alt_max + voxel_size_vertical, voxel_size_vertical)

        print(f"   Voxel grid: {len(lon_bins)-1} x {len(lat_bins)-1} x {len(alt_bins)-1} cells", flush=True)

        # Aggregate data into voxels
        voxel_count = 0
        for i in range(len(lon_bins) - 1):
            for j in range(len(lat_bins) - 1):
                for k in range(len(alt_bins) - 1):
                    # Define voxel boundaries
                    lon_start, lon_end = lon_bins[i], lon_bins[i + 1]
                    lat_start, lat_end = lat_bins[j], lat_bins[j + 1]
                    alt_start, alt_end = alt_bins[k], alt_bins[k + 1]

                    # Find points within this voxel
                    mask = (
                        (df['longitude'] >= lon_start) & (df['longitude'] < lon_end) &
                        (df['latitude'] >= lat_start) & (df['latitude'] < lat_end) &
                        (df['altitude'] >= alt_start) & (df['altitude'] < alt_end)
                    )
                    voxel_data = df[mask]

                    if len(voxel_data) == 0:
                        continue  # Skip empty voxels

                    # Calculate average quality score for this voxel
                    quality_scores = []
                    for _, row in voxel_data.iterrows():
                        if mode == 'lte' and lte_column:
                            score = self._normalize_lte_quality(row[lte_column], lte_column)
                        elif mode == 'starlink' and starlink_column:
                            score = self._normalize_starlink_quality(row[starlink_column], starlink_column)
                        elif mode == 'combined':
                            # Redundancy logic: Use whichever signal is available
                            lte_score = self._normalize_lte_quality(row[lte_column], lte_column) if lte_column else np.nan
                            starlink_score = self._normalize_starlink_quality(row[starlink_column], starlink_column) if starlink_column else np.nan
                            score = np.nanmax([lte_score, starlink_score])
                        else:
                            continue

                        if score is not None and not np.isnan(score):
                            quality_scores.append(score)

                    if len(quality_scores) == 0:
                        continue  # Skip voxels with no valid quality data

                    # Average quality score for this voxel
                    avg_quality = np.mean(quality_scores)
                    color = self._get_unified_quality_color(avg_quality)

                    # Add transparency to voxels (60% opacity)
                    color_with_alpha = color.copy()
                    color_with_alpha[3] = 153  # 60% opacity (255 * 0.6)

                    # Voxel center position
                    center_lon = (lon_start + lon_end) / 2
                    center_lat = (lat_start + lat_end) / 2
                    center_alt = (alt_start + alt_end) / 2

                    # Create box entity
                    voxel_id = f"voxel_{mode}_{self.session_id}_{voxel_count}"
                    entity = {
                        "id": voxel_id,
                        "position": {
                            "cartographicDegrees": [center_lon, center_lat, center_alt]
                        },
                        "box": {
                            "dimensions": {
                                "cartesian": [voxel_size_horizontal, voxel_size_horizontal, voxel_size_vertical]
                            },
                            "material": {
                                "solidColor": {
                                    "color": {
                                        "rgba": color_with_alpha
                                    }
                                }
                            },
                            "outline": True,
                            "outlineColor": {
                                "rgba": [0, 0, 0, 100]  # Semi-transparent black outline
                            },
                            "outlineWidth": 1.0
                        }
                    }
                    entities.append(entity)
                    voxel_count += 1

        print(f"✅ Created {len(entities)} voxel boxes for {mode.upper()} mode", flush=True)
        return entities
