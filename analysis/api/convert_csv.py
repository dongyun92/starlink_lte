"""
CSV Conversion API - Convert ULG files to UAO database CSV format
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import tempfile
from pyulog import ULog
import pandas as pd
from datetime import datetime
import math

convert_csv_bp = Blueprint('convert_csv', __name__)

ALLOWED_EXTENSIONS = {'ulg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def convert_ulg_to_csv_data(ulg_path, session_id, aircraft_id='UMT001'):
    """
    Convert ULG file to CSV format for UAO database

    Args:
        ulg_path: Path to ULG file
        session_id: Session identifier
        aircraft_id: Aircraft identifier (default: UMT001)

    Returns:
        DataFrame with converted data
    """
    # Load ULG file
    ulog = ULog(ulg_path)

    # Extract GPS data
    gps_data = ulog.get_dataset('vehicle_gps_position')

    records = []
    total_points = len(gps_data.data['timestamp'])

    # Sample every 10th point for 1Hz sampling
    sample_interval = 10

    for i in range(0, total_points, sample_interval):
        # Timestamp conversion
        time_utc_us = gps_data.data['time_utc_usec'][i]
        dt = datetime.utcfromtimestamp(time_utc_us / 1e6)

        # Position (already in degrees)
        lat = gps_data.data['latitude_deg'][i]
        lon = gps_data.data['longitude_deg'][i]
        alt_m = gps_data.data['altitude_msl_m'][i]

        # Unit conversions
        altitude = round(alt_m * 3.28084)  # meters → feet

        # Speed (already in m/s)
        speed_ms = gps_data.data['vel_m_s'][i]
        speed = round(speed_ms * 1.94384)  # m/s → knots

        # Heading
        if 'heading' in gps_data.data and not math.isnan(gps_data.data['heading'][i]):
            heading_deg = gps_data.data['heading'][i]
        else:
            cog_rad = gps_data.data['cog_rad'][i]
            if not math.isnan(cog_rad):
                heading_deg = cog_rad * 57.2958  # radians to degrees
            else:
                heading_deg = 0
        heading = round(heading_deg) % 360

        # Vertical rate
        vel_d_ms = gps_data.data['vel_d_m_s'][i]
        vertical_rate = round(-vel_d_ms * 196.85)  # m/s → feet/min

        # On ground determination
        on_ground = altitude < 100

        records.append({
            'hexid': aircraft_id,
            'callsign': aircraft_id,
            'aircraft_type': 'UAM',
            'latitude': round(lat, 6),
            'longitude': round(lon, 6),
            'altitude': altitude,
            'speed': speed,
            'heading': heading,
            'vertical_rate': vertical_rate,
            'squawk': '',
            'on_ground': str(on_ground).lower(),
            'session_id': session_id,
            'timestamp': dt.strftime('%Y-%m-%d %H:%M:%S')
        })

    return pd.DataFrame(records)


@convert_csv_bp.route('/convert-to-csv', methods=['POST'])
def convert_to_csv():
    """
    Convert ULG file to CSV format

    Request:
        - ulg_file: ULG file
        - session_id: Session identifier (optional, auto-generated if not provided)
        - aircraft_id: Aircraft identifier (optional, default: UMT001)

    Response:
        - CSV file download
    """
    try:
        # Validate file upload
        if 'ulg_file' not in request.files:
            return jsonify({'error': 'ULG 파일이 필요합니다'}), 400

        ulg_file = request.files['ulg_file']

        if ulg_file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다'}), 400

        if not allowed_file(ulg_file.filename):
            return jsonify({'error': 'ULG 파일만 업로드 가능합니다'}), 400

        # Get parameters
        session_id = request.form.get('session_id')
        aircraft_id = request.form.get('aircraft_id', 'UMT001')

        # Auto-generate session_id if not provided
        if not session_id:
            import time
            session_id = int(time.time())
        else:
            session_id = int(session_id)

        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            ulg_filename = secure_filename(ulg_file.filename)
            ulg_path = os.path.join(temp_dir, ulg_filename)
            ulg_file.save(ulg_path)

            # Convert to CSV
            df = convert_ulg_to_csv_data(ulg_path, session_id, aircraft_id)

            # Generate output filename
            base_name = os.path.splitext(ulg_filename)[0]
            csv_filename = f"{base_name}_{aircraft_id.lower()}.csv"
            csv_path = os.path.join(temp_dir, csv_filename)

            # Save CSV
            df.to_csv(csv_path, index=False)

            # Get statistics
            stats = {
                'records': len(df),
                'time_range': {
                    'start': df['timestamp'].iloc[0],
                    'end': df['timestamp'].iloc[-1]
                },
                'position_range': {
                    'lat_min': float(df['latitude'].min()),
                    'lat_max': float(df['latitude'].max()),
                    'lon_min': float(df['longitude'].min()),
                    'lon_max': float(df['longitude'].max())
                },
                'altitude_range': {
                    'min': int(df['altitude'].min()),
                    'max': int(df['altitude'].max())
                },
                'speed_range': {
                    'min': int(df['speed'].min()),
                    'max': int(df['speed'].max())
                }
            }

            # Send file with statistics in headers
            response = send_file(
                csv_path,
                mimetype='text/csv',
                as_attachment=True,
                download_name=csv_filename
            )

            response.headers['X-Conversion-Stats'] = str(stats)

            return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'변환 중 오류 발생: {str(e)}'}), 500


@convert_csv_bp.route('/convert-to-csv/info', methods=['POST'])
def get_conversion_info():
    """
    Get ULG file information without converting

    Request:
        - ulg_file: ULG file

    Response:
        - File information (points, time range, etc.)
    """
    try:
        if 'ulg_file' not in request.files:
            return jsonify({'error': 'ULG 파일이 필요합니다'}), 400

        ulg_file = request.files['ulg_file']

        if ulg_file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다'}), 400

        if not allowed_file(ulg_file.filename):
            return jsonify({'error': 'ULG 파일만 업로드 가능합니다'}), 400

        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.ulg', delete=False) as temp_file:
            ulg_file.save(temp_file.name)

            try:
                # Load ULG file
                ulog = ULog(temp_file.name)
                gps_data = ulog.get_dataset('vehicle_gps_position')

                total_points = len(gps_data.data['timestamp'])
                estimated_records = total_points // 10  # 1Hz sampling

                # Get time range
                first_time = datetime.utcfromtimestamp(gps_data.data['time_utc_usec'][0] / 1e6)
                last_time = datetime.utcfromtimestamp(gps_data.data['time_utc_usec'][-1] / 1e6)

                info = {
                    'filename': ulg_file.filename,
                    'total_gps_points': total_points,
                    'estimated_csv_records': estimated_records,
                    'time_range': {
                        'start': first_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'end': last_time.strftime('%Y-%m-%d %H:%M:%S')
                    },
                    'duration_seconds': (last_time - first_time).total_seconds()
                }

                return jsonify(info)

            finally:
                # Clean up temp file
                os.unlink(temp_file.name)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'파일 정보 조회 중 오류 발생: {str(e)}'}), 500
