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
from .tower_estimation import (
    estimate_tower_hybrid,
    estimate_tower_by_enodeb,
    compute_flight_boundary,
    filter_by_signal_quality,
    validate_tower_position
)
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
        - altitude_bin_size: Altitude bin size in meters for 3D voxel layers (default: 25)

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
        altitude_bin_size = request.args.get('altitude_bin_size', 25.0, type=float)

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
            if not 10 <= altitude_bin_size <= 100:
                return jsonify({'error': 'Invalid altitude_bin_size. Must be between 10 and 100'}), 400

        # Create cache key (include hexagon parameters)
        cache_key = f"heatmap:{session_id}:{mode}:{style}:{flight_id}:{resolution}:{aggregation}:{altitude_bin_size}"

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

            # Auto-detect available columns (consistent with CZMLGenerator)
            lte_column = None
            if 'lte_rsrp' in df.columns and not df['lte_rsrp'].isna().all():
                lte_column = 'lte_rsrp'
            elif 'lte_rssi' in df.columns and not df['lte_rssi'].isna().all():
                lte_column = 'lte_rssi'
            elif 'lte_sinr' in df.columns and not df['lte_sinr'].isna().all():
                lte_column = 'lte_sinr'

            starlink_column = None
            if 'starlink_snr' in df.columns and not df['starlink_snr'].isna().all():
                starlink_column = 'starlink_snr'
            elif 'starlink_latency' in df.columns and not df['starlink_latency'].isna().all():
                starlink_column = 'starlink_latency'

            # Map mode to actual column
            mode_map = {
                'lte': lte_column,
                'starlink': starlink_column,
                'combined': lte_column  # Default to LTE for combined
            }
            quality_mode = mode_map.get(mode)

            # Check if requested mode has data
            if quality_mode is None:
                # Return empty CZML if no data available
                return jsonify([{"id": "document", "version": "1.0", "name": f"Empty Heatmap - No {mode.upper()} data"}]), 200

            # Generate 3D hexagonal voxel grid
            hex_generator = HexagonalHeatmapGenerator(
                resolution=resolution,
                altitude_bin_size=altitude_bin_size
            )
            czml_data = hex_generator.generate_czml(
                df=df,
                mode=quality_mode,
                aggregation=aggregation,
                extrusion_height=0  # Not used in 3D voxel mode
            )

            generation_time = (time.time() - start_time) * 1000
            voxel_count = len(czml_data) - 1  # Exclude document header
            print(f"⏱️ 3D Hexagonal Voxel Grid generation time: {generation_time:.1f}ms")
            print(f"   Resolution: {resolution}, Voxels: {voxel_count}, Altitude Bins: {altitude_bin_size}m")
            print(f"   Mode: {quality_mode}, Aggregation: {aggregation}")
        else:
            # Use existing CZMLGenerator for point/voxel styles
            generator = CZMLGenerator(session_id)
            czml_data = generator.create_heatmap_czml(mode=mode, style=style, flight_id=flight_id, altitude_bin_size=altitude_bin_size)
            generation_time = (time.time() - start_time) * 1000
            print(f"⏱️ Heatmap generation time: {generation_time:.1f}ms (mode={mode}, style={style}, altitude_bin_size={altitude_bin_size}m)")

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


