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
from .czml_generator import CZMLGenerator, compute_lte_cqs_scores
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

                # Extract actual flight time range from merged_data.csv
                flight_time_range = None
                try:
                    import pandas as pd
                    results_dir = Path(__file__).parent.parent.parent / 'results' / session.id
                    merged_data_path = results_dir / 'merged_data.csv'
                    if merged_data_path.exists():
                        df_times = pd.read_csv(merged_data_path, usecols=['timestamp'])
                        df_times = df_times.dropna()
                        if len(df_times) > 0:
                            flight_time_range = {
                                'start': str(df_times['timestamp'].min()),
                                'end': str(df_times['timestamp'].max())
                            }
                except Exception:
                    pass

                flights.append({
                    'id': session.id,
                    'name': session.name or f"Flight {session.id}",
                    'created_at': created_at,
                    'file_count': {
                        'flight_logs': flight_logs_count,
                        'lte_data': lte_data_count,
                        'starlink_data': starlink_data_count
                    },
                    'time_range': flight_time_range
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
        lap = request.args.get('lap', 0, type=int)  # 0=all, 1=lap1, 2=lap2
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
        cache_key = f"czml:{session_id}:{sample_rate}:{color_by}:{flight_id}:{lap}:{custom_metrics_hash}"

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
            custom_metrics=custom_metrics,
            lap=lap
        )
        generation_time = (time.time() - start_time) * 1000  # Convert to ms
        print(f"⏱️ CZML generation time: {generation_time:.1f}ms")

        # Convert to JSON
        czml_json = json.dumps(czml_data)

        # Cache the JSON data (1 hour TTL — uploaded data is immutable)
        if redis_client:
            try:
                redis_client.setex(cache_key, 3600, czml_json)
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
        metric = request.args.get('metric', None, type=str)  # Explicit metric override
        style = 'hexagon'  # Only hexagon style supported
        flight_id = request.args.get('flight_id', None, type=int)
        resolution = request.args.get('resolution', 8, type=int)
        aggregation = request.args.get('aggregation', 'mean', type=str)
        altitude_bin_size = request.args.get('altitude_bin_size', 25.0, type=float)

        # Validate mode
        if mode not in ['lte', 'starlink', 'combined']:
            return jsonify({'error': 'Invalid mode. Must be lte, starlink, or combined'}), 400

        # Validate hexagon-specific parameters
        if style == 'hexagon':
            if not 7 <= resolution <= 10:
                return jsonify({'error': 'Invalid resolution. Must be between 7 and 10'}), 400
            if aggregation not in ['mean', 'max', 'min', 'median']:
                return jsonify({'error': 'Invalid aggregation. Must be mean, max, min, or median'}), 400
            if not 10 <= altitude_bin_size <= 100:
                return jsonify({'error': 'Invalid altitude_bin_size. Must be between 10 and 100'}), 400

        # Create cache key (include hexagon parameters)
        cache_key = f"heatmap:{session_id}:{mode}:{metric}:{style}:{flight_id}:{resolution}:{aggregation}:{altitude_bin_size}"

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

        if True:  # hexagon only
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

            # Hexagonal heatmap: LTE → CQS, Starlink → download speed
            has_lte_cqs = ('lte_rsrp' in df.columns and not df['lte_rsrp'].isna().all() and
                           'lte_sinr' in df.columns and 'lte_rsrq' in df.columns)
            has_starlink_dl = ('starlink_downlink_throughput_bps' in df.columns and
                               not df['starlink_downlink_throughput_bps'].isna().all())

            df = df.copy()

            # Pre-compute normalized columns (0-1 scale)
            if has_lte_cqs:
                df['_lte_cqs'] = compute_lte_cqs_scores(df)
                print(f"📊 Hexagon: CQS pre-computed ({df['_lte_cqs'].notna().sum()} valid rows)", flush=True)

            if has_starlink_dl:
                # 0.3 Mbps = p95 기준 (combined_connectivity와 동일한 수치)
                dl_mbps = pd.to_numeric(df['starlink_downlink_throughput_bps'], errors='coerce') / 1_000_000.0
                df['_starlink_dl_norm'] = (dl_mbps / 0.3).clip(0, 1)
                print(f"📊 Hexagon: Starlink DL norm pre-computed ({df['_starlink_dl_norm'].notna().sum()} valid rows)", flush=True)

            # Combined: combined_connectivity 경로 색상과 동일한 공식 (평균 50:50, 한쪽만 있으면 그쪽 사용)
            if mode == 'combined' and has_lte_cqs and has_starlink_dl:
                lte = df['_lte_cqs']
                sl = df['_starlink_dl_norm']
                both = lte.notna() & sl.notna()
                lte_only = lte.notna() & sl.isna()
                sl_only = lte.isna() & sl.notna()
                combined = pd.Series(float('nan'), index=df.index)
                combined[both] = (lte[both] + sl[both]) / 2.0
                combined[lte_only] = lte[lte_only]
                combined[sl_only] = sl[sl_only]
                df['_combined_score'] = combined
                quality_mode = '_combined_score'
            elif mode == 'combined' and has_lte_cqs:
                quality_mode = '_lte_cqs'
            elif mode == 'combined' and has_starlink_dl:
                quality_mode = '_starlink_dl_norm'
            elif mode == 'lte':
                quality_mode = '_lte_cqs' if has_lte_cqs else None
            elif mode == 'starlink':
                quality_mode = '_starlink_dl_norm' if has_starlink_dl else None
            else:
                quality_mode = None

            # Explicit metric override (from dropdown selection)
            if metric and metric in df.columns:
                quality_mode = metric
                print(f"📊 Heatmap metric override: {metric}", flush=True)

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

        # Convert to JSON
        czml_json = json.dumps(czml_data)

        # Cache the JSON data (1 hour TTL — uploaded data is immutable)
        if redis_client:
            try:
                redis_client.setex(cache_key, 3600, czml_json)
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



@api_3d_bp.route('/heatmap/all-sessions', methods=['GET'])
def get_all_sessions_heatmap_czml():
    """
    Generate and return heatmap CZML combining data from ALL completed sessions.

    Query Parameters:
        - mode: Heatmap mode ('lte', 'starlink', or 'combined') (default: 'combined')
        - resolution: H3 resolution for hexagon (7-10) (default: 8)
        - aggregation: Aggregation method ('mean', 'max', 'min', 'median') (default: 'mean')
        - altitude_bin_size: Altitude bin size in meters (default: 25)

    Returns:
        CZML JSON data with heatmap entities aggregated across all sessions
    """
    try:
        import pandas as pd

        mode = request.args.get('mode', 'combined', type=str)
        resolution = request.args.get('resolution', 8, type=int)
        aggregation = request.args.get('aggregation', 'mean', type=str)
        altitude_bin_size = request.args.get('altitude_bin_size', 25.0, type=float)

        if mode not in ['lte', 'starlink', 'combined']:
            return jsonify({'error': 'Invalid mode. Must be lte, starlink, or combined'}), 400
        if not 7 <= resolution <= 10:
            return jsonify({'error': 'Invalid resolution. Must be between 7 and 10'}), 400
        if aggregation not in ['mean', 'max', 'min', 'median']:
            return jsonify({'error': 'Invalid aggregation.'}), 400
        if not 10 <= altitude_bin_size <= 100:
            return jsonify({'error': 'Invalid altitude_bin_size. Must be between 10 and 100'}), 400

        cache_key = f"heatmap:all-sessions:{mode}:hexagon:{resolution}:{aggregation}:{altitude_bin_size}"

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

        # Load all completed sessions' merged_data.csv
        start_time = time.time()
        results_base = Path(__file__).parent.parent.parent / 'results'

        sessions = Session.get_all()
        completed_sessions = [s for s in sessions if s.status == 'completed']

        dfs = []
        for session in completed_sessions:
            merged_data_path = results_base / session.id / 'merged_data.csv'
            if merged_data_path.exists():
                try:
                    df_session = pd.read_csv(merged_data_path, low_memory=False)
                    df_session['_session_id'] = session.id
                    dfs.append(df_session)
                    print(f"  ✅ Loaded session {session.id}: {len(df_session)} rows")
                except Exception as e:
                    print(f"  ⚠️ Failed to load {session.id}: {e}")

        if not dfs:
            return jsonify({'error': 'No completed session data found'}), 404

        df = pd.concat(dfs, ignore_index=True)
        print(f"📊 All-sessions combined: {len(df)} total rows from {len(dfs)} sessions")

        # Pre-compute normalized columns (same as single-session endpoint)
        df = df.copy()

        has_lte_cqs = ('lte_rsrp' in df.columns and not df['lte_rsrp'].isna().all() and
                       'lte_sinr' in df.columns and 'lte_rsrq' in df.columns)
        has_starlink_dl = ('starlink_downlink_throughput_bps' in df.columns and
                           not df['starlink_downlink_throughput_bps'].isna().all())

        if has_lte_cqs:
            df['_lte_cqs'] = compute_lte_cqs_scores(df)
            print(f"📊 CQS pre-computed ({df['_lte_cqs'].notna().sum()} valid rows)")

        if has_starlink_dl:
            dl_mbps = pd.to_numeric(df['starlink_downlink_throughput_bps'], errors='coerce') / 1_000_000.0
            df['_starlink_dl_norm'] = (dl_mbps / 0.3).clip(0, 1)
            print(f"📊 Starlink DL norm pre-computed ({df['_starlink_dl_norm'].notna().sum()} valid rows)")

        if mode == 'combined' and has_lte_cqs and has_starlink_dl:
            lte = df['_lte_cqs']
            sl = df['_starlink_dl_norm']
            both = lte.notna() & sl.notna()
            lte_only = lte.notna() & sl.isna()
            sl_only = lte.isna() & sl.notna()
            combined = pd.Series(float('nan'), index=df.index)
            combined[both] = (lte[both] + sl[both]) / 2.0
            combined[lte_only] = lte[lte_only]
            combined[sl_only] = sl[sl_only]
            df['_combined_score'] = combined
            quality_mode = '_combined_score'
        elif mode == 'combined' and has_lte_cqs:
            quality_mode = '_lte_cqs'
        elif mode == 'combined' and has_starlink_dl:
            quality_mode = '_starlink_dl_norm'
        elif mode == 'lte':
            quality_mode = '_lte_cqs' if has_lte_cqs else None
        elif mode == 'starlink':
            quality_mode = '_starlink_dl_norm' if has_starlink_dl else None
        else:
            quality_mode = None

        if quality_mode is None:
            return jsonify([{"id": "document", "version": "1.0", "name": f"Empty All-Sessions Heatmap - No {mode.upper()} data"}]), 200

        hex_generator = HexagonalHeatmapGenerator(
            resolution=resolution,
            altitude_bin_size=altitude_bin_size
        )
        czml_data = hex_generator.generate_czml(
            df=df,
            mode=quality_mode,
            aggregation=aggregation,
            extrusion_height=0
        )

        generation_time = (time.time() - start_time) * 1000
        voxel_count = len(czml_data) - 1
        print(f"⏱️ All-sessions heatmap: {generation_time:.1f}ms, {voxel_count} voxels, {len(dfs)} sessions")

        czml_json = json.dumps(czml_data)

        if redis_client:
            try:
                redis_client.setex(cache_key, 3600, czml_json)
                print(f"💾 Cache saved: {cache_key} ({len(czml_json)} bytes)")
            except Exception as e:
                print(f"⚠️ Cache write error: {e}")

        response = make_response(czml_json)
        response.headers['Content-Type'] = 'application/json'
        response.headers['X-Cache'] = 'MISS'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_3d_bp.route('/cell-towers/<session_id>', methods=['GET'])
def get_cell_towers(session_id):
    """
    Return official cell tower locations from Korean MSIT data (고흥읍 기지국)
    """
    try:
        data_path = Path(__file__).parent.parent.parent / 'data' / 'goheung_cell_towers.json'
        if not data_path.exists():
            return jsonify({'type': 'FeatureCollection', 'features': []}), 200
        with open(data_path, 'r', encoding='utf-8') as f:
            geojson = json.load(f)
        return jsonify(geojson), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

        # Cache the JSON data (1 hour TTL — uploaded data is immutable)
        if redis_client:
            try:
                redis_client.setex(cache_key, 3600, czml_json)
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

        # Cache the JSON data (1 hour TTL — uploaded data is immutable)
        if redis_client:
            try:
                redis_client.setex(cache_key, 3600, czml_json)
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


@api_3d_bp.route('/lap-info/<session_id>', methods=['GET'])
def get_lap_info(session_id: str):
    """
    Detect and return lap boundary information for a flight path.
    Supports flight_id query param to detect laps per flight, not per session.

    Returns:
        JSON with lap boundary timestamp and lap point counts.
    """
    try:
        import pandas as pd
        import numpy as np
        from pathlib import Path

        flight_id = request.args.get('flight_id', None, type=int)

        results_dir = Path(__file__).parent.parent.parent / 'results' / session_id
        merged_data_path = results_dir / 'merged_data.csv'

        if not merged_data_path.exists():
            return jsonify({'error': 'No merged data found', 'has_laps': False}), 404

        df = pd.read_csv(merged_data_path, parse_dates=['timestamp'])
        df = df.dropna(subset=['latitude', 'longitude'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        # Filter by flight_id if specified (lap detection per flight, not per session)
        if flight_id is not None and 'flight_id' in df.columns:
            df = df[df['flight_id'] == flight_id]
            if df.empty:
                return jsonify({'has_laps': False, 'reason': f'No data for flight_id {flight_id}'})

        gps = df[['latitude', 'longitude']].dropna()
        if len(gps) < 100:
            return jsonify({'has_laps': False, 'reason': 'Not enough GPS data'})

        start_lat = gps['latitude'].iloc[0]
        start_lon = gps['longitude'].iloc[0]

        dlat = (gps['latitude'] - start_lat) * 111000
        dlon = (gps['longitude'] - start_lon) * 111000 * np.cos(np.radians(start_lat))
        dist = np.sqrt(dlat**2 + dlon**2)

        window = min(30, len(dist) // 20)
        dist_smooth = dist.rolling(window, center=True, min_periods=1).mean()

        max_dist = dist_smooth.max()

        # Find FIRST return to start AFTER having flown far away.
        # Uses was_far cumsum (not global peak) so it works even when the global
        # peak occurs in lap 2 rather than lap 1.
        threshold = max_dist * 0.10
        was_far = (dist_smooth > max_dist * 0.30).cumsum()
        is_close = dist_smooth <= threshold
        close_to_start = dist_smooth[is_close & (was_far > 0)]
        if len(close_to_start) == 0:
            close_to_start = dist_smooth[(dist_smooth <= max_dist * 0.20) & (was_far > 0)]
        if len(close_to_start) == 0:
            return jsonify({'has_laps': False, 'reason': 'Path does not return close to start'})

        lap_boundary_idx = close_to_start.index[0]
        min_dist = dist_smooth.loc[lap_boundary_idx]

        # Verify lap 2 exists after boundary
        after_boundary = dist_smooth.loc[lap_boundary_idx:]
        if len(after_boundary) < 20 or after_boundary.max() < max_dist * 0.3:
            return jsonify({'has_laps': False, 'reason': 'No significant lap 2 after boundary'})

        # Calculate boundary position
        boundary_pos = df.index.get_loc(lap_boundary_idx) if lap_boundary_idx in df.index else df.index.searchsorted(lap_boundary_idx)
        if isinstance(boundary_pos, slice):
            boundary_pos = boundary_pos.start

        # Format boundary timestamp as ISO string
        boundary_str = str(lap_boundary_idx)

        return jsonify({
            'has_laps': True,
            'lap_boundary': boundary_str,
            'lap1_points': int(boundary_pos),
            'lap2_points': int(len(df) - boundary_pos),
            'total_points': int(len(df)),
            'lap1_start': str(df.index[0]),
            'lap2_start': boundary_str,
            'lap_end': str(df.index[-1]),
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'has_laps': False}), 500


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
