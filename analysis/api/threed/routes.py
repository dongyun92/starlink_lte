"""
3D Visualization API Routes
Endpoints for CZML data and flight visualization
"""

from flask import Blueprint, jsonify, request, make_response
from pathlib import Path
import sys
import redis
import json
import hashlib
import time

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.session import Session
from .czml_generator import CZMLGenerator
from .opencellid_client import OpenCellIDClient
from .hexagonal_heatmap import HexagonalHeatmapGenerator

api_3d_bp = Blueprint('api_3d', __name__, url_prefix='/api/3d')

# Redis client for caching
try:
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=False  # We'll handle JSON encoding/decoding ourselves
    )
    redis_client.ping()
    print("✅ Redis connected for 3D API caching")
except Exception as e:
    print(f"⚠️ Redis connection failed: {e}")
    redis_client = None

# OpenCellID client (singleton)
opencellid_client = None

def get_opencellid_client():
    """Get or create OpenCellID client"""
    global opencellid_client
    if opencellid_client is None:
        try:
            opencellid_client = OpenCellIDClient()
        except ValueError as e:
            print(f"⚠️ OpenCellID client not available: {e}")
            return None
    return opencellid_client


@api_3d_bp.route('/flights', methods=['GET'])
def list_flights():
    """
    Get list of all flight sessions

    Returns:
        JSON array of flight sessions with metadata
    """
    try:
        sessions = Session.get_all()

        flights = []
        for session in sessions:
            if session.status == 'completed':
                # created_at is already a string from database
                created_at = session.created_at if isinstance(session.created_at, str) else session.created_at.isoformat()

                # Count actual files from filesystem
                session_path = Path(__file__).parent.parent.parent / 'uploads' / session.id
                flight_logs_count = len(list((session_path / 'flight_logs').glob('*.ulg'))) if (session_path / 'flight_logs').exists() else 0
                lte_data_count = len(list((session_path / 'lte_data').glob('*.csv'))) if (session_path / 'lte_data').exists() else 0
                starlink_data_count = len(list((session_path / 'starlink_data').glob('*.csv'))) if (session_path / 'starlink_data').exists() else 0

                flights.append({
                    'id': session.id,
                    'name': session.name or f"Flight {session.id}",
                    'created_at': created_at,
                    'file_count': {
                        'flight_logs': flight_logs_count,
                        'lte_data': lte_data_count,
                        'starlink_data': starlink_data_count
                    }
                })

        return jsonify(flights), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_3d_bp.route('/flights/<session_id>', methods=['GET'])
