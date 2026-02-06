"""
CZML Generator for Flight Data Visualization
Converts flight data from database to CZML format for Cesium.js
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
import numpy as np

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from flight_data_analyzer import FlightDataAnalyzer


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
        # Load flight data
        self.analyzer = FlightDataAnalyzer(self.session_id)
        self.analyzer.step_1_load_data()

        # Get merged data
        df = self.analyzer.merged_data

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

        # Flight path entity
        czml.append(self._create_flight_path_entity(df, color_by))

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

    def _create_flight_path_entity(self, df, color_by: str) -> dict:
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

        entity = {
            "id": f"flight_{self.session_id}",
            "name": f"Flight Path - Session {self.session_id}",
            "availability": f"{df.index.min().isoformat()}/{df.index.max().isoformat()}",
            "position": {
                "epoch": df.index.min().isoformat(),
                "cartographicDegrees": positions
            },
            "path": {
                "show": True,
                "width": 3,
                "material": path_material,
                "resolution": 60,
                "leadTime": 0,
                "trailTime": float('inf')
            },
            "billboard": {
                "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAA7AAAAOwBeShxvQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAALNSURBVFiF7ZdNaBNBGIafsUmb/GnSJv5UY0vFH6SNgohgD4Ig/giCBz0U9KAHPXgQD4IXD+rFg1dF8OAP6EkE0YP+QBURbEGlVW2tP1UrjdYkNm2SbprdzO7OTNx0N7tJuweVPiz7zXzzPjszu9/uqcQwDANpRLwFGRBkQJABQQYEGRBkQJABQQYE/T8DbEsxf+Nz9A9HIJarJCpbRbvDO1AonT1+LoMZMQd/lJgYHMDIwDDMpnKT8W3b0djYiKYqL7w+H7Ze/oL8nL+NdQbmRkfR3X4R86Pj4Ps4OwtaOzvQ2HEVkb4QWHEaZsVpyBlHwQ7E8b3lBEIDz0yjLDUQHRxB14VziA6OmIxbg+r5p6HqBqg1HsCXr2aQYYiJr+cR/RlD1KT0LdB78Hpke/soNMMAJPKQ//MjUFd+DM21btPGPgKansc0PQu2fS/krBrIBxdCrXXpOV/OMWZwlDGQ/9jnwSuv/PU+ugDaU4D8Pc7fBlLpHOB0gJWXN02JqOvVE/9YgPwLFIUVeVg5BdqfSJq8xkBkL+TSakiF5VoRzkyCri5cZfx/U6AH8hYb8JQWJe1rDKhuJ5SiAvC/Jic/FwNbWQytt8E07dsFqG4XZKYIvKzqgQIr4cuMzTGqFw4opVzKxBnQtSJS4QL4MqPRfEpvIKW3ByQsUzY0I2XL+FofwPUc5IJKJwFwdPwHmJIimNISU7nNTUH1HjQJWKGJATGDT/S1o2ck5WeCeB87bsIjz6K37zHG3rfj5VsJY32deNLRjmdP2vB+pBcvevvw+0cndpaVIDtLBUGpkCvL4KreCcyNQ60sgfMXQuS4BCfh0K8IpPJyiEeLIe4pAOFcr7hX/FsqJm+LbuDyjGgqPRXQ5D+xsK1VmE+lCMABIPoegXo18Hja/Q/WgCADggwIMiDIgCADggwIMiD4HwvMAb/g3BLyvwqYAAAAAElFTkSuQmCC",
                "scale": 0.3,
                "eyeOffset": {
                    "cartesian": [0, 0, 0]
                }
            }
        }

        return entity

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
            # Time offset in seconds
            time_offset = (timestamp - start_time).total_seconds()

            # Position: longitude, latitude, altitude (in meters)
            lon = row['longitude']
            lat = row['latitude']
            alt = row['altitude']  # Already in meters

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