def get_cell_towers_geojson_internal(session_id: str, flight_id: int = None) -> dict:
    """
    Internal function to compute cell tower positions (for use by other modules)

    Args:
        session_id: Session identifier
        flight_id: Optional flight ID to filter by

    Returns:
        GeoJSON FeatureCollection dict (not a Flask response)
    """
    # Load session data
    session = Session.get_by_id(session_id)

    if not session or session.status != 'completed':
        return {'type': 'FeatureCollection', 'features': []}

    # Read merged data
    results_dir = Path(__file__).parent.parent.parent / 'results' / session_id
    merged_data_path = results_dir / 'merged_data.csv'

    if not merged_data_path.exists():
        return {'type': 'FeatureCollection', 'features': []}

    # Read CSV and compute tower positions
    import pandas as pd
    df = pd.read_csv(merged_data_path, low_memory=False)

    if df.empty:
        return {'type': 'FeatureCollection', 'features': []}

    # Filter by flight_id if specified
    if flight_id is not None and 'flight_id' in df.columns:
        df = df[df['flight_id'] == flight_id].copy()

    # Filter LTE data
    if 'lte_cell_id' not in df.columns:
        return {'type': 'FeatureCollection', 'features': []}

    df_lte = df[df['lte_cell_id'].notna()].copy()

    if df_lte.empty:
        return {'type': 'FeatureCollection', 'features': []}

    # Load original LTE CSV for detailed cell information
    uploads_dir = Path(__file__).parent.parent.parent / 'uploads' / session_id / 'lte_data'
    lte_csv_files = list(uploads_dir.glob('*.csv')) if uploads_dir.exists() else []

    # Operator mapping
    OPERATORS = {5: 'SK Telecom', 6: 'LG U+', 8: 'KT'}

    # Helper function to safely convert to int
    def safe_int(value):
        if pd.isna(value):
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            try:
                return int(str(value), 16)
            except (ValueError, TypeError):
                return None

    # Read original LTE data for cell details from ALL LTE CSV files
    lte_details = {}
    if lte_csv_files:
        print(f"\n🔍 Reading {len(lte_csv_files)} LTE CSV files for cell details...")

        for lte_file in lte_csv_files:
            # Force cell_id to be read as string to preserve hex values
            lte_original = pd.read_csv(lte_file, dtype={'cell_id': str})

            for cell_id in lte_original['cell_id'].unique():
                if pd.isna(cell_id) or cell_id in ['0', 'FFFFFFFF', 'nan']:
                    continue

                # Convert to uppercase for consistent matching
                cell_id_key = str(cell_id).upper()

                # Skip if already processed
                if cell_id_key in lte_details:
                    continue

                cell_rows = lte_original[lte_original['cell_id'] == cell_id]
                first_row = cell_rows.iloc[0]

                lte_details[cell_id_key] = {
                    'mcc': safe_int(first_row.get('mcc')) or 450,
                    'mnc': safe_int(first_row.get('mnc')),
                    'lac': safe_int(first_row.get('lac')),
                    'pcid': safe_int(first_row.get('pcid')),
                    'enodeb_id': safe_int(first_row.get('enodeb_id')),
                    'cell_sector_id': safe_int(first_row.get('cell_sector_id')),
                }

        print(f"✅ Built lte_details dictionary with {len(lte_details)} unique cell IDs")

    # ═══════════════════════════════════════════════════════════════
    # P1: eNodeB-Based Tower Position Estimation
    # ═══════════════════════════════════════════════════════════════
    # Physical Reality: Same eNodeB = Same physical tower location
    # Multiple sectors (0, 1, 2, ...) are directional antennas on the same tower
    # Combining all sector data dramatically improves estimation accuracy
    # ═══════════════════════════════════════════════════════════════

    tower_features = []
    unique_cells = df_lte['lte_cell_id'].unique()
    print(f"📡 Found {len(unique_cells)} unique cell IDs in merged data")

    # Step 1: Group cells by eNodeB ID (same physical tower)
    enodeb_groups = {}  # enodeb_id → { sector_id → cell_id }
    cells_without_enodeb = []

    for cell_id in unique_cells:
        if cell_id in ['0', 'FFFFFFFF', 'nan'] or pd.isna(cell_id):
            continue

        cell_id_key = str(cell_id).upper()
        details = lte_details.get(cell_id_key, {})
        enodeb_id = details.get('enodeb_id')
        sector_id = details.get('cell_sector_id')

        if enodeb_id is not None and sector_id is not None:
            # Group by eNodeB
            if enodeb_id not in enodeb_groups:
                enodeb_groups[enodeb_id] = {}
            enodeb_groups[enodeb_id][sector_id] = cell_id
        else:
            # No eNodeB info - process individually
            cells_without_enodeb.append(cell_id)

    print(f"  📊 eNodeB grouping: {len(enodeb_groups)} physical towers, {sum(len(s) for s in enodeb_groups.values())} total sectors")
    print(f"  ⚠️  {len(cells_without_enodeb)} cells without eNodeB info (will process individually)")

    # Compute flight path boundary for physical validation
    flight_boundary = compute_flight_boundary(df_lte, buffer_km=5.0)
    flight_center_lat = float(df_lte['latitude'].mean())
    flight_center_lon = float(df_lte['longitude'].mean())

    # Step 2: Estimate tower positions by eNodeB (combined sectors)
    for enodeb_id, sector_cells in enodeb_groups.items():
        # Get details from first sector (all sectors share same MCC, MNC, LAC)
        first_cell_id = list(sector_cells.values())[0]
        cell_id_key = str(first_cell_id).upper()
        details = lte_details.get(cell_id_key, {})

        # Estimate tower position using ALL sectors of this eNodeB
        estimation = estimate_tower_by_enodeb(df_lte, enodeb_id, sector_cells, verbose=True)

        if estimation is None:
            continue

        tower_lat = estimation['latitude']
        tower_lon = estimation['longitude']
        tower_alt = estimation.get('altitude', 30.0)
        uncertainty_m = estimation['uncertainty_m']
        position_method = estimation['position_method']

        # Physical validation
        is_valid, validation_reason = validate_tower_position(
            tower_lat, tower_lon, flight_boundary,
            flight_center_lat, flight_center_lon,
            max_distance_km=15.0
        )

        if not is_valid:
            print(f"  ❌ eNodeB {enodeb_id} rejected: {validation_reason}")
            continue

        # Get signal statistics (combined across all sectors)
        all_sector_data = []
        for cell_id in sector_cells.values():
            sector_data = df_lte[df_lte['lte_cell_id'] == cell_id]
            if len(sector_data) > 0:
                all_sector_data.append(sector_data)

        if len(all_sector_data) == 0:
            continue

        combined_data = pd.concat(all_sector_data, ignore_index=True)
        avg_rsrp = float(combined_data['lte_rsrp'].mean()) if 'lte_rsrp' in combined_data.columns else -100
        connection_count = len(combined_data)

        # Get cell information
        mcc = details.get('mcc', 450)
        mnc = details.get('mnc')
        lac = details.get('lac')

        # Generate tower name
        operator_name = OPERATORS.get(mnc, 'Unknown') if mnc else 'GPS Computed'
        sector_list = ', '.join([str(s) for s in sorted(sector_cells.keys())])
        tower_name = f"{operator_name} - eNB {enodeb_id} ({len(sector_cells)} sectors: {sector_list})"

        # Create primary tower ID (use first sector's cell_id for ID)
        primary_cell_id = list(sector_cells.values())[0]

        # Collect ALL cell_ids for this eNodeB (all sectors)
        all_cell_ids = [str(cell_id).upper() for cell_id in sector_cells.values()]

        # Create GeoJSON feature for this physical tower
        tower_features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [tower_lon, tower_lat, 50]
            },
            'properties': {
                'id': f"GPS-{mcc}-{mnc}-{lac}-eNB{enodeb_id}",
                'name': tower_name,
                'radio': 'LTE',
                'operator': operator_name,
                'mcc': mcc,
                'mnc': mnc,
                'lac': lac,
                'cid': str(primary_cell_id),  # Use first sector's cell_id
                'all_cell_ids': all_cell_ids,  # ✨ ALL cell_ids for this tower
                'enodeb_id': enodeb_id,
                'sector_count': estimation['sector_count'],
                'sectors': list(sector_cells.keys()),  # List of all sectors
                'connection_count': connection_count,
                'avg_rsrp': avg_rsrp,
                'position_method': position_method,
                'uncertainty_m': uncertainty_m,
                'estimation_confidence': estimation.get('avg_confidence', 0.0),
                'num_estimation_methods': estimation.get('num_methods', 1),
                'is_connected': True
            }
        })

    # Step 3: Process cells without eNodeB info (fallback to old method)
    print(f"\n  🔧 Processing {len(cells_without_enodeb)} cells without eNodeB info...")
    for cell_id in cells_without_enodeb:
        # Skip invalid cell IDs
        if cell_id in ['0', 'FFFFFFFF', 'nan'] or pd.isna(cell_id):
            continue

        # Get all positions where drone was connected to this cell
        cell_data = df_lte[df_lte['lte_cell_id'] == cell_id].copy()

        # ✅ CONNECTED TOWER: This cell was actually connected during flight
        is_connected_tower = True  # If it appears in merged data, it was connected

        # Require RSRP data for accurate estimation
        if 'lte_rsrp' not in cell_data.columns or cell_data['lte_rsrp'].notna().sum() < 3:
            # Skip only if not connected or insufficient data
            if not is_connected_tower:
                continue
            # For connected towers with insufficient data, use all available points
            print(f"⚠️  Connected tower {cell_id} has only {cell_data['lte_rsrp'].notna().sum()} RSRP samples")

        # Filter to valid RSRP range
        cell_data_filtered = cell_data[(cell_data['lte_rsrp'] >= -140) & (cell_data['lte_rsrp'] <= -40)]

        # Signal quality filtering (use top 50% RSRP only)
        cell_data_quality = filter_by_signal_quality(cell_data_filtered, rsrp_percentile=50.0)

        # ⚠️ CRITICAL: Relax minimum data requirement from 5 → 3
        # Connected towers must be displayed even with limited data
        if len(cell_data_quality) < 3:
            if is_connected_tower and len(cell_data_filtered) >= 2:
                # Use all filtered data for connected towers
                cell_data_quality = cell_data_filtered
                print(f"⚠️  Connected tower {cell_id}: Using {len(cell_data_quality)} samples (relaxed)")
            else:
                continue

        # Use the quality-filtered data for estimation
        cell_data = cell_data_quality

        # Hybrid estimation: Trilateration + Weighted Centroid + Top-3 Average
        estimation = estimate_tower_hybrid(cell_data, verbose=False)

        tower_lat = estimation['latitude']
        tower_lon = estimation['longitude']
        tower_alt = estimation.get('altitude', 30.0)
        uncertainty_m = estimation['uncertainty_m']
        position_method = estimation['position_method']

        # Physical validation (boundary + distance check)
        is_valid, validation_reason = validate_tower_position(
            tower_lat, tower_lon,
            flight_boundary,
            flight_center_lat, flight_center_lon,
            max_distance_km=15.0
        )

        if not is_valid:
            continue

        # Get signal statistics
        all_cell_data = df_lte[df_lte['lte_cell_id'] == cell_id]
        avg_rsrp = float(all_cell_data['lte_rsrp'].mean()) if 'lte_rsrp' in all_cell_data.columns else -100
        connection_count = len(all_cell_data)

        # Get detailed cell information (cell_id is already uppercase string)
        cell_id_key = str(cell_id).upper()
        details = lte_details.get(cell_id_key, {})

        if not details:
            print(f"⚠️  No LTE details found for cell_id '{cell_id}' (normalized: '{cell_id_key}')")

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

        # Create GeoJSON feature
        tower_features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [tower_lon, tower_lat, 50]
            },
            'properties': {
                'id': f"GPS-{mcc}-{mnc}-{lac}-{cell_id}",
                'name': tower_name,
                'radio': 'LTE',
                'operator': operator_name,
                'mcc': mcc,
                'mnc': mnc,
                'lac': lac,
                'cid': str(cell_id),
                'pcid': pcid,
                'enodeb_id': enodeb_id,
                'sector_id': sector_id,
                'connection_count': connection_count,
                'avg_rsrp': avg_rsrp,
                'position_method': position_method,
                'uncertainty_m': uncertainty_m,
                'estimation_confidence': estimation.get('avg_confidence', 0.0),
                'num_estimation_methods': estimation.get('num_methods', 1),
                'is_connected': True
            }
        })

    # Create GeoJSON FeatureCollection
    return {
        'type': 'FeatureCollection',
        'features': tower_features
    }


