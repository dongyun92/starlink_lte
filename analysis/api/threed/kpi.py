"""
KPI Summary API
Provides flight statistics and signal quality summary
"""
from flask import Blueprint, jsonify
import pandas as pd
import numpy as np
from pathlib import Path
import config
from math import radians, sin, cos, sqrt, atan2

kpi_bp = Blueprint('kpi', __name__)


@kpi_bp.route('/api/3d/kpi/<session_id>', methods=['GET'])
def get_kpi_summary(session_id: str):
    """
    Calculate and return KPI summary for a session

    Returns:
        {
            'flight': {
                'duration_seconds': float,
                'distance_km': float,
                'max_altitude_m': float,
                'avg_speed_kmh': float
            },
            'lte': {
                'avg_rsrp': float,
                'quality': str,
                'color': str
            },
            'starlink': {
                'avg_latency': float,
                'quality': str,
                'color': str
            },
            'signal_loss': {
                'percentage': float,
                'segment_count': int,
                'total_duration_seconds': float
            }
        }
    """
    try:
        # Load merged data
        merged_csv_path = config.RESULTS_FOLDER / session_id / 'merged_data.csv'
        if not merged_csv_path.exists():
            return jsonify({'error': 'Session data not found'}), 404

        df = pd.read_csv(merged_csv_path)

        # Convert timestamp to datetime (handle mixed formats)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', utc=True)

        if len(df) == 0:
            return jsonify({'error': 'No data in session'}), 404

        # Flight metrics
        duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
        distance = calculate_total_distance(df)
        max_altitude = df['altitude'].max() if 'altitude' in df.columns else 0
        avg_speed = df['speed_mps'].mean() * 3.6 if 'speed_mps' in df.columns else 0  # m/s to km/h

        # LTE metrics
        lte_avg_rsrp = None
        lte_quality = None
        lte_color = '#cccccc'

        if 'lte_rsrp' in df.columns:
            lte_rsrp_values = df['lte_rsrp'].dropna()
            if len(lte_rsrp_values) > 0:
                lte_avg_rsrp = float(lte_rsrp_values.mean())
                lte_quality = classify_lte_quality(lte_avg_rsrp)
                lte_color = quality_to_color(lte_quality)

        # Starlink metrics
        starlink_avg_latency = None
        starlink_quality = None
        starlink_color = '#cccccc'

        if 'starlink_latency' in df.columns:
            starlink_latency_values = df['starlink_latency'].dropna()
            if len(starlink_latency_values) > 0:
                starlink_avg_latency = float(starlink_latency_values.mean())
                starlink_quality = classify_starlink_quality(starlink_avg_latency)
                starlink_color = quality_to_color(starlink_quality)

        # Signal loss detection
        signal_loss_info = detect_signal_loss_segments(df)

        return jsonify({
            'flight': {
                'duration_seconds': round(duration, 2),
                'distance_km': round(distance, 2),
                'max_altitude_m': round(max_altitude, 2),
                'avg_speed_kmh': round(avg_speed, 2)
            },
            'lte': {
                'avg_rsrp': round(lte_avg_rsrp, 2) if lte_avg_rsrp else None,
                'quality': lte_quality,
                'color': lte_color
            },
            'starlink': {
                'avg_latency': round(starlink_avg_latency, 2) if starlink_avg_latency else None,
                'quality': starlink_quality,
                'color': starlink_color
            },
            'signal_loss': signal_loss_info
        })

    except Exception as e:
        print(f'Error in KPI summary: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def calculate_total_distance(df: pd.DataFrame) -> float:
    """Calculate total flight distance in kilometers using Haversine formula"""
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        return 0.0

    total_distance = 0.0
    for i in range(1, len(df)):
        try:
            lat1 = radians(df.iloc[i-1]['latitude'])
            lon1 = radians(df.iloc[i-1]['longitude'])
            lat2 = radians(df.iloc[i]['latitude'])
            lon2 = radians(df.iloc[i]['longitude'])

            dlat = lat2 - lat1
            dlon = lon2 - lon1

            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))

            total_distance += 6371 * c  # Earth radius = 6371 km
        except:
            continue

    return total_distance


def classify_lte_quality(rsrp: float) -> str:
    """Classify LTE signal quality based on RSRP value"""
    if rsrp is None or np.isnan(rsrp):
        return None

    if rsrp >= -70:
        return 'excellent'
    elif rsrp >= -85:
        return 'good'
    elif rsrp >= -100:
        return 'fair'
    elif rsrp >= -110:
        return 'poor'
    else:
        return 'very_poor'


def classify_starlink_quality(latency: float) -> str:
    """Classify Starlink signal quality based on latency value"""
    if latency is None or np.isnan(latency):
        return None

    if latency <= 40:
        return 'excellent'
    elif latency <= 80:
        return 'good'
    elif latency <= 120:
        return 'fair'
    elif latency <= 160:
        return 'poor'
    else:
        return 'very_poor'


def quality_to_color(quality: str) -> str:
    """Map quality level to hex color"""
    color_map = {
        'excellent': '#1a9850',  # Green
        'good': '#91cf60',       # Light green
        'fair': '#fee08b',       # Yellow
        'poor': '#fc8d59',       # Orange
        'very_poor': '#d73027'   # Red
    }
    return color_map.get(quality, '#cccccc')


def detect_signal_loss_segments(df: pd.DataFrame) -> dict:
    """Detect segments with poor signal quality"""
    # Define poor signal thresholds
    poor_lte = pd.Series([False] * len(df))
    poor_starlink = pd.Series([False] * len(df))

    if 'lte_rsrp' in df.columns:
        poor_lte = df['lte_rsrp'] < -110

    if 'starlink_latency' in df.columns:
        poor_starlink = df['starlink_latency'] > 160

    poor_signal_mask = poor_lte | poor_starlink
    poor_count = poor_signal_mask.sum()

    if poor_count == 0:
        return {
            'percentage': 0.0,
            'segment_count': 0,
            'total_duration_seconds': 0.0
        }

    # Count continuous segments
    segment_count = 0
    in_segment = False

    for is_poor in poor_signal_mask:
        if is_poor and not in_segment:
            segment_count += 1
            in_segment = True
        elif not is_poor:
            in_segment = False

    # Calculate total duration (assuming 1Hz sampling)
    total_duration = float(poor_count)

    return {
        'percentage': round((poor_count / len(df)) * 100, 2),
        'segment_count': int(segment_count),
        'total_duration_seconds': round(total_duration, 2)
    }
