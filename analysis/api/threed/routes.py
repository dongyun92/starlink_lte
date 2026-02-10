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
        - style: Visualization style ('point' or 'voxel') (default: 'point')
        - flight_id: Optional flight ID to filter by (for multi-flight sessions)

    Returns:
        CZML JSON data with heatmap entities
    """
    try:
        # Get query parameters
        mode = request.args.get('mode', 'lte', type=str)
        style = request.args.get('style', 'point', type=str)
        flight_id = request.args.get('flight_id', None, type=int)

        # Validate mode
        if mode not in ['lte', 'starlink', 'combined']:
            return jsonify({'error': 'Invalid mode. Must be lte, starlink, or combined'}), 400

        # Validate style
        if style not in ['point', 'voxel']:
            return jsonify({'error': 'Invalid style. Must be point or voxel'}), 400

        # Create cache key
        cache_key = f"heatmap:{session_id}:{mode}:{style}:{flight_id}"

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
        generator = CZMLGenerator(session_id)
        czml_data = generator.create_heatmap_czml(mode=mode, style=style, flight_id=flight_id)
        generation_time = (time.time() - start_time) * 1000  # Convert to ms
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

        # Calculate tower positions from GPS data
        tower_features = []
        unique_cells = df_lte['lte_cell_id'].unique()

        for cell_id in unique_cells:
            # Skip invalid cell IDs
            if cell_id in ['0', 'FFFFFFFF', 'nan'] or pd.isna(cell_id):
                continue

            # Get all positions where drone was connected to this cell
            cell_data = df_lte[df_lte['lte_cell_id'] == cell_id]

            # Use median position (more robust than mean)
            tower_lat = float(cell_data['latitude'].median())
            tower_lon = float(cell_data['longitude'].median())

            # Get signal statistics
            avg_rsrp = float(cell_data['lte_rsrp'].mean()) if 'lte_rsrp' in cell_data.columns else -100
            connection_count = len(cell_data)

            # Create GeoJSON feature
            tower_features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [tower_lon, tower_lat, 50]  # lon, lat, altitude
                },
                'properties': {
                    'cell_id': str(cell_id),
                    'connection_count': connection_count,
                    'avg_rsrp': avg_rsrp,
                    'radio': 'LTE',
                    'connected': True  # All towers are connected (we computed from actual connections)
                }
            })

            print(f"  📍 Cell {cell_id}: ({tower_lat:.6f}, {tower_lon:.6f}) - {connection_count} connections, RSRP={avg_rsrp:.1f}dBm")

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
        - arrow_length: Arrow length in meters (default: 1000)
        - flight_id: Optional flight ID to filter by (for multi-flight sessions)

    Returns:
        CZML JSON data with satellite direction polyline arrows
    """
    try:
        # Get query parameters
        sample_rate = request.args.get('sample_rate', 0.2, type=float)
        color_by = request.args.get('color_by', 'starlink_snr', type=str)
        arrow_length = request.args.get('arrow_length', 1000, type=int)
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
