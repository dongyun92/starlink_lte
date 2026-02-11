"""
Hexagonal Heatmap Generator for Cesium 3D Visualization

Uses H3 hexagonal grid system for spatially aggregated quality metrics.
Generates CZML polygons with color-coded and height-extruded visualizations.
"""

from typing import List, Dict, Optional, Tuple
import h3
import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class ColorPoint:
    """Jet colormap control point"""
    value: float
    rgb: Tuple[int, int, int]


class HexagonalHeatmapGenerator:
    """
    Generates H3 hexagonal grid heatmaps for signal quality visualization.

    H3 Resolution Reference:
    - Resolution 7: 1.22 km edge, 3.87 km² area
    - Resolution 8: 461 m edge, 737,327 m² area (RECOMMENDED)
    - Resolution 9: 174 m edge, 105,332 m² area
    - Resolution 10: 66 m edge, 15,047 m² area
    """

    # Jet colormap: Blue → Cyan → Green → Yellow → Orange → Red
    JET_COLORMAP = [
        ColorPoint(0.0, (0, 0, 143)),      # Dark Blue
        ColorPoint(0.1, (0, 0, 255)),      # Blue
        ColorPoint(0.25, (0, 128, 255)),   # Cyan
        ColorPoint(0.4, (0, 255, 255)),    # Light Cyan
        ColorPoint(0.5, (0, 255, 128)),    # Cyan-Green
        ColorPoint(0.6, (0, 255, 0)),      # Green
        ColorPoint(0.7, (128, 255, 0)),    # Yellow-Green
        ColorPoint(0.8, (255, 255, 0)),    # Yellow
        ColorPoint(0.9, (255, 128, 0)),    # Orange
        ColorPoint(0.95, (255, 64, 0)),    # Dark Orange
        ColorPoint(1.0, (255, 0, 0)),      # Red
    ]

    # Domain-specific value ranges for normalization (UNIFIED with czml_generator.py)
    DOMAIN_RANGES = {
        'lte_rsrp': (-140, -40),      # dBm (higher = better) - TELECOM STANDARD
        'lte_rssi': (-120, -20),      # dBm (higher = better)
        'lte_sinr': (-20, 30),        # dB (higher = better)
        'lte_rsrq': (-20, -3),        # dB (higher = better)
        'starlink_snr': (0, 15),      # dB (higher = better)
        'starlink_latency': (0, 200), # ms (lower = better) - NORMAL RANGE, inverted in normalize
        'altitude': None,             # Use actual min/max
        'speed': None,                # Use actual min/max
    }

    def __init__(self, resolution: int = 8, altitude_bin_size: float = 25.0):
        """
        Initialize hexagonal heatmap generator.

        Args:
            resolution: H3 resolution level (7-10). Default 8 (461m edge).
            altitude_bin_size: Altitude bin size in meters for 3D voxel layers (default 25m).
        """
        if not 7 <= resolution <= 10:
            raise ValueError("Resolution must be between 7 and 10")
        self.resolution = resolution
        self.altitude_bin_size = altitude_bin_size

    def generate_czml(
        self,
        df: pd.DataFrame,
        mode: str,
        aggregation: str = 'mean',
        extrusion_height: float = 200.0
    ) -> List[Dict]:
        """
        Generate CZML hexagonal heatmap from flight data.

        Args:
            df: DataFrame with columns: latitude, longitude, [quality_column]
            mode: Quality metric ('lte_rsrp', 'starlink_snr', 'altitude', etc.)
            aggregation: Aggregation method ('mean', 'max', 'min', 'median')
            extrusion_height: Maximum extrusion height in meters (default 200)

        Returns:
            List of CZML packets (document + polygons)
        """
        # Validate input
        if df.empty:
            return self._create_empty_czml()

        # Get quality column with fallback
        quality_col = self._get_quality_column(mode)

        # Fallback for starlink_snr → starlink_latency if SNR not available
        if quality_col == 'starlink_snr' and quality_col not in df.columns:
            print(f"⚠️ {quality_col} not available, falling back to starlink_latency")
            quality_col = 'starlink_latency'
            mode = 'starlink_latency'  # Update mode for normalization
        elif quality_col == 'starlink_snr' and df[quality_col].isna().all():
            print(f"⚠️ {quality_col} has no valid data, falling back to starlink_latency")
            quality_col = 'starlink_latency'
            mode = 'starlink_latency'

        if quality_col not in df.columns:
            raise ValueError(f"Column '{quality_col}' not found in DataFrame")

        # Check if altitude column exists
        if 'altitude' not in df.columns:
            raise ValueError("altitude column required for 3D hexagonal voxel grid")

        # Filter out NaN values (include altitude)
        df_clean = df[['latitude', 'longitude', 'altitude', quality_col]].dropna()
        if df_clean.empty:
            return self._create_empty_czml()

        # Step 1: Create altitude bins for 3D voxel layers
        df_clean = df_clean.copy()
        altitude_min = df_clean['altitude'].min()
        altitude_max = df_clean['altitude'].max()

        # Create bins from altitude_min to altitude_max with altitude_bin_size steps
        num_bins = int(np.ceil((altitude_max - altitude_min) / self.altitude_bin_size))
        bins = [altitude_min + i * self.altitude_bin_size for i in range(num_bins + 1)]

        # Assign altitude bins
        df_clean['altitude_bin'] = pd.cut(
            df_clean['altitude'],
            bins=bins,
            labels=[i for i in range(num_bins)],
            include_lowest=True
        )

        # Calculate midpoint altitude for each bin
        df_clean['altitude_mid'] = df_clean['altitude_bin'].apply(
            lambda x: altitude_min + (float(x) + 0.5) * self.altitude_bin_size if pd.notna(x) else np.nan
        )

        # Remove rows where altitude_bin assignment failed
        df_clean = df_clean.dropna(subset=['altitude_bin', 'altitude_mid'])
        if df_clean.empty:
            return self._create_empty_czml()

        print(f"📊 3D Voxel Grid: {num_bins} altitude layers ({altitude_min:.1f}m - {altitude_max:.1f}m, {self.altitude_bin_size}m bins)")

        # Step 2: Convert GPS coordinates to H3 cells
        df_clean['h3_cell'] = df_clean.apply(
            lambda row: h3.latlng_to_cell(row['latitude'], row['longitude'], self.resolution),
            axis=1
        )

        # Step 3: Aggregate quality metrics per (H3 cell, altitude_bin)
        agg_func = self._get_aggregation_function(aggregation)
        grouped = df_clean.groupby(['h3_cell', 'altitude_bin', 'altitude_mid'], observed=True)[quality_col].agg(agg_func).reset_index()
        grouped.columns = ['h3_cell', 'altitude_bin', 'altitude_mid', 'quality_value']

        # Remove NaN quality values (can occur if no data in some groups)
        grouped = grouped.dropna(subset=['quality_value'])
        if grouped.empty:
            return self._create_empty_czml()

        # Step 4: Normalize quality values (0-1)
        normalized_values = self._normalize_values(grouped['quality_value'], mode)
        grouped['normalized'] = normalized_values

        # Step 5: Generate CZML polygons (3D voxel layers)
        czml_packets = [self._create_czml_document()]

        for _, row in grouped.iterrows():
            h3_cell = row['h3_cell']
            altitude_bin = int(row['altitude_bin'])
            altitude_mid = row['altitude_mid']
            quality = row['quality_value']
            normalized = row['normalized']

            # Get hexagon boundary coordinates
            boundary = h3.cell_to_boundary(h3_cell)

            # Convert to lon, lat order (GeoJSON/CZML format)
            polygon_coords = [[lon, lat] for lat, lon in boundary]
            polygon_coords.append(polygon_coords[0])  # Close polygon

            # Get color from RdYlGn_r colormap (Red=bad, Green=good)
            color = self._get_quality_color(normalized)

            # For 3D voxel: place hexagon at altitude_mid, with thickness = altitude_bin_size
            base_altitude = altitude_mid - self.altitude_bin_size / 2
            top_altitude = altitude_mid + self.altitude_bin_size / 2

            # Create CZML polygon packet (3D voxel layer)
            czml_packet = self._create_polygon_packet_3d(
                h3_cell=h3_cell,
                altitude_bin=altitude_bin,
                polygon_coords=polygon_coords,
                color=color,
                base_altitude=base_altitude,
                top_altitude=top_altitude,
                quality_value=quality
            )
            czml_packets.append(czml_packet)

        return czml_packets

    def _get_quality_column(self, mode: str) -> str:
        """Map mode to actual DataFrame column name"""
        mode_map = {
            'lte_rsrp': 'lte_rsrp',
            'lte_rssi': 'lte_rssi',
            'lte_sinr': 'lte_sinr',
            'lte_rsrq': 'lte_rsrq',
            'starlink_snr': 'starlink_snr',
            'starlink_latency': 'starlink_latency',
            'altitude': 'altitude',
            'speed': 'speed_mps',
        }
        return mode_map.get(mode, mode)

    def _get_aggregation_function(self, aggregation: str):
        """Get pandas aggregation function"""
        agg_map = {
            'mean': 'mean',
            'max': 'max',
            'min': 'min',
            'median': 'median',
        }
        return agg_map.get(aggregation, 'mean')

    def _normalize_values(self, values: pd.Series, mode: str) -> np.ndarray:
        """
        Normalize values to 0-1 range using domain-specific ranges.

        UNIFIED normalization (consistent with czml_generator.py):
        - For most metrics: higher value = better quality = 1
        - For latency: lower value = better quality = 1 (INVERTED)

        Args:
            values: Series of quality values
            mode: Quality metric name

        Returns:
            Normalized values (0-1) where 1 = best quality
        """
        if mode in self.DOMAIN_RANGES and self.DOMAIN_RANGES[mode] is not None:
            vmin, vmax = self.DOMAIN_RANGES[mode]
        else:
            # Use actual min/max for altitude, speed
            vmin, vmax = values.min(), values.max()

        # Normalize to 0-1
        normalized = (values - vmin) / (vmax - vmin)
        normalized = np.clip(normalized, 0, 1)

        # Invert for latency (lower latency = better quality)
        if 'latency' in mode:
            normalized = 1 - normalized

        return normalized.values

    def _get_quality_color(self, normalized_value: float) -> Tuple[int, int, int, int]:
        """
        Get RGBA color from RdYlGn_r colormap for normalized value (0-1).

        UNIFIED Color mapping (consistent with Voxel and Path colors):
        - 0 (bad quality) → Red
        - 0.5 (medium quality) → Yellow
        - 1 (good quality) → Green

        Uses industry-standard traffic light colormap (Red-Yellow-Green reversed)

        Args:
            normalized_value: Value between 0 and 1 (0=bad, 1=good)

        Returns:
            RGBA tuple (R, G, B, A) where each is 0-255
        """
        from matplotlib import cm

        # Clamp value to [0, 1]
        value = np.clip(normalized_value, 0, 1)

        # Use RdYlGn colormap (Traffic light standard: Red=bad, Green=good)
        # Note: RdYlGn (NOT reversed) because our normalization gives high values for good quality
        cmap = cm.RdYlGn
        rgba = cmap(value)

        # Convert to 0-255 range
        r = int(rgba[0] * 255)
        g = int(rgba[1] * 255)
        b = int(rgba[2] * 255)
        a = 200  # 78% opacity

        return (r, g, b, a)

    def _create_czml_document(self) -> Dict:
        """Create CZML document header"""
        return {
            "id": "document",
            "name": "H3 Hexagonal Heatmap",
            "version": "1.0",
            "clock": {
                "interval": "2024-01-01T00:00:00Z/2024-12-31T23:59:59Z",
                "currentTime": "2024-01-01T00:00:00Z",
                "multiplier": 1
            }
        }

    def _create_polygon_packet_3d(
        self,
        h3_cell: str,
        altitude_bin: int,
        polygon_coords: List[List[float]],
        color: Tuple[int, int, int, int],
        base_altitude: float,
        top_altitude: float,
        quality_value: float
    ) -> Dict:
        """
        Create CZML polygon packet for a 3D voxel hexagon layer.

        Args:
            h3_cell: H3 cell ID
            altitude_bin: Altitude bin index
            polygon_coords: List of [lon, lat] coordinates
            color: RGBA color tuple (R, G, B, A)
            base_altitude: Base altitude of voxel layer in meters
            top_altitude: Top altitude of voxel layer in meters
            quality_value: Original quality metric value

        Returns:
            CZML polygon packet
        """
        # Flatten coordinates with base altitude
        flat_coords = []
        for lon, lat in polygon_coords:
            flat_coords.extend([lon, lat, base_altitude])

        return {
            "id": f"hexagon_{h3_cell}_alt{altitude_bin}",
            "name": f"H3 Cell {h3_cell} @ {base_altitude:.0f}-{top_altitude:.0f}m",
            "description": f"Altitude: {base_altitude:.0f}-{top_altitude:.0f}m\nQuality: {quality_value:.2f}",
            "polygon": {
                "positions": {
                    "cartographicDegrees": flat_coords
                },
                "material": {
                    "solidColor": {
                        "color": {
                            "rgba": [color[0], color[1], color[2], color[3]]
                        }
                    }
                },
                "outline": True,
                "outlineColor": {
                    "rgba": [255, 255, 255, 80]  # White outline with 31% opacity (reduced for clarity)
                },
                "outlineWidth": 1.0,
                "extrudedHeight": top_altitude,  # Top of the voxel layer
                "perPositionHeight": True,  # Use altitude from positions
                "closeTop": True,
                "closeBottom": True
            }
        }

    def _create_empty_czml(self) -> List[Dict]:
        """Create empty CZML document when no data available"""
        return [self._create_czml_document()]

    def get_cell_count_estimate(self, df: pd.DataFrame) -> int:
        """
        Estimate number of H3 cells for given flight data.

        Args:
            df: DataFrame with latitude, longitude columns

        Returns:
            Estimated cell count
        """
        if df.empty:
            return 0

        # Convert sample points to H3 cells
        sample_size = min(1000, len(df))
        sample = df.sample(n=sample_size) if len(df) > sample_size else df

        cells = set()
        for _, row in sample.iterrows():
            cell = h3.latlng_to_cell(row['latitude'], row['longitude'], self.resolution)
            cells.add(cell)

        # Extrapolate to full dataset
        estimated_count = int(len(cells) * (len(df) / sample_size))
        return estimated_count
