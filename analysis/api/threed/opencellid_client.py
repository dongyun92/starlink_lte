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
