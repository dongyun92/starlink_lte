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

    # Domain-specific value ranges for normalization
    DOMAIN_RANGES = {
        'lte_rsrp': (-140, -40),      # dBm (higher = better)
        'lte_rssi': (-120, -20),      # dBm (higher = better)
        'lte_sinr': (-20, 30),        # dB (higher = better)
        'lte_rsrq': (-20, -3),        # dB (higher = better)
        'starlink_snr': (0, 15),      # dB (higher = better)
        'starlink_latency': (200, 0), # ms (lower = better, INVERTED!)
        'altitude': None,             # Use actual min/max
        'speed': None,                # Use actual min/max
    }

    def __init__(self, resolution: int = 8):
        """
        Initialize hexagonal heatmap generator.

        Args:
            resolution: H3 resolution level (7-10). Default 8 (461m edge).
        """
        if not 7 <= resolution <= 10:
            raise ValueError("Resolution must be between 7 and 10")
        self.resolution = resolution

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

        # Get quality column
        quality_col = self._get_quality_column(mode)
        if quality_col not in df.columns:
            raise ValueError(f"Column '{quality_col}' not found in DataFrame")

        # Filter out NaN values
        df_clean = df[['latitude', 'longitude', quality_col]].dropna()
        if df_clean.empty:
            return self._create_empty_czml()

        # Step 1: Convert GPS coordinates to H3 cells
        df_clean = df_clean.copy()
        df_clean['h3_cell'] = df_clean.apply(
            lambda row: h3.latlng_to_cell(row['latitude'], row['longitude'], self.resolution),
            axis=1
        )

        # Step 2: Aggregate quality metrics per H3 cell
        agg_func = self._get_aggregation_function(aggregation)
        grouped = df_clean.groupby('h3_cell')[quality_col].agg(agg_func).reset_index()
        grouped.columns = ['h3_cell', 'quality_value']

        # Step 3: Normalize quality values (0-1)
        normalized_values = self._normalize_values(grouped['quality_value'], mode)
        grouped['normalized'] = normalized_values

        # Step 4: Generate CZML polygons
        czml_packets = [self._create_czml_document()]

        for _, row in grouped.iterrows():
            h3_cell = row['h3_cell']
            quality = row['quality_value']
            normalized = row['normalized']

            # Get hexagon boundary coordinates
            boundary = h3.cell_to_boundary(h3_cell)

            # Convert to lon, lat order (GeoJSON/CZML format)
            polygon_coords = [[lon, lat] for lat, lon in boundary]
            polygon_coords.append(polygon_coords[0])  # Close polygon

            # Get color from Jet colormap
            color = self._get_jet_color(normalized)

            # Calculate extrusion height (proportional to quality)
            height = normalized * extrusion_height

            # Create CZML polygon packet
            czml_packet = self._create_polygon_packet(
                h3_cell=h3_cell,
                polygon_coords=polygon_coords,
                color=color,
                height=height,
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

        Args:
            values: Series of quality values
            mode: Quality metric name

        Returns:
            Normalized values (0-1)
        """
        if mode in self.DOMAIN_RANGES and self.DOMAIN_RANGES[mode] is not None:
            vmin, vmax = self.DOMAIN_RANGES[mode]
        else:
            # Use actual min/max for altitude, speed
            vmin, vmax = values.min(), values.max()

        # Normalize to 0-1
        normalized = (values - vmin) / (vmax - vmin)
        normalized = np.clip(normalized, 0, 1)

        return normalized.values

    def _get_jet_color(self, normalized_value: float) -> Tuple[int, int, int, int]:
        """
        Get RGBA color from Jet colormap for normalized value (0-1).

        Args:
            normalized_value: Value between 0 and 1

        Returns:
            RGBA tuple (R, G, B, A) where each is 0-255
        """
        # Clamp value to [0, 1]
        value = np.clip(normalized_value, 0, 1)

        # Find two closest control points
        for i in range(len(self.JET_COLORMAP) - 1):
            cp1 = self.JET_COLORMAP[i]
            cp2 = self.JET_COLORMAP[i + 1]

            if cp1.value <= value <= cp2.value:
                # Linear interpolation between two control points
                t = (value - cp1.value) / (cp2.value - cp1.value)

                r = int(cp1.rgb[0] + t * (cp2.rgb[0] - cp1.rgb[0]))
                g = int(cp1.rgb[1] + t * (cp2.rgb[1] - cp1.rgb[1]))
                b = int(cp1.rgb[2] + t * (cp2.rgb[2] - cp1.rgb[2]))

                return (r, g, b, 200)  # 200 = 78% opacity

        # Fallback (shouldn't happen with proper clamping)
        return (255, 0, 0, 200)  # Red

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

    def _create_polygon_packet(
        self,
        h3_cell: str,
        polygon_coords: List[List[float]],
        color: Tuple[int, int, int, int],
        height: float,
        quality_value: float
    ) -> Dict:
        """
        Create CZML polygon packet for a single H3 cell.

        Args:
            h3_cell: H3 cell ID
            polygon_coords: List of [lon, lat] coordinates
            color: RGBA color tuple (R, G, B, A)
            height: Extrusion height in meters
            quality_value: Original quality metric value

        Returns:
            CZML polygon packet
        """
        # Flatten coordinates for CZML format
        flat_coords = []
        for lon, lat in polygon_coords:
            flat_coords.extend([lon, lat, 0])  # Ground level

        return {
            "id": f"hexagon_{h3_cell}",
            "name": f"H3 Cell {h3_cell}",
            "description": f"Quality: {quality_value:.2f}",
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
                    "rgba": [255, 255, 255, 100]  # White outline with 40% opacity
                },
                "outlineWidth": 1.0,
                "extrudedHeight": height,
                "perPositionHeight": False,
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