def get_flight_metadata(session_id):
    """
    Get metadata for a specific flight session

    Args:
        session_id: Session identifier

    Returns:
        JSON object with flight metadata
    """
    try:
        session = Session.get_by_id(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session.status != 'completed':
            return jsonify({'error': 'Session not completed'}), 400

        created_at = session.created_at if isinstance(session.created_at, str) else session.created_at.isoformat()

        metadata = {
            'id': session.id,
            'name': session.name or f"Flight {session.id}",
            'created_at': created_at,
            'status': session.status,
            'files': {
                'flight_logs': session.metadata.get('flight_log_count', 0),
                'lte_data': session.metadata.get('lte_data_count', 0),
                'starlink_data': session.metadata.get('starlink_data_count', 0)
            }
        }

        return jsonify(metadata), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_3d_bp.route('/flights/<session_id>/scenarios', methods=['GET'])
def get_flight_scenarios(session_id):
    """
    Get list of available flight scenarios (individual flights) within a session

    Args:
        session_id: Session identifier

    Returns:
        JSON array of flight scenarios with metadata
    """
    try:
        import pandas as pd

        session = Session.get_by_id(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session.status != 'completed':
            return jsonify({'error': 'Session not completed'}), 400

        # Read merged data to extract flight information
        results_dir = Path(__file__).parent.parent.parent / 'results' / session_id
        merged_data_path = results_dir / 'merged_data.csv'

        if not merged_data_path.exists():
            return jsonify({'error': 'No merged data found for session'}), 404

        # Read CSV and extract unique flights
        df = pd.read_csv(merged_data_path)

        if 'flight_id' not in df.columns or 'flight_name' not in df.columns:
            return jsonify({'error': 'Flight information not available'}), 400

        # Group by flight to get metadata
        scenarios = []
        for flight_id, group in df.groupby('flight_id'):
            flight_name = group['flight_name'].iloc[0]

            # Extract scenario name from filename (e.g., "1_RTL__20260123_1600" -> "RTL")
            scenario_name = "Unknown"
            if '_' in flight_name:
                parts = flight_name.split('_')
                if len(parts) >= 2 and parts[1]:
                    scenario_name = parts[1]
                elif len(parts) >= 3 and parts[2]:
                    scenario_name = parts[2].split('__')[0] if '__' in parts[2] else parts[2]

            scenarios.append({
                'flight_id': int(flight_id),
                'flight_name': flight_name,
                'scenario_name': scenario_name,
                'data_points': len(group),
                'time_range': {
                    'start': str(group['timestamp'].min()),
                    'end': str(group['timestamp'].max())
                },
                'coordinates': {
                    'lat_min': float(group['latitude'].min()),
                    'lat_max': float(group['latitude'].max()),
                    'lon_min': float(group['longitude'].min()),
                    'lon_max': float(group['longitude'].max()),
                    'alt_min': float(group['altitude'].min()),
                    'alt_max': float(group['altitude'].max())
                }
            })

        # Sort by flight_id
        scenarios.sort(key=lambda x: x['flight_id'])

        return jsonify(scenarios), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_3d_bp.route('/czml/<session_id>', methods=['GET'])
def get_czml_data(session_id):
    """
    Generate and return CZML data for a flight session

    Args:
        session_id: Session identifier

    Query Parameters:
        - sample_rate: Sampling rate in Hz (default: 1)
        - color_by: What to color by ('altitude', 'speed', 'quality') (default: 'altitude')
        - flight_id: Optional flight ID to filter by (for multi-flight sessions)
        - custom_metrics: Optional JSON string of custom metric weights
                         Example: {"rsrp": 0.3, "sinr": 0.5, "rsrq": 0.2}

    Returns:
        CZML JSON data
    """
    try:
        # Get query parameters
        sample_rate = request.args.get('sample_rate', 1.0, type=float)
        color_by = request.args.get('color_by', 'altitude', type=str)
        flight_id = request.args.get('flight_id', None, type=int)
        custom_metrics_str = request.args.get('custom_metrics', None, type=str)

        # Parse custom_metrics JSON if provided
        custom_metrics = None
        if custom_metrics_str:
            try:
                custom_metrics = json.loads(custom_metrics_str)
            except json.JSONDecodeError as e:
                return jsonify({'error': f'Invalid custom_metrics JSON: {str(e)}'}), 400

        # Create cache key (include custom_metrics hash for unique caching)
        custom_metrics_hash = hashlib.md5(custom_metrics_str.encode()).hexdigest()[:8] if custom_metrics_str else 'none'
        cache_key = f"czml:{session_id}:{sample_rate}:{color_by}:{flight_id}:{custom_metrics_hash}"

        # Try to get from cache
        if redis_client:
            try:
                cached_json = redis_client.get(cache_key)
                if cached_json:
                    print(f"✅ Cache HIT: {cache_key}")
                    # Return cached JSON directly
                    response = make_response(cached_json)
                    response.headers['Content-Type'] = 'application/json'
                    response.headers['X-Cache'] = 'HIT'
                    return response
            except Exception as e:
                print(f"⚠️ Cache read error: {e}")

        # Validate session
        session = Session.get_by_id(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session.status != 'completed':
            return jsonify({'error': 'Session not completed'}), 400

        # Generate CZML
        start_time = time.time()
        generator = CZMLGenerator(session_id)
        czml_data = generator.generate(
            sample_rate=sample_rate,
            color_by=color_by,
            flight_id=flight_id,
            custom_metrics=custom_metrics
        )
        generation_time = (time.time() - start_time) * 1000  # Convert to ms
        print(f"⏱️ CZML generation time: {generation_time:.1f}ms")

        # Convert to JSON
        czml_json = json.dumps(czml_data)

        # Cache the JSON data (5 minutes TTL)
        if redis_client:
            try:
                redis_client.setex(cache_key, 300, czml_json)
                print(f"💾 Cache MISS: {cache_key} saved ({len(czml_json)} bytes)")
            except Exception as e:
                print(f"⚠️ Cache write error: {e}")

        # Return JSON response
        response = make_response(czml_json)
        response.headers['Content-Type'] = 'application/json'
        response.headers['X-Cache'] = 'MISS'
        return response

    except ValueError as e:
        # Client error - invalid data selection (e.g., missing data for color_by)
        error_msg = str(e)
        print(f"⚠️ ValueError: {error_msg}")
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        # Server error
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_3d_bp.route('/heatmap/<session_id>', methods=['GET'])
def get_heatmap_czml(session_id):
    """
    Generate and return heatmap CZML data for data quality visualization

    Args:
        session_id: Session identifier

    Query Parameters:
        - mode: Heatmap mode ('lte', 'starlink', or 'combined') (default: 'lte')
        - style: Visualization style ('point', 'voxel', or 'hexagon') (default: 'point')
        - flight_id: Optional flight ID to filter by (for multi-flight sessions)
        - resolution: H3 resolution for hexagon style (7-10) (default: 8)
        - aggregation: Aggregation method for hexagon style ('mean', 'max', 'min', 'median') (default: 'mean')
        - extrusion_height: Maximum extrusion height in meters for hexagon style (default: 200)

    Returns:
        CZML JSON data with heatmap entities
    """
    try:
        # Get query parameters
        mode = request.args.get('mode', 'lte', type=str)
        style = request.args.get('style', 'point', type=str)
        flight_id = request.args.get('flight_id', None, type=int)
        resolution = request.args.get('resolution', 8, type=int)
        aggregation = request.args.get('aggregation', 'mean', type=str)
        extrusion_height = request.args.get('extrusion_height', 200.0, type=float)

        # Validate mode
        if mode not in ['lte', 'starlink', 'combined']:
            return jsonify({'error': 'Invalid mode. Must be lte, starlink, or combined'}), 400

        # Validate style
        if style not in ['point', 'voxel', 'hexagon']:
            return jsonify({'error': 'Invalid style. Must be point, voxel, or hexagon'}), 400

        # Validate hexagon-specific parameters
        if style == 'hexagon':
            if not 7 <= resolution <= 10:
                return jsonify({'error': 'Invalid resolution. Must be between 7 and 10'}), 400
            if aggregation not in ['mean', 'max', 'min', 'median']:
                return jsonify({'error': 'Invalid aggregation. Must be mean, max, min, or median'}), 400

        # Create cache key (include hexagon parameters)
        cache_key = f"heatmap:{session_id}:{mode}:{style}:{flight_id}:{resolution}:{aggregation}:{extrusion_height}"

        # Try to get from cache
        if redis_client:
            try:
                cached_json = redis_client.get(cache_key)
                if cached_json:
                    print(f"✅ Cache HIT: {cache_key}")
                    # Return cached JSON directly
                    response = make_response(cached_json)
                    response.headers['Content-Type'] = 'application/json'
                    response.headers['X-Cache'] = 'HIT'
                    return response
            except Exception as e:
                print(f"⚠️ Cache read error: {e}")

        # Validate session
        session = Session.get_by_id(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session.status != 'completed':
            return jsonify({'error': 'Session not completed'}), 400

        # Generate heatmap CZML
        start_time = time.time()

        if style == 'hexagon':
            # Use HexagonalHeatmapGenerator for hexagon style
            import pandas as pd

            # Read merged data
            results_dir = Path(__file__).parent.parent.parent / 'results' / session_id
            merged_data_path = results_dir / 'merged_data.csv'

            if not merged_data_path.exists():
                return jsonify({'error': 'No flight data available'}), 404

            # Load data
            df = pd.read_csv(merged_data_path, low_memory=False)

            # Filter by flight_id if specified
            if flight_id is not None:
                if 'flight_id' not in df.columns:
                    return jsonify({'error': 'Flight ID filtering not available'}), 400
                df = df[df['flight_id'] == flight_id]

            # Map mode to quality metric
            mode_map = {
                'lte': 'lte_rsrp',
                'starlink': 'starlink_snr',
                'combined': 'lte_rsrp'  # Default to LTE for combined
            }
            quality_mode = mode_map.get(mode, 'lte_rsrp')

            # Generate hexagonal heatmap
            hex_generator = HexagonalHeatmapGenerator(resolution=resolution)
            czml_data = hex_generator.generate_czml(
                df=df,
                mode=quality_mode,
                aggregation=aggregation,
                extrusion_height=extrusion_height
            )

            generation_time = (time.time() - start_time) * 1000
            cell_count = len(czml_data) - 1  # Exclude document header
            print(f"⏱️ Hexagonal heatmap generation time: {generation_time:.1f}ms")
            print(f"   Resolution: {resolution}, Cells: {cell_count}, Mode: {quality_mode}, Aggregation: {aggregation}")
        else:
            # Use existing CZMLGenerator for point/voxel styles
            generator = CZMLGenerator(session_id)
            czml_data = generator.create_heatmap_czml(mode=mode, style=style, flight_id=flight_id)
            generation_time = (time.time() - start_time) * 1000
            print(f"⏱️ Heatmap generation time: {generation_time:.1f}ms (mode={mode}, style={style})")

        # Convert to JSON
        czml_json = json.dumps(czml_data)

        # Cache the JSON data (5 minutes TTL)
        if redis_client:
            try:
                redis_client.setex(cache_key, 300, czml_json)
                print(f"💾 Cache MISS: {cache_key} saved ({len(czml_json)} bytes)")
            except Exception as e:
                print(f"⚠️ Cache write error: {e}")

        # Return JSON response
        response = make_response(czml_json)
        response.headers['Content-Type'] = 'application/json'
        response.headers['X-Cache'] = 'MISS'
        return response

    except ValueError as e:
        # Client error - invalid data selection (e.g., missing data for color_by)
        error_msg = str(e)
        print(f"⚠️ ValueError: {error_msg}")
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        # Server error
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_3d_bp.route('/cell-towers/<session_id>', methods=['GET'])
def get_cell_towers(session_id):
    """
    Get cell tower data for visualization
    Computes tower locations from actual drone connection data (GPS-based)

    Query Parameters:
        - use_cache: Use cached data if available (true/false) [default: true]

    Response:
        GeoJSON FeatureCollection with cell tower locations
    """
    try:
        # Get query parameters
        use_cache = request.args.get('use_cache', 'true', type=str) == 'true'

        # Cache key
        cache_key = f"cell_towers_gps:{session_id}"

        # Check cache (24 hour TTL)
        if use_cache and redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    print(f"✅ Cell towers cache HIT: {cache_key}")
                    return jsonify(json.loads(cached)), 200
            except Exception as e:
                print(f"⚠️ Redis cache read error: {e}")

        # Load session data
        session = Session.get_by_id(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session.status != 'completed':
            return jsonify({'error': 'Session not completed'}), 400

        # Read merged data
        results_dir = Path(__file__).parent.parent.parent / 'results' / session_id
        merged_data_path = results_dir / 'merged_data.csv'

        if not merged_data_path.exists():
            return jsonify({'error': 'No flight data available'}), 404

        # Read CSV and compute tower positions
        import pandas as pd
        df = pd.read_csv(merged_data_path, low_memory=False)

        if df.empty:
            return jsonify({'error': 'No flight data available'}), 404

        # Filter LTE data
        if 'lte_cell_id' not in df.columns:
            return jsonify({'error': 'No LTE cell data available'}), 404

        df_lte = df[df['lte_cell_id'].notna()].copy()

        if df_lte.empty:
            return jsonify({'error': 'No LTE connection data available'}), 404

        print(f"📡 Computing tower positions from {len(df_lte)} LTE connection points...")

        # Load original LTE CSV for detailed cell information
        uploads_dir = Path(__file__).parent.parent.parent / 'uploads' / session_id / 'lte_data'
        lte_csv_files = list(uploads_dir.glob('*.csv')) if uploads_dir.exists() else []

        # Operator mapping
        OPERATORS = {
            5: 'SK Telecom',
            6: 'LG U+',
            8: 'KT'
        }

        # Read original LTE data for cell details
        lte_details = {}
        if lte_csv_files:
            lte_original = pd.read_csv(lte_csv_files[0])
            for cell_id in lte_original['cell_id'].unique():
                if pd.isna(cell_id) or cell_id in ['0', 'FFFFFFFF']:
                    continue
                cell_rows = lte_original[lte_original['cell_id'] == cell_id]
                first_row = cell_rows.iloc[0]

                lte_details[cell_id] = {
                    'mcc': int(first_row['mcc']) if pd.notna(first_row.get('mcc')) else 450,
                    'mnc': int(first_row['mnc']) if pd.notna(first_row.get('mnc')) else None,
                    'lac': int(first_row['lac']) if pd.notna(first_row.get('lac')) else None,
                    'pcid': int(first_row['pcid']) if pd.notna(first_row.get('pcid')) else None,
                    'enodeb_id': int(first_row['enodeb_id']) if pd.notna(first_row.get('enodeb_id')) else None,
                    'cell_sector_id': int(first_row['cell_sector_id']) if pd.notna(first_row.get('cell_sector_id')) else None,
                }

        # Calculate tower positions from GPS data
        tower_features = []
        unique_cells = df_lte['lte_cell_id'].unique()

        for cell_id in unique_cells:
            # Skip invalid cell IDs
            if cell_id in ['0', 'FFFFFFFF', 'nan'] or pd.isna(cell_id):
                continue

            # Get all positions where drone was connected to this cell
            cell_data = df_lte[df_lte['lte_cell_id'] == cell_id]

            # Filter to strongest signal positions (top 20% RSRP)
            # Tower is closest where signal is strongest - avoids ocean/distant positions
            if 'lte_rsrp' in cell_data.columns and cell_data['lte_rsrp'].notna().sum() > 0:
                rsrp_threshold = cell_data['lte_rsrp'].quantile(0.80)  # Top 20% strongest signals
                cell_data_strong = cell_data[cell_data['lte_rsrp'] >= rsrp_threshold]

                # Use at least 3 points for stability
                if len(cell_data_strong) >= 3:
                    cell_data = cell_data_strong
                    print(f"    🎯 Cell {cell_id}: Using top 20% signal strength ({len(cell_data)} points, RSRP≥{rsrp_threshold:.1f}dBm)")

            # Use median position (more robust than mean)
            tower_lat = float(cell_data['latitude'].median())
            tower_lon = float(cell_data['longitude'].median())

            # Get signal statistics (from original data, not filtered)
            all_cell_data = df_lte[df_lte['lte_cell_id'] == cell_id]
            avg_rsrp = float(all_cell_data['lte_rsrp'].mean()) if 'lte_rsrp' in all_cell_data.columns else -100
            connection_count = len(all_cell_data)

            # Get detailed cell information from original LTE data
            details = lte_details.get(cell_id, {})
            mcc = details.get('mcc', 450)
            mnc = details.get('mnc')
            lac = details.get('lac')
            pcid = details.get('pcid')
            enodeb_id = details.get('enodeb_id')
            sector_id = details.get('cell_sector_id')

            # Generate meaningful name
            operator_name = OPERATORS.get(mnc, 'Unknown') if mnc else 'GPS Computed'
            if enodeb_id and sector_id is not None:
                tower_name = f"{operator_name} - eNB {enodeb_id} - Sector {sector_id}"
            else:
                tower_name = f"{operator_name} - Cell {cell_id}"

            # Create GeoJSON feature with complete LTE information
            tower_features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [tower_lon, tower_lat, 50]  # lon, lat, altitude
                },
                'properties': {
                    'id': f"GPS-{mcc}-{mnc}-{lac}-{cell_id}",  # Unique ID
                    'name': tower_name,  # Human-readable name
                    'radio': 'LTE',
                    'operator': operator_name,
                    'mcc': mcc,  # Mobile Country Code
                    'mnc': mnc,  # Mobile Network Code
                    'lac': lac,  # Location Area Code
                    'cid': str(cell_id),  # Cell ID (hex)
                    'pcid': pcid,  # Physical Cell ID
                    'enodeb_id': enodeb_id,  # eNodeB ID (base station)
                    'sector_id': sector_id,  # Sector ID (antenna direction)
                    'connection_count': connection_count,  # Number of connections
                    'avg_rsrp': avg_rsrp,  # Average signal strength
                    'position_method': 'GPS-based (Top 20% signal)',  # How position was computed
                    'connected': True  # This tower was connected during flight
                }
            })

            # Print detailed tower info
            info_parts = [f"Cell {cell_id}"]
            if enodeb_id:
                info_parts.append(f"eNB {enodeb_id}")
            if sector_id is not None:
                info_parts.append(f"Sector {sector_id}")
            if pcid:
                info_parts.append(f"PCID {pcid}")

            print(f"  📍 {' | '.join(info_parts)}")
            print(f"      Position: ({tower_lat:.6f}, {tower_lon:.6f})")
            print(f"      Operator: {operator_name} (MCC:{mcc}, MNC:{mnc}, LAC:{lac})")
            print(f"      Stats: {connection_count} connections, Avg RSRP={avg_rsrp:.1f}dBm")

        # Create GeoJSON FeatureCollection
        geojson = {
            'type': 'FeatureCollection',
            'features': tower_features
        }

        print(f"✅ Computed {len(tower_features)} tower positions from GPS data")

        # Cache result (24 hours)
        if redis_client:
            try:
                redis_client.setex(cache_key, 86400, json.dumps(geojson))
                print(f"💾 Cell towers cached: {cache_key}")
            except Exception as e:
                print(f"⚠️ Redis cache write error: {e}")

        return jsonify(geojson), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to fetch cell towers: {str(e)}'}), 500


def _convert_towers_to_geojson(towers: list, connected_lacs: set = None) -> dict:
    """
    Convert OpenCellID tower list to GeoJSON FeatureCollection

    Args:
        towers: List of tower dicts from OpenCellID
        connected_lacs: Set of LAC (Location Area Code) values that were connected during flight

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
                'coordinates': [
                    float(tower['lon']),
                    float(tower['lat']),
                    0  # Ground level
                ]
            },
            'properties': {
                'id': f"{tower.get('mcc', 'unknown')}-{tower.get('mnc', 'unknown')}-{tower.get('lac', 'unknown')}-{tower.get('cid', 'unknown')}",
                'radio': tower.get('radio', 'unknown'),
                'operator': OPERATORS.get(tower.get('mnc'), 'Unknown'),
                'mcc': tower.get('mcc'),
                'mnc': tower.get('mnc'),
                'lac': tower.get('lac'),
                'cid': tower.get('cid'),
                'range': tower.get('range', 1000),  # Default 1km
                'samples': tower.get('samples', 0),
                'signal': tower.get('averageSignal'),
                'updated': tower.get('updated'),
                'is_connected': is_connected  # Flag for towers used during flight
            }
        }

        features.append(feature)

    return {
        'type': 'FeatureCollection',
        'features': features
    }


@api_3d_bp.route('/satellite-direction/<session_id>', methods=['GET'])
def get_satellite_direction_czml(session_id):
    """
    Generate and return CZML data for satellite direction arrows

    Args:
        session_id: Session identifier

    Query Parameters:
        - sample_rate: Sampling rate in Hz (default: 0.2)
        - color_by: What to color arrows by ('starlink_snr' or 'starlink_latency') (default: 'starlink_snr')
        - arrow_length: Arrow length in meters (default: 10)
        - flight_id: Optional flight ID to filter by (for multi-flight sessions)

    Returns:
        CZML JSON data with satellite direction polyline arrows
    """
    try:
        # Get query parameters
        sample_rate = request.args.get('sample_rate', 0.2, type=float)
        color_by = request.args.get('color_by', 'starlink_snr', type=str)
        arrow_length = request.args.get('arrow_length', 10, type=int)
        flight_id = request.args.get('flight_id', None, type=int)

        # Validate color_by
        if color_by not in ['starlink_snr', 'starlink_latency']:
            return jsonify({'error': 'Invalid color_by. Must be starlink_snr or starlink_latency'}), 400

        # Create cache key
        cache_key = f"sat_dir:{session_id}:{sample_rate}:{color_by}:{arrow_length}:{flight_id}"

        # Try to get from cache
        if redis_client:
            try:
                cached_json = redis_client.get(cache_key)
                if cached_json:
                    print(f"✅ Cache HIT: {cache_key}")
                    response = make_response(cached_json)
                    response.headers['Content-Type'] = 'application/json'
                    response.headers['X-Cache'] = 'HIT'
                    return response
            except Exception as e:
                print(f"⚠️ Cache read error: {e}")

        # Validate session
        session = Session.get_by_id(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session.status != 'completed':
            return jsonify({'error': 'Session not completed'}), 400

        # Generate satellite direction CZML
        start_time = time.time()
        generator = CZMLGenerator(session_id)
        czml_data = generator.generate_satellite_direction_arrows(
            sample_rate=sample_rate,
            color_by=color_by,
            flight_id=flight_id,
            arrow_length=arrow_length
        )
        generation_time = (time.time() - start_time) * 1000
        print(f"⏱️ Satellite direction CZML generation time: {generation_time:.1f}ms")

        # Convert to JSON
        czml_json = json.dumps(czml_data)

        # Cache the JSON data (5 minutes TTL)
        if redis_client:
            try:
                redis_client.setex(cache_key, 300, czml_json)
                print(f"💾 Cache MISS: {cache_key} saved ({len(czml_json)} bytes)")
            except Exception as e:
                print(f"⚠️ Cache write error: {e}")

        # Return JSON response
        response = make_response(czml_json)
        response.headers['Content-Type'] = 'application/json'
        response.headers['X-Cache'] = 'MISS'
        return response

    except ValueError as e:
        error_msg = str(e)
        print(f"⚠️ ValueError: {error_msg}")
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        print(f"❌ Error generating satellite direction CZML: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_3d_bp.route('/tower-connections/<session_id>', methods=['GET'])
def get_tower_connections_czml(session_id):
    """
    Generate and return CZML data for LTE tower connections

    Args:
        session_id: Session identifier

    Query Parameters:
        - sample_rate: Sampling rate in Hz (default: 0.2)
        - flight_id: Optional flight ID to filter by (for multi-flight sessions)

    Returns:
        CZML JSON data with time-dynamic tower connection polylines
    """
    try:
        # Get query parameters
        sample_rate = request.args.get('sample_rate', 0.2, type=float)
        flight_id = request.args.get('flight_id', None, type=int)

        # Create cache key
        cache_key = f"tower_conn:{session_id}:{sample_rate}:{flight_id}"

        # Try to get from cache
        if redis_client:
            try:
                cached_json = redis_client.get(cache_key)
                if cached_json:
                    print(f"✅ Cache HIT: {cache_key}")
                    response = make_response(cached_json)
                    response.headers['Content-Type'] = 'application/json'
                    response.headers['X-Cache'] = 'HIT'
                    return response
            except Exception as e:
                print(f"⚠️ Cache read error: {e}")

        # Validate session
        session = Session.get_by_id(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session.status != 'completed':
            return jsonify({'error': 'Session not completed'}), 400

        # Generate tower connections CZML
        start_time = time.time()
        generator = CZMLGenerator(session_id)
        czml_data = generator.generate_tower_connections(
            sample_rate=sample_rate,
            flight_id=flight_id
        )
        generation_time = (time.time() - start_time) * 1000
        print(f"⏱️ Tower connections CZML generation time: {generation_time:.1f}ms")

        # Convert to JSON
        czml_json = json.dumps(czml_data)

        # Cache the JSON data (5 minutes TTL)
        if redis_client:
            try:
                redis_client.setex(cache_key, 300, czml_json)
                print(f"💾 Cache MISS: {cache_key} saved ({len(czml_json)} bytes)")
            except Exception as e:
                print(f"⚠️ Cache write error: {e}")

        # Return JSON response
        response = make_response(czml_json)
        response.headers['Content-Type'] = 'application/json'
        response.headers['X-Cache'] = 'MISS'
        return response

    except ValueError as e:
        error_msg = str(e)
        print(f"⚠️ ValueError: {error_msg}")
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        print(f"❌ Error generating tower connections CZML: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_3d_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint

    Returns:
        JSON object with service status
    """
    return jsonify({
        'status': 'healthy',
        'service': '3D Visualization API',
        'version': '1.0.0'
    }), 200