@api_3d_bp.route('/cell-towers/<session_id>', methods=['GET'])
def get_cell_towers(session_id):
    """
    Get cell tower data for visualization
    Computes tower locations from actual drone connection data (GPS-based)

    Query Parameters:
        - use_cache: Use cached data if available (true/false) [default: true]
        - flight_id: Optional flight ID to filter by (for multi-flight sessions)

    Response:
        GeoJSON FeatureCollection with cell tower locations
    """
    try:
        # Get query parameters
        use_cache = request.args.get('use_cache', 'true', type=str) == 'true'
        flight_id = request.args.get('flight_id', None, type=int)

        # Cache key (include flight_id if specified)
        cache_key = f"cell_towers:{session_id}:LTE" if flight_id is None else f"cell_towers:{session_id}:{flight_id}:LTE"

        # Check cache (24 hour TTL)
        if use_cache and redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    print(f"✅ Cell towers cache HIT: {cache_key}")
                    return jsonify(json.loads(cached)), 200
            except Exception as e:
                print(f"⚠️ Redis cache read error: {e}")

        # Call internal function to compute tower positions
        print(f"📡 Computing tower positions from GPS data...")
        geojson = get_cell_towers_geojson_internal(session_id, flight_id=flight_id)

        # Check if any towers found
        if not geojson or not geojson.get('features'):
            return jsonify({'error': 'No LTE connection data available'}), 404

        print(f"✅ Computed {len(geojson['features'])} tower positions")

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


