"""
3D Visualization API Routes
Endpoints for CZML data and flight visualization
"""

from flask import Blueprint, jsonify, request
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.session import Session
from .czml_generator import CZMLGenerator

api_3d_bp = Blueprint('api_3d', __name__, url_prefix='/api/3d')


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


@api_3d_bp.route('/czml/<session_id>', methods=['GET'])
def get_czml_data(session_id):
    """
    Generate and return CZML data for a flight session

    Args:
        session_id: Session identifier

    Query Parameters:
        - sample_rate: Sampling rate in Hz (default: 1)
        - color_by: What to color by ('altitude', 'speed', 'quality') (default: 'altitude')

    Returns:
        CZML JSON data
    """
    try:
        # Get query parameters
        sample_rate = request.args.get('sample_rate', 1, type=int)
        color_by = request.args.get('color_by', 'altitude', type=str)

        # Validate session
        session = Session.get_by_id(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session.status != 'completed':
            return jsonify({'error': 'Session not completed'}), 400

        # Generate CZML
        generator = CZMLGenerator(session_id)
        czml_data = generator.generate(
            sample_rate=sample_rate,
            color_by=color_by
        )

        return jsonify(czml_data), 200

    except Exception as e:
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

    Returns:
        CZML JSON data with heatmap entities
    """
    try:
        # Get query parameters
        mode = request.args.get('mode', 'lte', type=str)
        style = request.args.get('style', 'point', type=str)

        # Validate mode
        if mode not in ['lte', 'starlink', 'combined']:
            return jsonify({'error': 'Invalid mode. Must be lte, starlink, or combined'}), 400

        # Validate style
        if style not in ['point', 'voxel']:
            return jsonify({'error': 'Invalid style. Must be point or voxel'}), 400

        # Validate session
        session = Session.get_by_id(session_id)

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session.status != 'completed':
            return jsonify({'error': 'Session not completed'}), 400

        # Generate heatmap CZML
        generator = CZMLGenerator(session_id)
        czml_data = generator.create_heatmap_czml(mode=mode, style=style)

        return jsonify(czml_data), 200

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
