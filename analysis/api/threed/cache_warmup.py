"""
Cache Warmup Module
Pre-loads cell tower data for all completed sessions into Redis cache
"""
import threading
import time
import json
from pathlib import Path
import pandas as pd
import redis

from models.session import Session
from .opencellid_client import OpenCellIDClient


def warmup_cell_tower_cache(redis_client: redis.Redis, opencellid_client: OpenCellIDClient):
    """
    Pre-load cell tower data for all completed sessions into Redis cache

    This runs in background thread to not block Flask startup.
    Populates cache for instant subsequent requests (<100ms).

    Args:
        redis_client: Redis connection for caching
        opencellid_client: OpenCellID API client
    """
    if not redis_client or not opencellid_client:
        print("⚠️ Cache warmup skipped: Redis or OpenCellID not available")
        return

    def warmup_worker():
        """Background worker thread for cache warmup"""
        print("\n🔥 Starting cell tower cache warmup...")
        start_time = time.time()

        try:
            # Get all completed sessions
            sessions = Session.get_all()
            completed_sessions = [s for s in sessions if s.status == 'completed']

            if not completed_sessions:
                print("📭 No completed sessions found, warmup skipped")
                return

            print(f"📊 Found {len(completed_sessions)} completed sessions")

            radio_types = ['LTE']  # Default radio type
            success_count = 0
            skip_count = 0
            error_count = 0

            for idx, session in enumerate(completed_sessions, 1):
                session_id = session.id
                session_name = session.name or session_id[:8]

                print(f"\n  [{idx}/{len(completed_sessions)}] Processing {session_name}...")

                for radio in radio_types:
                    cache_key = f"cell_towers:{session_id}:{radio}"

                    # Check if already cached
                    try:
                        if redis_client.exists(cache_key):
                            print(f"    ✓ {radio} already cached, skipping")
                            skip_count += 1
                            continue
                    except Exception as e:
                        print(f"    ⚠️ Cache check error: {e}")

                    # Load session data
                    try:
                        results_dir = Path(__file__).parent.parent.parent / 'results' / session_id
                        merged_data_path = results_dir / 'merged_data.csv'

                        if not merged_data_path.exists():
                            print(f"    ⚠️ No merged_data.csv found")
                            error_count += 1
                            continue

                        # Read CSV to get bounding box and connected LACs
                        df = pd.read_csv(merged_data_path, low_memory=False)

                        if df.empty:
                            print(f"    ⚠️ Empty flight data")
                            error_count += 1
                            continue

                        # Calculate bounding box with margin
                        MARGIN = 0.05  # ~5km margin
                        min_lat = float(df['latitude'].min() - MARGIN)
                        max_lat = float(df['latitude'].max() + MARGIN)
                        min_lon = float(df['longitude'].min() - MARGIN)
                        max_lon = float(df['longitude'].max() + MARGIN)

                        # Extract connected LACs (Location Area Code)
                        connected_lacs = set()
                        if 'lte_lac' in df.columns:
                            lac_values = df['lte_lac'].dropna().astype(str).unique()
                            for lac_hex in lac_values:
                                try:
                                    if lac_hex not in ['0', 'FFFF', 'nan']:
                                        lac_decimal = int(lac_hex, 16)
                                        connected_lacs.add(lac_decimal)
                                except ValueError:
                                    continue

                        # Query OpenCellID using grid search
                        towers = opencellid_client.get_cell_towers_grid_search(
                            min_lat, max_lat, min_lon, max_lon, radio,
                            grid_size=0.045  # ~5km grid cells, max 25 grids
                        )

                        # Convert to GeoJSON
                        geojson = _convert_towers_to_geojson(towers, connected_lacs)

                        # Cache result (24 hours)
                        redis_client.setex(cache_key, 86400, json.dumps(geojson))

                        print(f"    ✅ {radio} cached: {len(towers)} towers")
                        success_count += 1

                        # Rate limiting to avoid overwhelming OpenCellID API
                        time.sleep(0.5)

                    except Exception as e:
                        print(f"    ❌ Error: {e}")
                        error_count += 1
                        continue

            elapsed = time.time() - start_time
            print(f"\n🎉 Cache warmup complete in {elapsed:.1f}s")
            print(f"   ✅ Success: {success_count}")
            print(f"   ⏭️  Skipped: {skip_count}")
            print(f"   ❌ Errors: {error_count}")

        except Exception as e:
            print(f"\n❌ Cache warmup failed: {e}")
            import traceback
            traceback.print_exc()

    # Start background thread
    thread = threading.Thread(target=warmup_worker, daemon=True)
    thread.start()
    print("🚀 Cache warmup started in background thread")


def _convert_towers_to_geojson(towers: list, connected_lacs: set = None) -> dict:
    """
    Convert OpenCellID tower list to GeoJSON FeatureCollection

    Args:
        towers: List of tower dicts from OpenCellID
        connected_lacs: Set of LAC values that were connected during flight

    Returns:
        GeoJSON FeatureCollection
    """
    if connected_lacs is None:
        connected_lacs = set()

    # Operator mapping (MCC 450 = Korea)
    OPERATORS = {
        5: 'SK Telecom',
        6: 'LG U+',
        8: 'KT'
    }

    features = []

    for tower in towers:
        # Skip towers without coordinates
        if not tower.get('lat') or not tower.get('lon'):
            continue

        # Check if this tower's LAC was connected during flight
        tower_lac = tower.get('lac')
        is_connected = tower_lac in connected_lacs

        # Create feature
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [tower['lon'], tower['lat']]
            },
            'properties': {
                'id': f"{tower.get('mcc', 0)}-{tower.get('mnc', 0)}-{tower.get('lac', 0)}-{tower.get('cellid', 0)}",
                'operator': OPERATORS.get(tower.get('mnc'), f"MNC {tower.get('mnc')}"),
                'radio': tower.get('radio', 'Unknown'),
                'mcc': tower.get('mcc'),
                'mnc': tower.get('mnc'),
                'lac': tower.get('lac'),
                'cellid': tower.get('cellid'),
                'range': tower.get('range', 0),
                'samples': tower.get('samples', 0),
                'is_connected': is_connected  # Mark if connected during flight
            }
        }
        features.append(feature)

    return {
        'type': 'FeatureCollection',
        'features': features
    }
