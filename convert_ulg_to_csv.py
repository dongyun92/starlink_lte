#!/usr/bin/env python3
"""
ULG to CSV Converter for UAO Database Import
Converts PX4 ULG flight logs to aviation database CSV format
"""

from pyulog import ULog
import pandas as pd
from datetime import datetime
import sys
import os
import math

def convert_ulg_to_csv(ulg_path, session_id, output_csv):
    """
    Convert ULG file to CSV format for UAO database

    Args:
        ulg_path: Path to ULG file
        session_id: Session identifier (1 for sortie_1, 2 for sortie_2)
        output_csv: Output CSV file path
    """
    print(f"\n{'='*60}")
    print(f"🔄 Converting: {os.path.basename(ulg_path)}")
    print(f"📊 Session ID: {session_id}")
    print(f"{'='*60}\n")

    try:
        # Load ULG file
        print("📂 Loading ULG file...")
        ulog = ULog(ulg_path)

        # Extract GPS data
        print("🛰️  Extracting GPS data from vehicle_gps_position topic...")
        gps_data = ulog.get_dataset('vehicle_gps_position')

        records = []
        total_points = len(gps_data.data['timestamp'])
        print(f"📍 Total GPS points: {total_points}")

        # Determine sampling rate (assume 10Hz, sample every 10th point for 1Hz)
        # Adjust this if your data has different frequency
        sample_interval = 10

        print(f"⏱️  Sampling: 1 point per second (every {sample_interval}th point)")

        for i in range(0, total_points, sample_interval):
            # Timestamp conversion (use time_utc_usec for actual UTC time)
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

            # Heading (cog_rad is in radians, heading is in degrees)
            # Use heading field directly if available, otherwise convert cog_rad
            if 'heading' in gps_data.data and not math.isnan(gps_data.data['heading'][i]):
                heading_deg = gps_data.data['heading'][i]
            else:
                cog_rad = gps_data.data['cog_rad'][i]
                if not math.isnan(cog_rad):
                    heading_deg = cog_rad * 57.2958  # radians to degrees
                else:
                    heading_deg = 0  # Default to 0 if no heading available
            heading = round(heading_deg) % 360  # 0-360 range

            # Vertical rate (vel_d_m_s is down velocity in m/s, negative for climb)
            vel_d_ms = gps_data.data['vel_d_m_s'][i]
            vertical_rate = round(-vel_d_ms * 196.85)  # m/s → feet/min (negative because down is positive)

            # On ground determination
            on_ground = altitude < 100

            records.append({
                'hexid': 'UMT001',
                'callsign': 'UMT001',
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

        # Create DataFrame and save to CSV
        print(f"\n💾 Creating CSV with {len(records)} records...")
        df = pd.DataFrame(records)
        df.to_csv(output_csv, index=False)

        print(f"✅ Conversion complete!")
        print(f"📄 Output: {output_csv}")
        print(f"📊 Records: {len(records)}")
        print(f"⏱️  Time range: {records[0]['timestamp']} → {records[-1]['timestamp']}")
        print(f"🗺️  Position range:")
        print(f"   Latitude:  {df['latitude'].min():.6f} → {df['latitude'].max():.6f}")
        print(f"   Longitude: {df['longitude'].min():.6f} → {df['longitude'].max():.6f}")
        print(f"✈️  Altitude range: {df['altitude'].min()} ft → {df['altitude'].max()} ft")
        print(f"🚀 Speed range: {df['speed'].min()} kt → {df['speed'].max()} kt")

        return True

    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🛰️  ULG to CSV Converter for UAO Database")
    print("="*60)

    # File paths
    base_path = '/Users/dykim/dev/starlink/data_save'
    output_path = '/Users/dykim/dev/UAO'

    conversions = [
        {
            'input': f'{base_path}/sortie_1.ulg',
            'session_id': 1,
            'output': f'{output_path}/sortie_1_umt001.csv'
        },
        {
            'input': f'{base_path}/sortie_2.ulg',
            'session_id': 2,
            'output': f'{output_path}/sortie_2_umt001.csv'
        }
    ]

    success_count = 0

    for conv in conversions:
        if convert_ulg_to_csv(conv['input'], conv['session_id'], conv['output']):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"🎉 Conversion Summary: {success_count}/{len(conversions)} successful")
    print(f"{'='*60}\n")

    if success_count == len(conversions):
        print("✅ All conversions completed successfully!")
        print(f"\n📁 Output files:")
        for conv in conversions:
            print(f"   - {conv['output']}")
        print(f"\n📝 Next step: Import to PostgreSQL database")
        print(f"   Use the COPY commands from ULG_TO_CSV_REQUEST.md")
    else:
        print("⚠️  Some conversions failed. Check errors above.")
        sys.exit(1)
