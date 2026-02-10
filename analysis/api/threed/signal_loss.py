"""
Signal Loss Detection API
Provides segment-level signal loss information with geospatial data
"""
from flask import Blueprint, jsonify
import pandas as pd
import numpy as np
from pathlib import Path
import config

signal_loss_bp = Blueprint('signal_loss', __name__)


@signal_loss_bp.route('/api/3d/signal-loss/<session_id>', methods=['GET'])
def get_signal_loss_segments(session_id: str):
    """
    Detect and return detailed signal loss segments with geospatial data

    Returns:
        {
            'segments': [
                {
                    'start_index': int,
                    'end_index': int,
                    'start_time': str (ISO format),
                    'end_time': str (ISO format),
                    'duration_seconds': float,
                    'center_lat': float,
                    'center_lon': float,
                    'center_altitude': float,
                    'lte_poor': bool,
                    'starlink_poor': bool,
                    'avg_lte_rsrp': float | null,
                    'avg_starlink_latency': float | null
                }
            ],
            'total_percentage': float,
            'total_segments': int
        }
    """
    try:
        # Load merged data
        merged_csv_path = config.RESULTS_FOLDER / session_id / 'merged_data.csv'
        if not merged_csv_path.exists():
            return jsonify({'error': 'Session data not found'}), 404

        df = pd.read_csv(merged_csv_path)

        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', utc=True)

        if len(df) == 0:
            return jsonify({'error': 'No data in session'}), 404

        # Detect poor signal masks
        poor_lte = pd.Series([False] * len(df))
        poor_starlink = pd.Series([False] * len(df))

        if 'lte_rsrp' in df.columns:
            poor_lte = df['lte_rsrp'] < -110

        if 'starlink_latency' in df.columns:
            poor_starlink = df['starlink_latency'] > 160

        poor_signal_mask = poor_lte | poor_starlink

        # Extract continuous segments
        segments = []
        in_segment = False
        segment_start = None

        for i in range(len(df)):
            is_poor = poor_signal_mask.iloc[i]

            if is_poor and not in_segment:
                # Start new segment
                segment_start = i
                in_segment = True
            elif not is_poor and in_segment:
                # End current segment
                segment_end = i - 1
                segment_data = extract_segment_data(df, segment_start, segment_end, poor_lte, poor_starlink)
                segments.append(segment_data)
                in_segment = False

        # Handle segment ending at last point
        if in_segment:
            segment_end = len(df) - 1
            segment_data = extract_segment_data(df, segment_start, segment_end, poor_lte, poor_starlink)
            segments.append(segment_data)

        # Calculate total statistics
        poor_count = poor_signal_mask.sum()
        total_percentage = (poor_count / len(df)) * 100 if len(df) > 0 else 0.0

        return jsonify({
            'segments': segments,
            'total_percentage': round(total_percentage, 2),
            'total_segments': len(segments)
        })

    except Exception as e:
        print(f'Error in signal loss detection: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def extract_segment_data(df: pd.DataFrame, start_idx: int, end_idx: int,
                        poor_lte: pd.Series, poor_starlink: pd.Series) -> dict:
    """Extract detailed data for a signal loss segment"""
    segment_df = df.iloc[start_idx:end_idx+1]

    # Calculate center position (median)
    center_lat = segment_df['latitude'].median()
    center_lon = segment_df['longitude'].median()
    center_altitude = segment_df['altitude'].median() if 'altitude' in segment_df.columns else 0.0

    # Calculate duration
    duration = (segment_df['timestamp'].max() - segment_df['timestamp'].min()).total_seconds()

    # Check which system caused the signal loss
    lte_poor_in_segment = poor_lte.iloc[start_idx:end_idx+1].any()
    starlink_poor_in_segment = poor_starlink.iloc[start_idx:end_idx+1].any()

    # Calculate average signal quality in segment
    avg_lte_rsrp = None
    if 'lte_rsrp' in segment_df.columns:
        lte_values = segment_df['lte_rsrp'].dropna()
        if len(lte_values) > 0:
            avg_lte_rsrp = float(lte_values.mean())

    avg_starlink_latency = None
    if 'starlink_latency' in segment_df.columns:
        starlink_values = segment_df['starlink_latency'].dropna()
        if len(starlink_values) > 0:
            avg_starlink_latency = float(starlink_values.mean())

    return {
        'start_index': int(start_idx),
        'end_index': int(end_idx),
        'start_time': segment_df['timestamp'].iloc[0].isoformat(),
        'end_time': segment_df['timestamp'].iloc[-1].isoformat(),
        'duration_seconds': round(duration, 2),
        'center_lat': round(center_lat, 6),
        'center_lon': round(center_lon, 6),
        'center_altitude': round(center_altitude, 2),
        'lte_poor': bool(lte_poor_in_segment),
        'starlink_poor': bool(starlink_poor_in_segment),
        'avg_lte_rsrp': round(avg_lte_rsrp, 2) if avg_lte_rsrp is not None else None,
        'avg_starlink_latency': round(avg_starlink_latency, 2) if avg_starlink_latency is not None else None
    }
