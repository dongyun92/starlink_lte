"""
Root Cause Analysis API
Provides statistical analysis of signal loss segments
"""
from flask import Blueprint, jsonify
import pandas as pd
import numpy as np
from pathlib import Path
import config

root_cause_bp = Blueprint('root_cause', __name__)


@root_cause_bp.route('/api/3d/root-cause/<session_id>', methods=['GET'])
def get_root_cause_analysis(session_id: str):
    """
    Analyze root causes of signal loss segments

    Returns:
        {
            'cause_breakdown': {
                'lte_only': {'count': int, 'percentage': float, 'total_duration': float},
                'starlink_only': {'count': int, 'percentage': float, 'total_duration': float},
                'both': {'count': int, 'percentage': float, 'total_duration': float}
            },
            'altitude_distribution': [
                {'range': str, 'count': int, 'percentage': float, 'avg_duration': float}
            ],
            'time_distribution': [
                {'period': str, 'count': int, 'percentage': float}
            ],
            'summary': {
                'total_segments': int,
                'avg_duration': float,
                'total_impact_time': float
            }
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

        # Extract segments
        segments = []
        in_segment = False
        segment_start = None

        for i in range(len(df)):
            is_poor = poor_signal_mask.iloc[i]

            if is_poor and not in_segment:
                segment_start = i
                in_segment = True
            elif not is_poor and in_segment:
                segment_end = i - 1
                segments.append({
                    'start_idx': segment_start,
                    'end_idx': segment_end,
                    'lte_poor': poor_lte.iloc[segment_start:segment_end+1].any(),
                    'starlink_poor': poor_starlink.iloc[segment_start:segment_end+1].any(),
                    'duration': (df.iloc[segment_end]['timestamp'] - df.iloc[segment_start]['timestamp']).total_seconds(),
                    'altitude': df.iloc[segment_start:segment_end+1]['altitude'].mean() if 'altitude' in df.columns else 0
                })
                in_segment = False

        # Handle last segment
        if in_segment:
            segment_end = len(df) - 1
            segments.append({
                'start_idx': segment_start,
                'end_idx': segment_end,
                'lte_poor': poor_lte.iloc[segment_start:segment_end+1].any(),
                'starlink_poor': poor_starlink.iloc[segment_start:segment_end+1].any(),
                'duration': (df.iloc[segment_end]['timestamp'] - df.iloc[segment_start]['timestamp']).total_seconds(),
                'altitude': df.iloc[segment_start:segment_end+1]['altitude'].mean() if 'altitude' in df.columns else 0
            })

        if len(segments) == 0:
            return jsonify({
                'cause_breakdown': {
                    'lte_only': {'count': 0, 'percentage': 0, 'total_duration': 0},
                    'starlink_only': {'count': 0, 'percentage': 0, 'total_duration': 0},
                    'both': {'count': 0, 'percentage': 0, 'total_duration': 0}
                },
                'altitude_distribution': [],
                'time_distribution': [],
                'summary': {
                    'total_segments': 0,
                    'avg_duration': 0,
                    'total_impact_time': 0
                }
            })

        # 1. Cause breakdown
        lte_only = [s for s in segments if s['lte_poor'] and not s['starlink_poor']]
        starlink_only = [s for s in segments if s['starlink_poor'] and not s['lte_poor']]
        both = [s for s in segments if s['lte_poor'] and s['starlink_poor']]

        total_segments = len(segments)
        cause_breakdown = {
            'lte_only': {
                'count': len(lte_only),
                'percentage': round((len(lte_only) / total_segments) * 100, 1),
                'total_duration': round(sum(s['duration'] for s in lte_only), 2)
            },
            'starlink_only': {
                'count': len(starlink_only),
                'percentage': round((len(starlink_only) / total_segments) * 100, 1),
                'total_duration': round(sum(s['duration'] for s in starlink_only), 2)
            },
            'both': {
                'count': len(both),
                'percentage': round((len(both) / total_segments) * 100, 1),
                'total_duration': round(sum(s['duration'] for s in both), 2)
            }
        }

        # 2. Altitude distribution
        altitude_ranges = [
            (0, 50, 'Low (0-50m)'),
            (50, 100, 'Mid-Low (50-100m)'),
            (100, 150, 'Mid (100-150m)'),
            (150, 200, 'Mid-High (150-200m)'),
            (200, float('inf'), 'High (200m+)')
        ]

        altitude_distribution = []
        for min_alt, max_alt, label in altitude_ranges:
            range_segments = [s for s in segments if min_alt <= s['altitude'] < max_alt]
            if len(range_segments) > 0:
                altitude_distribution.append({
                    'range': label,
                    'count': len(range_segments),
                    'percentage': round((len(range_segments) / total_segments) * 100, 1),
                    'avg_duration': round(sum(s['duration'] for s in range_segments) / len(range_segments), 2)
                })

        # 3. Time distribution (divide flight into 10 periods)
        flight_duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
        period_duration = flight_duration / 10

        time_distribution = []
        for period_idx in range(10):
            period_start = df['timestamp'].min() + pd.Timedelta(seconds=period_idx * period_duration)
            period_end = period_start + pd.Timedelta(seconds=period_duration)

            period_segments = [
                s for s in segments
                if period_start <= df.iloc[s['start_idx']]['timestamp'] < period_end
            ]

            time_distribution.append({
                'period': f'{period_idx*10}-{(period_idx+1)*10}%',
                'count': len(period_segments),
                'percentage': round((len(period_segments) / total_segments) * 100, 1) if total_segments > 0 else 0
            })

        # 4. Summary
        total_duration = sum(s['duration'] for s in segments)
        summary = {
            'total_segments': total_segments,
            'avg_duration': round(total_duration / total_segments, 2) if total_segments > 0 else 0,
            'total_impact_time': round(total_duration, 2)
        }

        return jsonify({
            'cause_breakdown': cause_breakdown,
            'altitude_distribution': altitude_distribution,
            'time_distribution': time_distribution,
            'summary': summary
        })

    except Exception as e:
        print(f'Error in root cause analysis: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