@api_3d_bp.route('/cell-towers-opencellid/<session_id>', methods=['GET'])
def get_cell_towers_opencellid(session_id):
    """
    Get nearby cell towers from OpenCellID API for a flight session.
    Returns blue markers showing towers in the flight area from OpenCellID database.

    Query Parameters:
        - use_cache: Use cached data if available (true/false) [default: true]
        - flight_id: Optional flight ID to filter by
        - radio: Radio type filter (LTE, UMTS, GSM, NR, ALL) [default: LTE]

    Response:
        GeoJSON FeatureCollection with cell tower locations (id does NOT start with GPS-)
    """
    try:
        use_cache = request.args.get('use_cache', 'true', type=str) == 'true'
        flight_id = request.args.get('flight_id', None, type=int)
        radio = request.args.get('radio', 'LTE', type=str)

        cache_key = f"opencellid:{session_id}:{flight_id}:{radio}"

        # Check cache (1 hour TTL)
        if use_cache and redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    print(f"✅ OpenCellID cache HIT: {cache_key}")
                    return jsonify(json.loads(cached)), 200
            except Exception as e:
                print(f"⚠️ Cache read error: {e}")

        # Validate session
        session = Session.get_by_id(session_id)
        if not session or session.status != 'completed':
            return jsonify({'error': 'Session not found or not completed'}), 404

        # Read merged data to get flight bounding box
        results_dir = Path(__file__).parent.parent.parent / 'results' / session_id
        merged_data_path = results_dir / 'merged_data.csv'

        if not merged_data_path.exists():
            return jsonify({'error': 'No flight data found'}), 404

        import pandas as pd
        df = pd.read_csv(merged_data_path, low_memory=False)

        if flight_id is not None and 'flight_id' in df.columns:
            df = df[df['flight_id'] == flight_id]

        if df.empty or 'latitude' not in df.columns:
            return jsonify({'error': 'No GPS data available'}), 404

        # Compute bounding box with ~2km buffer
        lat_buffer = 0.018
        lon_buffer = 0.018
        lat_min = float(df['latitude'].min()) - lat_buffer
        lat_max = float(df['latitude'].max()) + lat_buffer
        lon_min = float(df['longitude'].min()) - lon_buffer
        lon_max = float(df['longitude'].max()) + lon_buffer

        print(f"📐 Flight bbox: ({lat_min:.4f},{lon_min:.4f}) → ({lat_max:.4f},{lon_max:.4f})")

        # Get OpenCellID client
        client = get_opencellid_client()
        if not client:
            return jsonify({'error': 'OpenCellID API key not configured. Set OPENCELLID_API_KEY env var.'}), 503

        # Grid search over flight bounding box
        towers = client.get_cell_towers_grid_search(
            min_lat=lat_min, max_lat=lat_max,
            min_lon=lon_min, max_lon=lon_max,
            radio=radio
        )

        print(f"✅ OpenCellID returned {len(towers)} towers")

        # Convert to GeoJSON (ids do NOT start with GPS-, so frontend renders blue)
        geojson = _convert_towers_to_geojson(towers)

        # Cache result (1 hour)
        if redis_client:
            try:
                redis_client.setex(cache_key, 3600, json.dumps(geojson))
                print(f"💾 OpenCellID towers cached: {cache_key}")
            except Exception as e:
                print(f"⚠️ Cache write error: {e}")

        return jsonify(geojson), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to fetch OpenCellID towers: {str(e)}'}), 500


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
        - color_by: What to color arrows by ('starlink_latency') (default: 'starlink_latency')
        - arrow_length: Arrow length in meters (default: 10)
        - flight_id: Optional flight ID to filter by (for multi-flight sessions)

    Returns:
        CZML JSON data with satellite direction polyline arrows
    """
    try:
        # Get query parameters
        sample_rate = request.args.get('sample_rate', 0.2, type=float)
        color_by = request.args.get('color_by', 'starlink_latency', type=str)
        arrow_length = request.args.get('arrow_length', 10, type=int)
        flight_id = request.args.get('flight_id', None, type=int)

        # Validate color_by
        if color_by not in ['starlink_latency']:
            return jsonify({'error': 'Invalid color_by. Must be starlink_latency'}), 400

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


@api_3d_bp.route('/attitude-analysis/<session_id>', methods=['GET'])
def get_attitude_analysis(session_id):
    """
    Analyze aircraft attitude (pitch, roll) vs Starlink performance
    Returns Pitch+Elevation matrix and other attitude-based statistics

    Query Parameters:
        - flight_id: Optional flight ID to filter by (for multi-flight sessions)

    Returns:
        JSON with:
        - pitch_elevation_matrix: 2D matrix of success rates by pitch and elevation bins
        - pitch_stats: Performance by pitch angle
        - roll_stats: Performance by roll angle
        - azimuth_stats: Performance by satellite azimuth direction
        - optimal_conditions: Best performing conditions
    """
    try:
        import pandas as pd
        import numpy as np

        flight_id = request.args.get('flight_id', None, type=int)

        # Load merged data
        results_dir = Path(__file__).parent.parent.parent / 'results' / session_id
        merged_data_path = results_dir / 'merged_data.csv'

        if not merged_data_path.exists():
            return jsonify({'error': 'Session data not found'}), 404

        df = pd.read_csv(merged_data_path)

        # Filter by flight_id if specified
        if flight_id is not None and 'flight_id' in df.columns:
            df = df[df['flight_id'] == flight_id]

        # Check required columns
        required_cols = ['pitch']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return jsonify({'error': f'Missing required columns: {missing}'}), 400

        # ═══════════════════════════════════════════════════════════════
        # Multi-metric performance analysis: Upload, Download, Latency
        # ═══════════════════════════════════════════════════════════════

        # Upload throughput analysis (>200 Kbps = good)
        if 'starlink_uplink_throughput_bps' in df.columns:
            df['is_good_upload'] = df['starlink_uplink_throughput_bps'] > 200_000
            df['upload_mbps'] = df['starlink_uplink_throughput_bps'] / 1_000_000
        else:
            df['is_good_upload'] = False
            df['upload_mbps'] = 0

        # Download throughput analysis (>1 Mbps = good)
        if 'starlink_downlink_throughput_bps' in df.columns:
            df['is_good_download'] = df['starlink_downlink_throughput_bps'] > 1_000_000
            df['download_mbps'] = df['starlink_downlink_throughput_bps'] / 1_000_000
        else:
            df['is_good_download'] = False
            df['download_mbps'] = 0

        # Latency analysis (<50ms = good)
        if 'starlink_latency' in df.columns:
            df['is_good_latency'] = df['starlink_latency'] < 50
        else:
            df['is_good_latency'] = False

        # Combined "good" = good upload (primary metric)
        df['is_good'] = df['is_good_upload']

        # 1. Pitch + Elevation Matrix
        pitch_bins = [-90, -5, -2, 0, 2, 5, 90]
        pitch_labels = ['<-5°', '-5~-2°', '-2~0°', '0~2°', '2~5°', '>5°']

        elev_bins = [0, 75, 80, 85, 90, 100]
        elev_labels = ['<75°', '75-80°', '80-85°', '85-90°', '>90°']

        df['pitch_bin'] = pd.cut(df['pitch'], bins=pitch_bins, labels=pitch_labels, include_lowest=True)

        if 'starlink_elevation' in df.columns:
            df['elev_bin'] = pd.cut(df['starlink_elevation'], bins=elev_bins, labels=elev_labels, include_lowest=True)

            # Create pivot table for success rate (all metrics)
            agg_dict = {
                'is_good_upload': ['mean', 'count'],
                'upload_mbps': 'mean'
            }
            if 'download_mbps' in df.columns:
                agg_dict['is_good_download'] = 'mean'
                agg_dict['download_mbps'] = 'mean'
            if 'starlink_latency' in df.columns:
                agg_dict['is_good_latency'] = 'mean'
                agg_dict['starlink_latency'] = 'mean'

            matrix_df = df.groupby(['pitch_bin', 'elev_bin'], observed=True).agg(agg_dict).reset_index()

            # Flatten column names
            matrix_df.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in matrix_df.columns.values]

            # Convert to matrix format for frontend
            pitch_elevation_matrix = []
            for _, row in matrix_df.iterrows():
                if pd.notna(row['pitch_bin']) and pd.notna(row['elev_bin']):
                    item = {
                        'pitch': str(row['pitch_bin']),
                        'elevation': str(row['elev_bin']),
                        'success_rate': round(float(row.get('is_good_upload_mean', 0)) * 100, 1),
                        'count': int(row.get('is_good_upload_count', 0)),
                        'avg_upload_mbps': round(float(row.get('upload_mbps_mean', 0)), 3) if pd.notna(row.get('upload_mbps_mean')) else 0
                    }
                    # Add download metrics if available
                    if 'is_good_download_mean' in row:
                        item['download_success_rate'] = round(float(row['is_good_download_mean']) * 100, 1)
                        item['avg_download_mbps'] = round(float(row.get('download_mbps_mean', 0)), 3) if pd.notna(row.get('download_mbps_mean')) else 0
                    # Add latency metrics if available
                    if 'is_good_latency_mean' in row:
                        item['latency_success_rate'] = round(float(row['is_good_latency_mean']) * 100, 1)
                        item['avg_latency_ms'] = round(float(row.get('starlink_latency_mean', 0)), 1) if pd.notna(row.get('starlink_latency_mean')) else 0
                    pitch_elevation_matrix.append(item)
        else:
            pitch_elevation_matrix = []

        # 2. Pitch Stats (success rate by pitch angle) - all metrics
        pitch_agg = {'is_good_upload': ['mean', 'count'], 'upload_mbps': 'mean'}
        if 'download_mbps' in df.columns:
            pitch_agg['is_good_download'] = 'mean'
            pitch_agg['download_mbps'] = 'mean'
        if 'starlink_latency' in df.columns:
            pitch_agg['is_good_latency'] = 'mean'
            pitch_agg['starlink_latency'] = 'mean'

        pitch_stats = df.groupby('pitch_bin', observed=True).agg(pitch_agg).reset_index()
        pitch_stats.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in pitch_stats.columns.values]

        pitch_stats_list = []
        for _, row in pitch_stats.iterrows():
            if pd.notna(row['pitch_bin']):
                item = {
                    'pitch': str(row['pitch_bin']),
                    'success_rate': round(float(row.get('is_good_upload_mean', 0)) * 100, 1),
                    'count': int(row.get('is_good_upload_count', 0)),
                    'avg_upload_mbps': round(float(row.get('upload_mbps_mean', 0)), 3) if pd.notna(row.get('upload_mbps_mean')) else 0
                }
                if 'is_good_download_mean' in row:
                    item['download_success_rate'] = round(float(row['is_good_download_mean']) * 100, 1)
                    item['avg_download_mbps'] = round(float(row.get('download_mbps_mean', 0)), 3) if pd.notna(row.get('download_mbps_mean')) else 0
                if 'is_good_latency_mean' in row:
                    item['latency_success_rate'] = round(float(row['is_good_latency_mean']) * 100, 1)
                    item['avg_latency_ms'] = round(float(row.get('starlink_latency_mean', 0)), 1) if pd.notna(row.get('starlink_latency_mean')) else 0
                pitch_stats_list.append(item)

        # 3. Roll Stats - all metrics
        roll_bins = [-90, -10, -5, -2, 2, 5, 10, 90]
        roll_labels = ['<-10°', '-10~-5°', '-5~-2°', '-2~2°', '2~5°', '5~10°', '>10°']
        df['roll_bin'] = pd.cut(df['roll'], bins=roll_bins, labels=roll_labels, include_lowest=True)

        roll_agg = {'is_good_upload': ['mean', 'count'], 'upload_mbps': 'mean'}
        if 'download_mbps' in df.columns:
            roll_agg['is_good_download'] = 'mean'
            roll_agg['download_mbps'] = 'mean'
        if 'starlink_latency' in df.columns:
            roll_agg['is_good_latency'] = 'mean'
            roll_agg['starlink_latency'] = 'mean'

        roll_stats = df.groupby('roll_bin', observed=True).agg(roll_agg).reset_index()
        roll_stats.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in roll_stats.columns.values]

        roll_stats_list = []
        for _, row in roll_stats.iterrows():
            if pd.notna(row['roll_bin']):
                item = {
                    'roll': str(row['roll_bin']),
                    'success_rate': round(float(row.get('is_good_upload_mean', 0)) * 100, 1),
                    'count': int(row.get('is_good_upload_count', 0)),
                    'avg_upload_mbps': round(float(row.get('upload_mbps_mean', 0)), 3) if pd.notna(row.get('upload_mbps_mean')) else 0
                }
                if 'is_good_download_mean' in row:
                    item['download_success_rate'] = round(float(row['is_good_download_mean']) * 100, 1)
                    item['avg_download_mbps'] = round(float(row.get('download_mbps_mean', 0)), 3) if pd.notna(row.get('download_mbps_mean')) else 0
                if 'is_good_latency_mean' in row:
                    item['latency_success_rate'] = round(float(row['is_good_latency_mean']) * 100, 1)
                    item['avg_latency_ms'] = round(float(row.get('starlink_latency_mean', 0)), 1) if pd.notna(row.get('starlink_latency_mean')) else 0
                roll_stats_list.append(item)

        # 4. Azimuth Stats (satellite direction)
        if 'starlink_azimuth' in df.columns:
            # Convert azimuth to compass direction
            def azimuth_to_direction(az):
                if pd.isna(az):
                    return None
                az = az % 360
                if az < 22.5 or az >= 337.5:
                    return 'N'
                elif az < 67.5:
                    return 'NE'
                elif az < 112.5:
                    return 'E'
                elif az < 157.5:
                    return 'SE'
                elif az < 202.5:
                    return 'S'
                elif az < 247.5:
                    return 'SW'
                elif az < 292.5:
                    return 'W'
                else:
                    return 'NW'

            df['azimuth_dir'] = df['starlink_azimuth'].apply(azimuth_to_direction)

            azimuth_agg = {'is_good_upload': ['mean', 'count'], 'upload_mbps': 'mean'}
            if 'download_mbps' in df.columns:
                azimuth_agg['is_good_download'] = 'mean'
                azimuth_agg['download_mbps'] = 'mean'
            if 'starlink_latency' in df.columns:
                azimuth_agg['is_good_latency'] = 'mean'
                azimuth_agg['starlink_latency'] = 'mean'

            azimuth_stats = df.groupby('azimuth_dir', observed=True).agg(azimuth_agg).reset_index()
            azimuth_stats.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in azimuth_stats.columns.values]

            azimuth_stats_list = []
            for _, row in azimuth_stats.iterrows():
                if pd.notna(row['azimuth_dir']):
                    item = {
                        'direction': str(row['azimuth_dir']),
                        'success_rate': round(float(row.get('is_good_upload_mean', 0)) * 100, 1),
                        'count': int(row.get('is_good_upload_count', 0)),
                        'avg_upload_mbps': round(float(row.get('upload_mbps_mean', 0)), 3) if pd.notna(row.get('upload_mbps_mean')) else 0
                    }
                    if 'is_good_download_mean' in row:
                        item['download_success_rate'] = round(float(row['is_good_download_mean']) * 100, 1)
                        item['avg_download_mbps'] = round(float(row.get('download_mbps_mean', 0)), 3) if pd.notna(row.get('download_mbps_mean')) else 0
                    if 'is_good_latency_mean' in row:
                        item['latency_success_rate'] = round(float(row['is_good_latency_mean']) * 100, 1)
                        item['avg_latency_ms'] = round(float(row.get('starlink_latency_mean', 0)), 1) if pd.notna(row.get('starlink_latency_mean')) else 0
                    azimuth_stats_list.append(item)
        else:
            azimuth_stats_list = []

        # 5. Elevation Stats - all metrics
        if 'starlink_elevation' in df.columns:
            elev_agg = {'is_good_upload': ['mean', 'count'], 'upload_mbps': 'mean'}
            if 'download_mbps' in df.columns:
                elev_agg['is_good_download'] = 'mean'
                elev_agg['download_mbps'] = 'mean'
            if 'starlink_latency' in df.columns:
                elev_agg['is_good_latency'] = 'mean'
                elev_agg['starlink_latency'] = 'mean'

            elev_stats = df.groupby('elev_bin', observed=True).agg(elev_agg).reset_index()
            elev_stats.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in elev_stats.columns.values]

            elev_stats_list = []
            for _, row in elev_stats.iterrows():
                if pd.notna(row['elev_bin']):
                    item = {
                        'elevation': str(row['elev_bin']),
                        'success_rate': round(float(row.get('is_good_upload_mean', 0)) * 100, 1),
                        'count': int(row.get('is_good_upload_count', 0)),
                        'avg_upload_mbps': round(float(row.get('upload_mbps_mean', 0)), 3) if pd.notna(row.get('upload_mbps_mean')) else 0
                    }
                    if 'is_good_download_mean' in row:
                        item['download_success_rate'] = round(float(row['is_good_download_mean']) * 100, 1)
                        item['avg_download_mbps'] = round(float(row.get('download_mbps_mean', 0)), 3) if pd.notna(row.get('download_mbps_mean')) else 0
                    if 'is_good_latency_mean' in row:
                        item['latency_success_rate'] = round(float(row['is_good_latency_mean']) * 100, 1)
                        item['avg_latency_ms'] = round(float(row.get('starlink_latency_mean', 0)), 1) if pd.notna(row.get('starlink_latency_mean')) else 0
                    elev_stats_list.append(item)
        else:
            elev_stats_list = []

        # 6. Find optimal conditions
        optimal_pitch = None
        optimal_elev = None
        optimal_success = 0

        for item in pitch_elevation_matrix:
            if item['count'] >= 100 and item['success_rate'] > optimal_success:
                optimal_success = item['success_rate']
                optimal_pitch = item['pitch']
                optimal_elev = item['elevation']

        # 7. Summary statistics - all metrics
        total_points = len(df)

        # Upload stats
        good_upload_points = int(df['is_good_upload'].sum())
        overall_upload_success_rate = round(good_upload_points / total_points * 100, 1) if total_points > 0 else 0
        avg_upload_mbps = round(float(df['upload_mbps'].mean()), 3) if 'upload_mbps' in df.columns else 0
        max_upload_mbps = round(float(df['upload_mbps'].max()), 3) if 'upload_mbps' in df.columns else 0

        # Download stats
        good_download_points = int(df['is_good_download'].sum()) if 'is_good_download' in df.columns else 0
        overall_download_success_rate = round(good_download_points / total_points * 100, 1) if total_points > 0 else 0
        avg_download_mbps = round(float(df['download_mbps'].mean()), 3) if 'download_mbps' in df.columns else 0
        max_download_mbps = round(float(df['download_mbps'].max()), 3) if 'download_mbps' in df.columns else 0

        # Latency stats
        good_latency_points = int(df['is_good_latency'].sum()) if 'is_good_latency' in df.columns else 0
        overall_latency_success_rate = round(good_latency_points / total_points * 100, 1) if total_points > 0 else 0
        avg_latency_ms = round(float(df['starlink_latency'].mean()), 1) if 'starlink_latency' in df.columns else 0
        min_latency_ms = round(float(df['starlink_latency'].min()), 1) if 'starlink_latency' in df.columns else 0

        return jsonify({
            'session_id': session_id,
            'total_points': total_points,

            # Upload metrics (primary)
            'good_points': good_upload_points,
            'overall_success_rate': overall_upload_success_rate,
            'avg_upload_mbps': avg_upload_mbps,
            'max_upload_mbps': max_upload_mbps,

            # Download metrics
            'good_download_points': good_download_points,
            'download_success_rate': overall_download_success_rate,
            'avg_download_mbps': avg_download_mbps,
            'max_download_mbps': max_download_mbps,

            # Latency metrics
            'good_latency_points': good_latency_points,
            'latency_success_rate': overall_latency_success_rate,
            'avg_latency_ms': avg_latency_ms,
            'min_latency_ms': min_latency_ms,

            # Detailed stats
            'pitch_elevation_matrix': pitch_elevation_matrix,
            'pitch_stats': pitch_stats_list,
            'roll_stats': roll_stats_list,
            'azimuth_stats': azimuth_stats_list,
            'elevation_stats': elev_stats_list,
            'optimal_conditions': {
                'pitch': optimal_pitch,
                'elevation': optimal_elev,
                'success_rate': optimal_success
            }
        }), 200

    except Exception as e:
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
