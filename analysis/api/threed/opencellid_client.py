"""
OpenCellID API Client
"""
import requests
from typing import List, Dict, Optional
import os

class OpenCellIDClient:
    """OpenCellID API wrapper"""

    BASE_URL = "https://www.opencellid.org/cell/getInArea"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenCellID client

        Args:
            api_key: OpenCellID API key (or use OPENCELLID_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENCELLID_API_KEY')
        if not self.api_key:
            raise ValueError("OpenCellID API key required")

    def get_cell_towers_in_bounding_box(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        radio: str = 'LTE',
        limit: int = 1000
    ) -> List[Dict]:
        """
        Get cell towers within a bounding box

        OpenCellID API Limitation: BBOX max size is 4,000,000 sq.mts (4 km²)
        This method queries center of bbox with max allowed area.

        Args:
            min_lat: Minimum latitude
            max_lat: Maximum latitude
            min_lon: Minimum longitude
            max_lon: Maximum longitude
            radio: Radio type filter (LTE, UMTS, GSM, NR)
            limit: Max number of results (default 1000)

        Returns:
            List of cell tower dicts
        """
        # Calculate center point
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        # OpenCellID BBOX limit: 4,000,000 sq.mts = 4 km²
        # Use 1km × 1km box around center (safe margin with cos correction)
        # 1 degree latitude ≈ 111 km, so 1km ≈ 0.009 degrees
        # Longitude: same 0.009 degrees (actual distance = 0.009 * 111 * cos(lat) km)
        import math
        lat_offset = 0.009  # ~1km radius (2km total height)
        lon_offset = 0.009  # ~1km radius at equator, less at higher latitudes

        # Create limited BBOX around center
        bbox_min_lat = center_lat - lat_offset
        bbox_max_lat = center_lat + lat_offset
        bbox_min_lon = center_lon - lon_offset
        bbox_max_lon = center_lon + lon_offset

        bbox = f"{bbox_min_lat},{bbox_min_lon},{bbox_max_lat},{bbox_max_lon}"

        params = {
            'key': self.api_key,
            'BBOX': bbox,
            'format': 'json',
            'limit': limit
        }

        if radio and radio.upper() != 'ALL':
            params['radio'] = radio.upper()

        print(f"  🔍 Query center: ({center_lat:.4f}, {center_lon:.4f})", flush=True)
        print(f"  📦 Limited BBOX: {bbox} (~4 km²)", flush=True)

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            # Check if response has error
            if 'error' in data:
                print(f"  ❌ OpenCellID API error: {data.get('error')} (code: {data.get('code')})")
                return []

            towers = data.get('cells', [])
            print(f"  📡 API response: {len(towers)} towers", flush=True)

            return towers

        except requests.exceptions.RequestException as e:
            print(f"❌ OpenCellID API request error: {e}", flush=True)
            return []
        except Exception as e:
            print(f"❌ OpenCellID API unexpected error: {e}", flush=True)
            return []

    def get_cell_towers_grid_search(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        radio: str = 'LTE',
        grid_size: float = 0.018,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Get cell towers using grid search to cover larger areas

        Divides the bounding box into overlapping grids and queries each grid.
        Removes duplicate towers based on cell ID.

        Args:
            min_lat: Minimum latitude
            max_lat: Maximum latitude
            min_lon: Minimum longitude
            max_lon: Maximum longitude
            radio: Radio type filter (LTE, UMTS, GSM, NR)
            grid_size: Grid cell size in degrees (default 0.018° ≈ 2km)
            limit: Max number of results per grid (default 1000)

        Returns:
            List of unique cell tower dicts
        """
        import math
        import time

        print(f"\n🔍 Grid search starting...", flush=True)
        print(f"  📐 Area: ({min_lat:.4f}, {min_lon:.4f}) to ({max_lat:.4f}, {max_lon:.4f})", flush=True)

        # Calculate grid dimensions
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon

        # Number of grids (with 50% overlap for better coverage)
        lat_grids = max(1, int(math.ceil(lat_range / (grid_size * 0.5))))
        lon_grids = max(1, int(math.ceil(lon_range / (grid_size * 0.5))))

        print(f"  📊 Grid configuration: {lat_grids} × {lon_grids} = {lat_grids * lon_grids} grids", flush=True)

        all_towers = []
        successful_queries = 0

        # Iterate through grid cells
        for i in range(lat_grids):
            for j in range(lon_grids):
                # Calculate grid boundaries
                grid_min_lat = min_lat + i * grid_size * 0.5
                grid_max_lat = min(grid_min_lat + grid_size, max_lat)
                grid_min_lon = min_lon + j * grid_size * 0.5
                grid_max_lon = min(grid_min_lon + grid_size, max_lon)

                # Skip if grid is too small
                if grid_max_lat - grid_min_lat < 0.001 or grid_max_lon - grid_min_lon < 0.001:
                    continue

                print(f"  🔎 Grid [{i},{j}]: ({grid_min_lat:.4f}, {grid_min_lon:.4f}) to ({grid_max_lat:.4f}, {grid_max_lon:.4f})", flush=True)

                # Query this grid
                towers = self.get_cell_towers_in_bounding_box(
                    min_lat=grid_min_lat,
                    max_lat=grid_max_lat,
                    min_lon=grid_min_lon,
                    max_lon=grid_max_lon,
                    radio=radio,
                    limit=limit
                )

                if towers:
                    all_towers.extend(towers)
                    successful_queries += 1

                # Rate limiting (5 requests per second max)
                time.sleep(0.2)

        # Remove duplicates based on cell ID
        unique_towers = {}
        for tower in all_towers:
            # Create unique key from cell identifiers
            key = f"{tower.get('mcc', 0)}-{tower.get('mnc', 0)}-{tower.get('lac', 0)}-{tower.get('cellid', 0)}"

            # Keep first occurrence of each tower
            if key not in unique_towers:
                unique_towers[key] = tower

        unique_list = list(unique_towers.values())

        print(f"\n📊 Grid search results:", flush=True)
        print(f"  ✅ Successful queries: {successful_queries}/{lat_grids * lon_grids}", flush=True)
        print(f"  📡 Total towers found: {len(all_towers)}", flush=True)
        print(f"  🎯 Unique towers: {len(unique_list)}", flush=True)

        return unique_list
