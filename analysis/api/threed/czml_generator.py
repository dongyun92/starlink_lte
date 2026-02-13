"""
CZML Generator for Flight Data Visualization
Converts flight data from database to CZML format for Cesium.js
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib.cm as cm
import matplotlib.colors as mcolors

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

    def _calculate_sampling_params(self, data_size: int) -> tuple[float, int]:
        """
        Calculate optimal sampling parameters based on data size.
        Goal: Keep rendered points between 5,000-15,000 for smooth performance.

        Args:
            data_size: Total number of GPS points

        Returns:
            (sampling_rate, segment_interval) tuple
            - sampling_rate: Fraction of data to keep (0.0-1.0)
            - segment_interval: Interval for creating path segments
        """
        # Target: 5,000-15,000 rendered points
        if data_size > 100000:
            # Very large dataset: aggressive sampling
            return 0.05, 5  # 5% of data, 5-point segments → ~1,000 segments
        elif data_size > 50000:
            # Large dataset: moderate sampling
            return 0.1, 3  # 10% of data, 3-point segments → ~1,666 segments
        elif data_size > 20000:
            # Medium dataset: light sampling
            return 0.2, 2  # 20% of data, 2-point segments → ~2,000 segments
        elif data_size > 10000:
            # Small-medium dataset: minimal sampling
            return 0.3, 1  # 30% of data, 1-point segments → ~3,000 segments
        else:
            # Small dataset: no sampling
            return 1.0, 1  # 100% of data, 1-point segments → all points


    def generate(self, sample_rate: int = 1, color_by: str = 'altitude', flight_id: int = None, custom_metrics: dict = None) -> list:
        """
        Generate CZML data for the flight session

        Args:
            sample_rate: Sampling rate in Hz (1 = 1 point per second)
            color_by: What to color by ('altitude', 'speed', 'quality')
            flight_id: Optional flight ID to filter by (for multi-flight sessions)
            custom_metrics: Optional custom metric weights for quality calculation
                           Format: {'rsrp': 0.3, 'sinr': 0.5, 'rsrq': 0.2} for LTE
                                   or {'snr': 0.3, 'latency': 0.2, ...} for Starlink

        Returns:
            CZML data as list of dictionaries
        """
        self.custom_metrics = custom_metrics
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

        # 🛡️ CRITICAL: Sort by timestamp to prevent flight path teleportation/backward movement
        # GPS data may arrive out of order due to network delays or data collection timing
        df.sort_index(inplace=True)
        print(f"✅ Sorted by timestamp: {len(df)} points in chronological order")

        if df.empty:
            raise ValueError("No flight data available")

        # Calculate optimal sampling parameters based on data size
        original_len = len(df)
        auto_sampling_rate, auto_segment_interval = self._calculate_sampling_params(original_len)

        # Skip sampling for binary/quality modes to preserve rare events
        # Binary modes (connection_quality, roaming) have few positive samples that must not be lost
        skip_sampling_modes = ['starlink_connection_quality', 'starlink_roaming', 'lte_quality_combined', 'starlink_quality_combined']
        should_skip_sampling = color_by in skip_sampling_modes

        # Apply sampling if needed (fraction-based sampling)
        if should_skip_sampling:
            print(f"🎯 Skipping sampling for '{color_by}' mode (preserves rare events): {len(df)} points (100%)")
            # Still calculate segment interval for rendering
            self._segment_interval = auto_segment_interval
        elif auto_sampling_rate < 1.0:
            # Use interval-based sampling for consistent temporal distribution
            sample_interval = max(1, int(1 / auto_sampling_rate))
            df = df.iloc[::sample_interval].copy()
            print(f"🎯 Dynamic Sampling: {len(df)} points from {original_len} ({auto_sampling_rate*100:.0f}%, interval={sample_interval})")
            self._segment_interval = auto_segment_interval
        else:
            print(f"📊 No sampling needed: {len(df)} points (100%)")
            self._segment_interval = auto_segment_interval

        # Generate CZML document
        czml = []

        # Initialize color metadata
        self._color_metadata = None

        # Document header
        czml.append(self._create_document_header(df))

        # Flight path entity (single path only, colored by user selection)
        czml.extend(self._create_flight_path_entity(df, color_by))

        # Add color metadata to document header (custom property)
        if self._color_metadata:
            czml[0]['colorMetadata'] = self._color_metadata

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

        # 전체 경로를 Cartesian3 좌표로 변환 (시간 오프셋 제거)
        polyline_positions = []
        for i in range(0, len(positions), 4):
            lon = positions[i+1]
            lat = positions[i+2]
            alt = positions[i+3]
            polyline_positions.extend([lon, lat, alt])

        # Create multiple polyline segments for gradient effect
        # Note: Data is already sampled, now use dynamic segment interval
        segment_entities = []
        num_points = len(polyline_positions) // 3

        # Use dynamically calculated segment interval for optimal performance
        # This was calculated based on total data size in _calculate_sampling_params()
        segment_interval = self._segment_interval

        estimated_segments = num_points // segment_interval
        print(f"🎨 Creating gradient segments: {num_points} points, interval={segment_interval}, ~{estimated_segments} segments")

        # Use list comprehension for better performance
        for i in range(0, num_points - 1, segment_interval):
            # Get current and next point (or skip to interval point)
            start_idx = i * 3
            end_idx = min((i + segment_interval) * 3, (num_points - 1) * 3)

            segment_positions = [
                polyline_positions[start_idx],     # lon1
                polyline_positions[start_idx + 1], # lat1
                polyline_positions[start_idx + 2], # alt1
                polyline_positions[end_idx],       # lon2
                polyline_positions[end_idx + 1],   # lat2
                polyline_positions[end_idx + 2]    # alt2
            ]

            # Use color from start point
            segment_color = colors[i].tolist()

            segment_entities.append({
                "id": f"path_seg_{i}",  # Shorter ID for performance
                "polyline": {
                    "positions": {
                        "cartographicDegrees": segment_positions
                    },
                    "show": True,
                    "width": 8,
                    "material": {
                        "solidColor": {
                            "color": {
                                "rgba": segment_color
                            }
                        }
                    },
                    "clampToGround": False
                }
            })

        print(f"✅ Created {len(segment_entities)} gradient segments (reduced from {num_points-1})")

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

        # Return all segment entities plus aircraft entity
        return segment_entities + [aircraft_entity]

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

        # Auto-detect available Starlink column (latency only)
        starlink_column = None
        if 'starlink_latency' in df.columns and not df['starlink_latency'].isna().all():
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

    def _calculate_lte_quality_combined(self, df) -> np.ndarray:
        """
        Calculate combined LTE quality score

        Formula: RSRP 30% + SINR 50% + RSRQ 20% (default)
                 Or custom weights if self.custom_metrics is set

        Args:
            df: Flight data DataFrame with LTE columns

        Returns:
            Combined quality score (0-1 range, higher is better)
        """
        # Use custom weights if provided
        if hasattr(self, 'custom_metrics') and self.custom_metrics:
            # Map custom metric names to column names
            metric_map = {
                'rsrp': 'lte_rsrp',
                'sinr': 'lte_sinr',
                'rsrq': 'lte_rsrq',
                'rssi': 'lte_rssi'
            }

            combined = np.zeros(len(df))
            weights_used = []

            for metric_name, weight in self.custom_metrics.items():
                col_name = metric_map.get(metric_name)
                if col_name and col_name in df.columns:
                    values = df[col_name].values

                    # Normalize based on metric type
                    if metric_name == 'rsrp':
                        normalized = np.clip((values - (-140)) / ((-40) - (-140)), 0, 1)
                    elif metric_name == 'sinr':
                        normalized = np.clip((values - (-20)) / (30 - (-20)), 0, 1)
                    elif metric_name == 'rsrq':
                        normalized = np.clip((values - (-20)) / ((-3) - (-20)), 0, 1)
                    elif metric_name == 'rssi':
                        normalized = np.clip((values - (-120)) / ((-20) - (-120)), 0, 1)

                    combined += weight * normalized
                    weights_used.append(f"{metric_name.upper()}({weight*100:.0f}%)")

            if len(weights_used) == 0:
                raise ValueError(f"❌ No valid LTE metrics found in custom configuration")

            print(f"📊 LTE Custom Quality: {' + '.join(weights_used)}")
            return combined

        # Default: Check required columns
        required = ['lte_rsrp', 'lte_sinr', 'lte_rsrq']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"❌ LTE combined quality requires: {', '.join(missing)}")

        # Get values
        rsrp = df['lte_rsrp'].values
        sinr = df['lte_sinr'].values
        rsrq = df['lte_rsrq'].values

        # Normalize each parameter to 0-1 range
        # RSRP: -140 ~ -40 dBm (higher is better)
        rsrp_norm = np.clip((rsrp - (-140)) / ((-40) - (-140)), 0, 1)

        # SINR: -20 ~ 30 dB (higher is better)
        sinr_norm = np.clip((sinr - (-20)) / (30 - (-20)), 0, 1)

        # RSRQ: -20 ~ -3 dB (higher is better)
        rsrq_norm = np.clip((rsrq - (-20)) / ((-3) - (-20)), 0, 1)

        # Weighted combination: RSRP 30% + SINR 50% + RSRQ 20%
        combined = 0.30 * rsrp_norm + 0.50 * sinr_norm + 0.20 * rsrq_norm

        print(f"📊 LTE Combined Quality: RSRP(30%) + SINR(50%) + RSRQ(20%)")

        return combined

    def _calculate_starlink_quality_combined(self, df) -> np.ndarray:
        """
        Calculate combined Starlink quality score

        Formula: SNR 60% + Latency 40% (default, auto-fallback if one is missing)
                 Or custom weights if self.custom_metrics is set

        Args:
            df: Flight data DataFrame with Starlink columns

        Returns:
            Combined quality score (0-1 range, higher is better)
        """
        # Use custom weights if provided
        if hasattr(self, 'custom_metrics') and self.custom_metrics:
            # Map custom metric names to column names
            metric_map = {
                'latency': 'starlink_latency',
                'packet_loss': 'starlink_ping_drop_rate',
                'obstruction': 'starlink_raw_status.fraction_obstructed',
                'throughput_down': 'starlink_downlink_throughput_bps',
                'throughput_up': 'starlink_uplink_throughput_bps',
                'uptime': 'starlink_uptime'
            }

            combined = np.zeros(len(df))
            weights_used = []

            for metric_name, weight in self.custom_metrics.items():
                col_name = metric_map.get(metric_name)

                # Handle obstruction fallback
                if metric_name == 'obstruction':
                    if 'starlink_raw_status.fraction_obstructed' in df.columns:
                        col_name = 'starlink_raw_status.fraction_obstructed'
                    elif 'starlink_obstruction.valid_s' in df.columns:
                        col_name = 'starlink_obstruction.valid_s'
                    else:
                        continue

                if col_name and col_name in df.columns:
                    values = df[col_name].values

                    # Skip if all NaN
                    if np.isnan(values).all():
                        continue

                    # Normalize based on metric type
                    if metric_name == 'snr':
                        normalized = np.clip((values - 0) / (15 - 0), 0, 1)
                    elif metric_name == 'latency':
                        normalized = np.clip((values - 200) / (0 - 200), 0, 1)  # INVERTED
                    elif metric_name == 'packet_loss':
                        normalized = np.clip((values - 1.0) / (0.0 - 1.0), 0, 1)  # INVERTED
                    elif metric_name == 'obstruction':
                        normalized = np.clip((values - 1.0) / (0.0 - 1.0), 0, 1)  # INVERTED
                    elif metric_name == 'throughput_down':
                        values_mbps = values / 1_000_000
                        normalized = np.clip((values_mbps - 0) / (100 - 0), 0, 1)
                    elif metric_name == 'throughput_up':
                        values_mbps = values / 1_000_000
                        normalized = np.clip((values_mbps - 0) / (10 - 0), 0, 1)
                    elif metric_name == 'uptime':
                        values_hours = values / 3600
                        # Use actual min/max for uptime
                        vmin, vmax = np.nanmin(values_hours), np.nanmax(values_hours)
                        if vmax > vmin:
                            normalized = np.clip((values_hours - vmin) / (vmax - vmin), 0, 1)
                        else:
                            normalized = np.ones_like(values_hours)

                    combined += weight * normalized
                    weights_used.append(f"{metric_name.upper()}({weight*100:.0f}%)")

            if len(weights_used) == 0:
                raise ValueError(f"❌ No valid Starlink metrics found in custom configuration")

            print(f"📊 Starlink Custom Quality: {' + '.join(weights_used)}")
            return combined

        # Default: Use latency only (SNR no longer provided by Starlink API)
        has_latency = 'starlink_latency' in df.columns

        if not has_latency:
            raise ValueError(f"❌ Starlink combined quality requires starlink_latency")

        # Check data availability (not just column existence)
        latency_valid = has_latency and not df['starlink_latency'].isna().all()

        if not latency_valid:
            raise ValueError(f"❌ Starlink latency data is all NaN. Choose a different color mode.")

        # Use latency (100%)
        latency = df['starlink_latency'].values
        latency_norm = np.clip((latency - 200) / (0 - 200), 0, 1)
        combined = latency_norm
        print(f"📊 Starlink Combined Quality: Latency (100%)")

        return combined

    def _calculate_colors(self, df, color_by: str) -> np.ndarray:
        """
        Calculate colors for each position based on parameter

        Args:
            df: Flight data DataFrame
            color_by: What to color by ('altitude', 'speed', 'lte_rsrp', 'lte_sinr', 'starlink_latency', etc.)

        Returns:
            Array of RGBA color values (0-255)
        """
        # Determine which column to use
        column_name = color_by  # Track selected column name for error messages

        if color_by == 'altitude':
            values = df['altitude'].values
        elif color_by == 'speed':
            if 'speed_mps' not in df.columns:
                raise ValueError(f"❌ Speed data not available in this session")
            values = df['speed_mps'].values

        # LTE modes
        elif color_by == 'lte_quality_combined':
            values = self._calculate_lte_quality_combined(df)
            column_name = 'lte_quality_combined'
        elif color_by == 'lte_rsrp':
            if 'lte_rsrp' not in df.columns:
                raise ValueError(f"❌ LTE RSRP data not available in this session")
            values = df['lte_rsrp'].values
        elif color_by == 'lte_sinr':
            if 'lte_sinr' not in df.columns:
                raise ValueError(f"❌ LTE SINR data not available in this session")
            values = df['lte_sinr'].values
        elif color_by == 'lte_rsrq':
            if 'lte_rsrq' not in df.columns:
                raise ValueError(f"❌ LTE RSRQ data not available in this session")
            values = df['lte_rsrq'].values
        elif color_by == 'lte_rssi':
            if 'lte_rssi' not in df.columns:
                raise ValueError(f"❌ LTE RSSI data not available in this session")
            values = df['lte_rssi'].values

        # Starlink modes
        elif color_by == 'starlink_quality_combined':
            values = self._calculate_starlink_quality_combined(df)
            column_name = 'starlink_quality_combined'
        elif color_by == 'starlink_latency':
            if 'starlink_latency' not in df.columns:
                raise ValueError(f"❌ Starlink latency data not available in this session")
            values = df['starlink_latency'].values
        elif color_by == 'starlink_packet_loss':
            if 'starlink_ping_drop_rate' not in df.columns:
                raise ValueError(f"❌ Starlink packet loss data not available in this session")
            values = df['starlink_ping_drop_rate'].values
            column_name = 'starlink_packet_loss'
        elif color_by == 'starlink_throughput_down':
            if 'starlink_downlink_throughput_bps' not in df.columns:
                raise ValueError(f"❌ Starlink downlink throughput data not available in this session")
            values = df['starlink_downlink_throughput_bps'].values / 1_000_000  # Convert to Mbps
            column_name = 'starlink_throughput_down'
        elif color_by == 'starlink_throughput_up':
            if 'starlink_uplink_throughput_bps' not in df.columns:
                raise ValueError(f"❌ Starlink uplink throughput data not available in this session")
            values = df['starlink_uplink_throughput_bps'].values / 1_000_000  # Convert to Mbps
            column_name = 'starlink_throughput_up'
        elif color_by == 'starlink_connection_quality':
            # Binary classification: Good (>1 Mbps) vs Bad (<=1 Mbps)
            if 'starlink_uplink_throughput_bps' not in df.columns:
                raise ValueError(f"❌ Starlink uplink throughput data not available in this session")
            values = (df['starlink_uplink_throughput_bps'].values > 1_000_000).astype(float)  # 1 = good, 0 = bad
            column_name = 'starlink_connection_quality'
        elif color_by == 'starlink_roaming':
            # Roaming status: False (not roaming) = good, True (roaming) = bad
            if 'starlink_alerts.alert_roaming' not in df.columns:
                raise ValueError(f"❌ Starlink roaming alert data not available in this session")
            values = (~df['starlink_alerts.alert_roaming'].fillna(False)).astype(float)  # 1 = not roaming (good), 0 = roaming (bad)
            column_name = 'starlink_roaming'
        elif color_by == 'starlink_obstruction':
            # Try multiple field candidates (fallback logic)
            obstruction_candidates = ['starlink_raw_status.fraction_obstructed', 'starlink_obstruction.valid_s']
            obstruction_field = None
            for field in obstruction_candidates:
                if field in df.columns and not df[field].isna().all():
                    obstruction_field = field
                    break
            if not obstruction_field:
                raise ValueError(f"❌ Starlink obstruction data not available in this session")
            values = df[obstruction_field].values
            column_name = 'starlink_obstruction'
        elif color_by == 'starlink_uptime':
            if 'starlink_uptime' not in df.columns:
                raise ValueError(f"❌ Starlink uptime data not available in this session")
            values = df['starlink_uptime'].values / 3600  # Convert seconds to hours
            column_name = 'starlink_uptime'

        else:
            # Default to altitude
            print(f"⚠️ Unknown color_by '{color_by}', using altitude")
            values = df['altitude'].values
            column_name = 'altitude'

        # Check data availability (reject if >80% NaN)
        nan_count = np.sum(np.isnan(values))
        total_count = len(values)
        nan_ratio = nan_count / total_count if total_count > 0 else 1.0

        print(f"🔍 Data check: column={column_name}, NaN={nan_count}/{total_count} ({nan_ratio*100:.1f}%)")

        if nan_ratio > 0.8:
            error_msg = f"❌ Insufficient data for '{column_name}': {nan_ratio*100:.1f}% missing. Choose a different color mode."
            print(error_msg)
            raise ValueError(error_msg)

        # Normalize values to 0-1 range using percentile-based logic
        # Use 5th~95th percentile to focus on main distribution (exclude outliers)
        vmin_actual = np.nanpercentile(values, 5)   # 5th percentile
        vmax_actual = np.nanpercentile(values, 95)  # 95th percentile

        # Fallback to absolute min/max if percentiles are identical
        if vmax_actual <= vmin_actual:
            vmin_actual = np.nanmin(values)
            vmax_actual = np.nanmax(values)

        # Domain-specific normalization using actual data ranges
        if column_name == 'lte_quality_combined' or column_name == 'starlink_quality_combined':
            # Combined quality scores are already normalized 0-1
            normalized = values
            vmin, vmax = 0, 1
        elif column_name in ['lte_rsrp', 'lte_rssi', 'lte_sinr', 'lte_rsrq']:
            # LTE metrics: use actual min/max from data (higher is better)
            vmin, vmax = vmin_actual, vmax_actual
            if vmax > vmin:
                normalized = (values - vmin) / (vmax - vmin)
            else:
                normalized = np.zeros_like(values)
        elif column_name == 'starlink_latency':
            # Latency: use actual min/max from data (lower is better, INVERTED!)
            vmin, vmax = vmax_actual, vmin_actual  # Swap for inversion
            if vmax > vmin:
                normalized = (values - vmin) / (vmax - vmin)
            else:
                normalized = np.zeros_like(values)
        elif column_name == 'starlink_packet_loss':
            # Packet Loss: use actual min/max from data (lower is better, INVERTED!)
            vmin, vmax = vmax_actual, vmin_actual  # Swap for inversion
            if vmax > vmin:
                normalized = (values - vmin) / (vmax - vmin)
            else:
                normalized = np.zeros_like(values)
        elif column_name == 'starlink_throughput_down':
            # Downlink: use actual min/max from data (higher is better)
            vmin, vmax = vmin_actual, vmax_actual
            if vmax > vmin:
                normalized = (values - vmin) / (vmax - vmin)
            else:
                normalized = np.zeros_like(values)
        elif column_name == 'starlink_throughput_up':
            # Uplink: use actual min/max from data (higher is better)
            vmin, vmax = vmin_actual, vmax_actual
            if vmax > vmin:
                normalized = (values - vmin) / (vmax - vmin)
            else:
                normalized = np.zeros_like(values)
        elif column_name == 'starlink_connection_quality':
            # Binary: already 0 or 1 (0=bad, 1=good)
            normalized = values
            vmin, vmax = 0, 1
        elif column_name == 'starlink_roaming':
            # Binary: already 0 or 1 (0=roaming/bad, 1=not roaming/good)
            normalized = values
            vmin, vmax = 0, 1
        elif column_name == 'starlink_obstruction':
            # Obstruction: use actual min/max from data (lower is better, INVERTED!)
            vmin, vmax = vmax_actual, vmin_actual  # Swap for inversion
            if vmax > vmin:
                normalized = (values - vmin) / (vmax - vmin)
            else:
                normalized = np.zeros_like(values)
        elif column_name == 'starlink_uptime':
            # Uptime: use actual min/max (higher is better)
            vmin, vmax = vmin_actual, vmax_actual
            if vmax > vmin:
                normalized = (values - vmin) / (vmax - vmin)
            else:
                normalized = np.zeros_like(values)
        elif column_name == 'speed_mps':
            # Speed: use actual min/max (higher is faster = redder)
            vmin, vmax = vmin_actual, vmax_actual
            if vmax > vmin:
                normalized = (values - vmin) / (vmax - vmin)
            else:
                normalized = np.zeros_like(values)
        else:
            # altitude and others: use actual min/max
            vmin, vmax = vmin_actual, vmax_actual
            if vmax > vmin:
                normalized = (values - vmin) / (vmax - vmin)
            else:
                normalized = np.zeros_like(values)

        # Clamp to 0-1 range
        normalized = np.clip(normalized, 0, 1)

        # Store metadata for legend
        # For binary modes (connection_quality, roaming), always use 0-1 range even if data is uniform
        if column_name in ['starlink_connection_quality', 'starlink_roaming']:
            metadata_min, metadata_max = 0.0, 1.0
        else:
            # For other modes, use actual data range
            metadata_min, metadata_max = float(vmin_actual), float(vmax_actual)

        self._color_metadata = {
            'column': column_name,
            'min': metadata_min,
            'max': metadata_max,
            'unit': self._get_unit(column_name)
        }
        print(f"📊 Color range: {column_name} = {metadata_min:.2f} ~ {metadata_max:.2f} {self._color_metadata['unit']}")

        # Apply industry-standard colormap based on data type
        colors = self._apply_colormap(normalized, column_name)

        return colors

    def _get_unit(self, column_name: str) -> str:
        """Get unit for column"""
        if 'quality_combined' in column_name:
            return 'score'
        elif 'connection_quality' in column_name or 'roaming' in column_name:
            return ''  # Binary: Bad/Good or Roaming/Not Roaming
        elif 'rsrp' in column_name or 'rssi' in column_name or 'sinr' in column_name or 'rsrq' in column_name or 'snr' in column_name:
            return 'dB'
        elif 'latency' in column_name:
            return 'ms'
        elif 'packet_loss' in column_name or 'obstruction' in column_name:
            return 'ratio'
        elif 'throughput' in column_name:
            return 'Mbps'
        elif 'uptime' in column_name:
            return 'hours'
        elif 'altitude' in column_name:
            return 'm'
        elif 'speed' in column_name:
            return 'm/s'
        else:
            return ''

    def _apply_colormap(self, values: np.ndarray, column_name: str) -> np.ndarray:
        """
        Apply industry-standard colormap based on data type

        Args:
            values: Normalized values (0-1)
            column_name: Name of the data column (determines colormap)

        Returns:
            RGBA colors (0-255)
        """
        # Select appropriate colormap based on data type
        if 'altitude' in column_name:
            # Terrain colormap: 초록(평지) → 갈색(언덕) → 흰색(산)
            # Natural terrain colors from DEM/elevation mapping standards
            cmap = cm.terrain
            print(f"🎨 Using TERRAIN colormap (Green→Brown→White) for altitude")

        elif any(sig in column_name for sig in ['rsrp', 'rssi', 'sinr', 'rsrq', 'snr', 'latency', 'quality_combined',
                                                   'packet_loss', 'throughput', 'obstruction', 'uptime']):
            # Traffic light colormap: 빨강(약함) → 노랑(보통) → 초록(강함)
            # LTE/Telecom industry standard (reversed for low=bad, high=good)
            cmap = cm.RdYlGn  # Red-Yellow-Green reversed
            print(f"🎨 Using TRAFFIC LIGHT colormap (Red→Yellow→Green) for {column_name}")

        elif 'speed' in column_name:
            # Turbo colormap: 파랑(느림) → 초록/노랑 → 빨강(빠름)
            # Fluid dynamics standard for velocity visualization
            cmap = cm.turbo
            print(f"🎨 Using TURBO colormap (Blue→Green→Yellow→Red) for speed")

        else:
            # Fallback: jet colormap
            cmap = cm.jet
            print(f"🎨 Using JET colormap (fallback) for {column_name}")

        # Apply colormap
        n = len(values)
        colors = np.zeros((n, 4), dtype=np.uint8)

        for i, val in enumerate(values):
            if np.isnan(val):
                colors[i] = [128, 128, 128, 255]  # Gray for NaN
                continue

            # Get RGBA from matplotlib colormap (0-1 range)
            rgba = cmap(val)

            # Convert to 0-255 range
            colors[i] = [
                int(rgba[0] * 255),  # R
                int(rgba[1] * 255),  # G
                int(rgba[2] * 255),  # B
                255                   # A (fully opaque)
            ]

        return colors

    def _calculate_lte_colors(self, df) -> np.ndarray:
        """
        Calculate colors based on LTE RSRP values with smooth gradient

        RSRP range: -120 dBm (worst) to -40 dBm (best)
        Color gradient: Red → Orange → Yellow → Green → Cyan

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

        # Normalize RSRP to 0-1 range (-120 to -40 dBm)
        rsrp_min, rsrp_max = -120, -40
        normalized = np.clip((rsrp_values - rsrp_min) / (rsrp_max - rsrp_min), 0, 1)

        # Apply jet colormap for smooth gradient
        colors = self._viridis_colormap(normalized)

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

            # 🛡️ Skip invalid positions (NaN, Infinity, out of range)
            if np.isnan(lon) or np.isnan(lat) or np.isnan(alt):
                continue
            if np.isinf(lon) or np.isinf(lat) or np.isinf(alt):
                continue

            # 🛡️ CRITICAL: Validate lat/lon ranges to prevent visualization crashes
            # Latitude: -90 to +90, Longitude: -180 to +180
            if not (-90 <= lat <= 90):
                print(f"⚠️ Invalid latitude {lat:.6f} at {timestamp}, skipping")
                continue
            if not (-180 <= lon <= 180):
                print(f"⚠️ Invalid longitude {lon:.6f} at {timestamp}, skipping")
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

    def create_heatmap_czml(self, mode: str = 'lte', style: str = 'point', flight_id: int = None, altitude_bin_size: float = 25.0) -> list:
        """
        Generate heatmap CZML for data quality visualization

        Args:
            mode: 'lte', 'starlink', or 'combined'
            style: 'point' or 'voxel' (default: 'point')
            flight_id: Optional flight ID to filter by (for multi-flight sessions)
            altitude_bin_size: Altitude bin size in meters for 3D voxel layers (default: 25.0)

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

        # 🛡️ CRITICAL: Sort by timestamp (same as flight path)
        df.sort_index(inplace=True)

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
            heatmap_entities = self._create_voxel_heatmap_entities(df, mode, altitude_bin_size)
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
        if 'starlink_latency' in df.columns and not df['starlink_latency'].isna().all():
            starlink_column = 'starlink_latency'

        print(f"🗺️ Generating {mode.upper()} heatmap: LTE={lte_column}, Starlink={starlink_column}", flush=True)

        # Create point entity for each GPS coordinate
        point_count = 0
        for idx, row in df.iterrows():
            lon = row['longitude']
            lat = row['latitude']
            alt = row['altitude']

            # 🛡️ Skip invalid positions (NaN, Infinity, out of range)
            if np.isnan(lon) or np.isnan(lat) or np.isnan(alt):
                continue
            if np.isinf(lon) or np.isinf(lat) or np.isinf(alt):
                continue
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
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
            column_name: 'starlink_latency'

        Returns:
            Quality score (0-100)
        """
        if np.isnan(value):
            return np.nan

        if column_name == 'starlink_latency':
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

        Uses industry-standard traffic light colormap (Red-Yellow-Green)
        - Red (0): Very poor signal
        - Orange/Yellow (50): Fair signal
        - Green (100): Excellent signal

        Args:
            quality_score: Quality score (0-100)

        Returns:
            RGBA color [R, G, B, A]
        """
        # Normalize to 0-1 range
        normalized = np.clip(quality_score / 100.0, 0, 1)

        # Use RdYlGn_r colormap (Traffic light standard: Red=bad, Green=good)
        cmap = cm.RdYlGn
        rgba = cmap(normalized)

        # Convert to 0-255 range
        return [
            int(rgba[0] * 255),  # R
            int(rgba[1] * 255),  # G
            int(rgba[2] * 255),  # B
            255                   # A (fully opaque)
        ]

    def _create_voxel_heatmap_entities(self, df, mode: str, altitude_bin_size: float = 25.0) -> list:
        """
        Create voxel (3D grid box) entities for heatmap visualization

        Args:
            df: Flight data DataFrame
            mode: 'lte', 'starlink', or 'combined'
            altitude_bin_size: Altitude bin size in meters for 3D voxel layers (default: 25.0)

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
        if 'starlink_latency' in df.columns and not df['starlink_latency'].isna().all():
            starlink_column = 'starlink_latency'

        print(f"🔲 Generating {mode.upper()} voxel heatmap: LTE={lte_column}, Starlink={starlink_column}", flush=True)

        # Calculate bounding box
        lon_min, lon_max = df['longitude'].min(), df['longitude'].max()
        lat_min, lat_max = df['latitude'].min(), df['latitude'].max()
        alt_min, alt_max = df['altitude'].min(), df['altitude'].max()

        # Voxel size configuration (in meters, converted to degrees for lat/lon)
        # Aviation visualization standard: 50m horizontal, altitude_bin_size vertical
        voxel_size_horizontal = 50  # 50 meters
        voxel_size_vertical = altitude_bin_size  # Use altitude_bin_size parameter (consistent with hexagon)

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

    def generate_satellite_direction_arrows(self, sample_rate: int = 1, color_by: str = 'starlink_latency', flight_id: int = None, arrow_length: int = 10) -> list:
        """
        Generate CZML with 3D arrows showing satellite direction

        Args:
            sample_rate: Sampling rate in Hz (default: 1)
            color_by: What to color arrows by (default: 'starlink_latency')
            flight_id: Optional flight ID filter
            arrow_length: Arrow length in meters (default: 10)

        Returns:
            CZML data with polyline arrows
        """
        # Load merged data
        results_dir = Path(__file__).parent.parent.parent / 'results' / self.session_id
        merged_data_path = results_dir / 'merged_data.csv'

        if not merged_data_path.exists():
            raise ValueError(f"No merged data found for session {self.session_id}")

        df = pd.read_csv(merged_data_path)
        # Ensure timestamp is datetime (handle mixed formats with ISO8601)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')

        # Filter by flight_id if specified
        if flight_id is not None and 'flight_id' in df.columns:
            df = df[df['flight_id'] == flight_id].copy()
            if df.empty:
                raise ValueError(f"No data found for flight_id {flight_id}")

        # Check required columns
        required = ['latitude', 'longitude', 'altitude', 'starlink_azimuth', 'starlink_elevation']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"❌ Satellite direction requires: {', '.join(missing)}")

        # Filter out NaN values in azimuth/elevation
        df_valid = df.dropna(subset=['starlink_azimuth', 'starlink_elevation'])
        if df_valid.empty:
            raise ValueError(f"❌ No valid satellite direction data available")

        # Use latency for coloring (SNR no longer provided by Starlink API)
        if 'starlink_latency' not in df_valid.columns:
            raise ValueError(f"❌ Starlink latency data not available")
        df_valid = df_valid.dropna(subset=['starlink_latency'])
        quality_column = 'starlink_latency'
        vmin, vmax = 200, 0  # INVERTED
        print(f"✅ Using starlink_latency for coloring ({len(df_valid)} points)")

        if df_valid.empty:
            raise ValueError(f"❌ No valid satellite direction data with quality values")

        # Apply sampling
        if sample_rate < 1:
            interval = int(1 / sample_rate)
            df_sampled = df_valid.iloc[::interval].copy()
        else:
            df_sampled = df_valid.copy()

        # Get quality values for coloring
        quality_values = df_sampled[quality_column].values

        # Normalize quality values
        quality_norm = np.clip((quality_values - vmin) / (vmax - vmin), 0, 1)

        # Generate CZML document
        czml_document = [
            {
                "id": "document",
                "name": f"Satellite Direction Arrows - {self.session_id}",
                "version": "1.0",
                "clock": {
                    "interval": f"{df_sampled['timestamp'].min().isoformat()}/{df_sampled['timestamp'].max().isoformat()}",
                    "currentTime": df_sampled['timestamp'].min().isoformat(),
                    "multiplier": 1,
                    "range": "LOOP_STOP",
                    "step": "SYSTEM_CLOCK_MULTIPLIER"
                }
            }
        ]

        # Traffic Light colormap for quality
        traffic_light_colors = np.array([
            [215, 25, 28, 255],      # 0.0 - Red (worst)
            [253, 174, 97, 255],     # 0.25 - Orange
            [255, 255, 191, 255],    # 0.5 - Yellow
            [166, 217, 106, 255],    # 0.75 - Light green
            [26, 150, 65, 255]       # 1.0 - Green (best)
        ])

        # Create polyline arrows
        arrow_count = 0
        for idx, row in df_sampled.iterrows():
            lat = row['latitude']
            lon = row['longitude']
            alt = row['altitude']
            azimuth = row['starlink_azimuth']
            elevation = row['starlink_elevation']
            quality = quality_norm[arrow_count]

            # Convert spherical coordinates to Cartesian offset
            # Azimuth: 0° = North, 90° = East, 180° = South, 270° = West
            # Elevation: 0° = Horizon, 90° = Zenith
            azimuth_rad = np.radians(azimuth)
            elevation_rad = np.radians(elevation)

            # Calculate 3D vector in local ENU (East-North-Up) coordinates
            # Then convert to geographic offset (approximate for short distances)
            dx_east = arrow_length * np.cos(elevation_rad) * np.sin(azimuth_rad)
            dy_north = arrow_length * np.cos(elevation_rad) * np.cos(azimuth_rad)
            dz_up = arrow_length * np.sin(elevation_rad)

            # Convert meters to degrees (approximate)
            meters_per_degree_lat = 111320  # Constant
            meters_per_degree_lon = 111320 * np.cos(np.radians(lat))

            end_lon = lon + (dx_east / meters_per_degree_lon)
            end_lat = lat + (dy_north / meters_per_degree_lat)
            end_alt = alt + dz_up

            # Get color from quality
            color_idx = int(quality * (len(traffic_light_colors) - 1))
            color = traffic_light_colors[color_idx]

            # Create polyline entity (arrow)
            entity = {
                "id": f"sat_arrow_{arrow_count}",
                "polyline": {
                    "positions": {
                        "cartographicDegrees": [
                            lon, lat, alt,
                            end_lon, end_lat, end_alt
                        ]
                    },
                    "material": {
                        "polylineArrow": {
                            "color": {
                                "rgba": color.tolist()
                            }
                        }
                    },
                    "width": 4,
                    "arcType": "NONE"  # Straight line, not geodesic
                }
            }
            czml_document.append(entity)
            arrow_count += 1

        print(f"✅ Created {arrow_count} satellite direction arrows", flush=True)
        return czml_document

    def generate_tower_connections(self, sample_rate: float = 0.2, flight_id: int = None) -> list:
        """
        Generate CZML data for LTE tower connections with time-dynamic polylines

        Shows which LTE tower the drone is connected to at each point in time,
        with lines colored by signal strength (RSRP).

        Args:
            sample_rate: Sampling rate in Hz (default: 0.2 = 1 point per 5 seconds)
            flight_id: Optional flight ID to filter by

        Returns:
            CZML document with time-dynamic tower connection polylines
        """
        # Load merged data
        results_dir = Path(__file__).parent.parent.parent / 'results' / self.session_id
        merged_data_path = results_dir / 'merged_data.csv'

        if not merged_data_path.exists():
            raise ValueError(f"No merged data found for session {self.session_id}")

        df = pd.read_csv(merged_data_path)
        # Ensure timestamp is datetime (handle mixed formats)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')

        # Filter by flight_id if specified
        if flight_id is not None and 'flight_id' in df.columns:
            df = df[df['flight_id'] == flight_id].copy()
            if df.empty:
                raise ValueError(f"No data found for flight_id {flight_id}")

        # Check required columns
        required = ['latitude', 'longitude', 'altitude', 'lte_cell_id']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"❌ Tower connections require: {', '.join(missing)}")

        # Filter out rows without LTE cell ID
        df_valid = df.dropna(subset=['lte_cell_id']).copy()
        if df_valid.empty:
            raise ValueError(f"❌ No LTE cell connection data available")

        print(f"📡 Processing {len(df_valid)} LTE connection points...", flush=True)

        # Detect cell changes (handovers)
        df_valid['cell_changed'] = df_valid['lte_cell_id'] != df_valid['lte_cell_id'].shift(1)
        df_valid['connection_segment'] = df_valid['cell_changed'].cumsum()

        # 🚀 Use high-accuracy tower positions from Cell Towers API (hybrid algorithm)
        # This ensures tower connections use the same positions as cell tower markers
        print(f"  🎯 Loading high-accuracy tower positions from Cell Towers API...", flush=True)

        # Import Cell Towers API logic
        from .routes import get_cell_towers_geojson_internal

        try:
            # Get tower positions from Cell Towers API (uses hybrid estimation + physical filtering)
            tower_geojson = get_cell_towers_geojson_internal(self.session_id, flight_id=flight_id)

            if not tower_geojson or 'features' not in tower_geojson:
                raise ValueError(f"❌ No cell tower data available from API")

            # Convert GeoJSON to tower positions dictionary
            # ✨ CRITICAL: Map ALL cell_ids (not just primary) to same tower position
            cell_tower_positions = {}
            for feature in tower_geojson['features']:
                props = feature['properties']
                coords = feature['geometry']['coordinates']  # [lon, lat, alt]

                # Extract primary Cell ID
                primary_cell_id = props.get('cid', '').upper()
                if not primary_cell_id or primary_cell_id in ['0', 'FFFFFFFF', 'NAN']:
                    continue

                # Get ALL cell_ids for this eNodeB (all sectors)
                all_cell_ids = props.get('all_cell_ids', [primary_cell_id])
                if isinstance(all_cell_ids, str):
                    all_cell_ids = [all_cell_ids]

                # Create tower position data
                tower_data = {
                    'lat': coords[1],
                    'lon': coords[0],
                    'alt': coords[2] if len(coords) > 2 else 50,
                    'cellid': primary_cell_id,
                    'connection_count': props.get('connection_count', 0),
                    'position_method': props.get('position_method', 'Unknown')
                }

                # ✨ Map ALL cell_ids to the SAME tower position
                # This ensures connections work for ALL sectors, not just the primary one
                for cell_id in all_cell_ids:
                    cell_id_key = str(cell_id).upper()
                    if cell_id_key and cell_id_key not in ['0', 'FFFFFFFF', 'NAN']:
                        cell_tower_positions[cell_id_key] = tower_data.copy()

            print(f"  ✅ Loaded {len(cell_tower_positions)} cell_id mappings from Cell Towers API", flush=True)

            # Show tower statistics (group by unique tower positions)
            unique_towers = {}
            for cell_id, tower in cell_tower_positions.items():
                tower_key = (tower['lat'], tower['lon'])
                if tower_key not in unique_towers:
                    unique_towers[tower_key] = {
                        'cell_ids': [],
                        'tower': tower
                    }
                unique_towers[tower_key]['cell_ids'].append(cell_id)

            print(f"  📊 {len(unique_towers)} physical towers with {len(cell_tower_positions)} total cell_id mappings:", flush=True)
            for tower_key, info in unique_towers.items():
                tower = info['tower']
                cell_ids = ', '.join(info['cell_ids'])
                method = tower.get('position_method', 'Unknown')
                print(f"    📍 Tower at ({tower['lat']:.6f}, {tower['lon']:.6f}): {len(info['cell_ids'])} cell_ids [{cell_ids}] - {tower['connection_count']} connections [{method}]", flush=True)

        except Exception as e:
            print(f"  ⚠️ Failed to load from Cell Towers API: {e}", flush=True)
            print(f"  ⚠️ Falling back to basic median calculation...", flush=True)

            # Fallback: Basic median calculation (old method)
            cell_tower_positions = {}
            unique_cells = df_valid['lte_cell_id'].unique()

            for cell_id in unique_cells:
                if cell_id in ['0', 'FFFFFFFF', 0, 'nan'] or pd.isna(cell_id):
                    continue

                cell_data = df_valid[df_valid['lte_cell_id'] == cell_id]

                tower_lat = cell_data['latitude'].median()
                tower_lon = cell_data['longitude'].median()

                cell_tower_positions[str(cell_id).upper()] = {
                    'lat': tower_lat,
                    'lon': tower_lon,
                    'alt': 50,
                    'cellid': str(cell_id).upper(),
                    'connection_count': len(cell_data)
                }

        if not cell_tower_positions:
            raise ValueError(f"❌ No valid LTE cell IDs found in data")

        # Process each connection segment
        segments = []
        handover_count = 0
        skipped_segments = 0
        skipped_reasons = {}

        total_segments = len(df_valid.groupby('connection_segment'))
        unique_cell_ids_in_data = df_valid['lte_cell_id'].unique()
        print(f"  📊 Total connection segments to process: {total_segments}", flush=True)
        print(f"  📊 Unique cell_ids in flight data: {len(unique_cell_ids_in_data)}", flush=True)
        print(f"      Cell IDs: {[str(c).upper() for c in unique_cell_ids_in_data[:20]]}", flush=True)
        print(f"  📊 Cell IDs in tower positions dict: {len(cell_tower_positions)}", flush=True)
        print(f"      Dict keys: {list(cell_tower_positions.keys())[:20]}", flush=True)

        for segment_id, group in df_valid.groupby('connection_segment'):
            cell_id = str(group.iloc[0]['lte_cell_id']).upper()

            # Skip invalid cell IDs
            if cell_id in ['0', 'FFFFFFFF', 'NAN']:
                skipped_segments += 1
                skipped_reasons[cell_id] = skipped_reasons.get(cell_id, 0) + 1
                continue

            if cell_id not in cell_tower_positions:
                skipped_segments += 1
                skipped_reasons[f"NOT_FOUND:{cell_id}"] = skipped_reasons.get(f"NOT_FOUND:{cell_id}", 0) + 1
                continue

            start_time = group['timestamp'].min()
            end_time = group['timestamp'].max()
            duration = (end_time - start_time).total_seconds()

            # Get average signal strength for this segment
            rsrp = group['lte_rsrp'].mean() if 'lte_rsrp' in group.columns else -100

            # Get tower position for this Cell ID
            tower_pos = cell_tower_positions[cell_id]

            # Apply sampling to reduce polyline count
            if sample_rate < 1:
                interval = max(1, int(1 / sample_rate))
                group_sampled = group.iloc[::interval]
            else:
                group_sampled = group

            segments.append({
                'cell_id': cell_id,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'drone_positions': group_sampled[['longitude', 'latitude', 'altitude']].values,
                'tower_lon': tower_pos['lon'],
                'tower_lat': tower_pos['lat'],
                'tower_alt': tower_pos['alt'],
                'rsrp': rsrp,
                'point_count': len(group_sampled)
            })

            if segment_id > 0:  # Count handovers (skip first segment)
                handover_count += 1

        print(f"  ✅ Created {len(segments)} valid segments, skipped {skipped_segments} segments", flush=True)
        if skipped_reasons:
            print(f"  📋 Skip reasons:", flush=True)
            for reason, count in sorted(skipped_reasons.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"      - {reason}: {count} segments", flush=True)
        print(f"  🔄 Detected {handover_count} handovers", flush=True)

        if not segments:
            raise ValueError(f"❌ No valid tower connection segments found in data")

        # Generate CZML document
        first_time = segments[0]['start_time']
        last_time = segments[-1]['end_time']

        czml_document = [
            {
                "id": "document",
                "name": f"LTE Tower Connections - {self.session_id}",
                "version": "1.0",
                "clock": {
                    "interval": f"{first_time.isoformat()}/{last_time.isoformat()}",
                    "currentTime": first_time.isoformat(),
                    "multiplier": 1,
                    "range": "LOOP_STOP",
                    "step": "SYSTEM_CLOCK_MULTIPLIER"
                }
            }
        ]

        # Signal strength color mapping (RSRP-based)
        def get_signal_color(rsrp):
            """Get color based on RSRP value"""
            if rsrp > -80:  # Strong signal
                return [0, 255, 0, 180]  # Green
            elif rsrp > -100:  # Medium signal
                return [255, 255, 0, 180]  # Yellow
            else:  # Weak signal
                return [255, 0, 0, 180]  # Red

        # Create connection polylines for each segment
        polyline_count = 0
        for idx, segment in enumerate(segments):
            start_iso = segment['start_time'].isoformat()
            end_iso = segment['end_time'].isoformat()
            color = get_signal_color(segment['rsrp'])

            # Create multiple polylines (one for each drone position in segment)
            for pos_idx, drone_pos in enumerate(segment['drone_positions']):
                drone_lon, drone_lat, drone_alt = drone_pos

                entity = {
                    "id": f"tower_conn_{idx}_{pos_idx}",
                    "availability": f"{start_iso}/{end_iso}",
                    "polyline": {
                        "positions": {
                            "cartographicDegrees": [
                                drone_lon, drone_lat, drone_alt,
                                segment['tower_lon'], segment['tower_lat'], segment['tower_alt']
                            ]
                        },
                        "material": {
                            "polylineOutline": {
                                "color": {"rgba": color},
                                "outlineColor": {"rgba": [0, 0, 0, 255]},
                                "outlineWidth": 1
                            }
                        },
                        "width": 3,
                        "arcType": "NONE"  # Straight line
                    }
                }
                czml_document.append(entity)
                polyline_count += 1

        print(f"✅ Created {polyline_count} tower connection polylines for {len(segments)} segments", flush=True)
        print(f"  📊 Signal strength: Strong={sum(1 for s in segments if s['rsrp'] > -80)}, "
              f"Medium={sum(1 for s in segments if -100 < s['rsrp'] <= -80)}, "
              f"Weak={sum(1 for s in segments if s['rsrp'] <= -100)}", flush=True)

        return czml_document
