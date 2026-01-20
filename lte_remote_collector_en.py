#!/usr/bin/env python3
"""
LTE Remote Data Collector for Aircraft
Collects communication quality data from Quectel EC25/EC21 LTE module
"""

from flask import Flask, jsonify, request, send_file
import threading
import time
import os
import csv
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import random
import serial
import re

app = Flask(__name__)

# Configuration
CONTROL_PORT = 8897
DATA_DIR = './lte-data'
CSV_PREFIX = 'lte_data'
CSV_ROTATION_MINUTES = 10
CSV_MAX_SIZE_MB = 30
SERIAL_PORT = '/dev/ttyUSB0'
SERIAL_BAUDRATE = 115200
COLLECTION_INTERVAL = 5  # seconds

class CollectorState(Enum):
    IDLE = "idle"
    COLLECTING = "collecting"
    ERROR = "error"

@dataclass
class LTEStatus:
    timestamp: str
    rssi: int  # Received Signal Strength Indicator (dBm)
    ber: float  # Bit Error Rate (%)
    network_type: str  # LTE/3G/2G
    network_operator: str
    cell_id: str
    lac: str  # Location Area Code  
    registration_status: str
    connection_state: str
    rx_bytes: int  # Received bytes
    tx_bytes: int  # Transmitted bytes
    rsrp: int  # Reference Signal Received Power (dBm) - LTE only
    rsrq: int  # Reference Signal Received Quality (dB) - LTE only
    sinr: int  # Signal to Interference plus Noise Ratio (dB) - LTE only

class LTEModule:
    def __init__(self, port=SERIAL_PORT, baudrate=SERIAL_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        
    def connect(self):
        """Connect to LTE module via serial port"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                rtscts=True,
                dsrdtr=True
            )
            self.connected = True
            print(f"[INFO] Connected to LTE module on {self.port}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to connect to LTE module: {e}")
            self.connected = False
            return False
    
    def send_at_command(self, command, wait_time=1):
        """Send AT command and get response"""
        if not self.connected or not self.ser:
            return None
        
        try:
            self.ser.write(f"{command}\r\n".encode())
            time.sleep(wait_time)
            response = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
            return response.strip()
        except Exception as e:
            print(f"[ERROR] AT command failed: {e}")
            return None
    
    def get_signal_quality(self):
        """Get signal quality (RSSI and BER) using AT+CSQ"""
        response = self.send_at_command("AT+CSQ")
        if response and "+CSQ:" in response:
            match = re.search(r"\+CSQ:\s*(\d+),(\d+)", response)
            if match:
                rssi_raw = int(match.group(1))
                ber_raw = int(match.group(2))
                
                # Convert RSSI (0-31 to dBm)
                if rssi_raw == 99:
                    rssi = -999  # No signal
                else:
                    rssi = -113 + (rssi_raw * 2)
                
                # Convert BER (0-7, 99 = unknown)
                ber = ber_raw if ber_raw != 99 else 0
                
                return rssi, ber
        return -999, 0
    
    def get_network_info(self):
        """Get network information using AT+QNWINFO"""
        response = self.send_at_command("AT+QNWINFO")
        if response and "+QNWINFO:" in response:
            match = re.search(r'\+QNWINFO:\s*"([^"]+)","([^"]+)","([^"]+)",(\d+)', response)
            if match:
                return {
                    'type': match.group(1),  # FDD LTE, TDD LTE, etc.
                    'operator': match.group(2),
                    'band': match.group(3),
                    'channel': match.group(4)
                }
        return {'type': 'Unknown', 'operator': 'Unknown', 'band': '0', 'channel': '0'}
    
    def get_registration_status(self):
        """Get network registration status using AT+CREG and AT+CEREG"""
        # Check 2G/3G registration
        response = self.send_at_command("AT+CREG?")
        creg_status = "0"
        if response and "+CREG:" in response:
            match = re.search(r"\+CREG:\s*\d+,(\d+)", response)
            if match:
                creg_status = match.group(1)
        
        # Check LTE registration  
        response = self.send_at_command("AT+CEREG?")
        cereg_status = "0"
        if response and "+CEREG:" in response:
            match = re.search(r"\+CEREG:\s*\d+,(\d+)", response)
            if match:
                cereg_status = match.group(1)
        
        # Status codes: 1=registered home, 5=registered roaming
        if cereg_status in ["1", "5"]:
            return "Registered (LTE)"
        elif creg_status in ["1", "5"]:
            return "Registered (2G/3G)"
        else:
            return "Not Registered"
    
    def get_data_usage(self):
        """Get data usage statistics using AT+QGDCNT"""
        response = self.send_at_command("AT+QGDCNT?")
        if response and "+QGDCNT:" in response:
            match = re.search(r"\+QGDCNT:\s*(\d+),(\d+)", response)
            if match:
                tx_bytes = int(match.group(1))
                rx_bytes = int(match.group(2))
                return rx_bytes, tx_bytes
        return 0, 0
    
    def get_cell_info(self):
        """Get cell ID and LAC using AT+QENG"""
        response = self.send_at_command("AT+QENG=\"servingcell\"", wait_time=2)
        if response and "+QENG:" in response:
            # Parse serving cell info for cell_id and lac
            lines = response.split('\n')
            for line in lines:
                if "LTE" in line or "servingcell" in line:
                    parts = line.split(',')
                    if len(parts) > 10:
                        try:
                            cell_id = parts[8] if len(parts) > 8 else "0"
                            lac = parts[9] if len(parts) > 9 else "0"
                            return cell_id.strip(), lac.strip()
                        except:
                            pass
        return "0", "0"
    
    def get_extended_signal_info(self):
        """Get extended signal information (RSRP, RSRQ, SINR)"""
        info = {
            'rsrp': -999,  # Reference Signal Received Power
            'rsrq': -999,  # Reference Signal Received Quality
            'sinr': -999   # Signal to Interference plus Noise Ratio
        }
        
        # Get RSRP
        response = self.send_at_command("AT+QRSRP")
        if response and "+QRSRP:" in response:
            match = re.search(r"\+QRSRP:\s*([-\d]+)", response)
            if match:
                info['rsrp'] = int(match.group(1))
        
        # Get RSRQ
        response = self.send_at_command("AT+QRSRQ")
        if response and "+QRSRQ:" in response:
            match = re.search(r"\+QRSRQ:\s*([-\d]+)", response)
            if match:
                info['rsrq'] = int(match.group(1))
                
        # Get SINR
        response = self.send_at_command("AT+QSINR")
        if response and "+QSINR:" in response:
            match = re.search(r"\+QSINR:\s*([-\d]+)", response)
            if match:
                info['sinr'] = int(match.group(1))
                
        return info
    
    def get_operator_name(self):
        """Get current operator name using AT+COPS"""
        response = self.send_at_command("AT+COPS?")
        if response and "+COPS:" in response:
            match = re.search(r'\+COPS:\s*\d+,\d+,"([^"]+)"', response)
            if match:
                return match.group(1)
        return "Unknown"
    
    def get_imei(self):
        """Get IMEI number"""
        response = self.send_at_command("AT+CGSN")
        if response:
            # IMEI is usually 15 digits
            match = re.search(r"(\d{15})", response)
            if match:
                return match.group(1)
        return "Unknown"
    
    def get_sim_info(self):
        """Get SIM card information"""
        info = {'imsi': 'Unknown', 'iccid': 'Unknown'}
        
        # Get IMSI
        response = self.send_at_command("AT+CIMI")
        if response:
            match = re.search(r"(\d{15})", response)
            if match:
                info['imsi'] = match.group(1)
        
        # Get ICCID  
        response = self.send_at_command("AT+CCID")
        if response:
            match = re.search(r"(\d{19,20})", response)
            if match:
                info['iccid'] = match.group(1)
                
        return info
    
    def close(self):
        """Close serial connection"""
        if self.ser:
            self.ser.close()
            self.connected = False
            print("[INFO] Disconnected from LTE module")

class LTEDataCollector:
    def __init__(self):
        self.current_state = CollectorState.IDLE
        self.collection_thread = None
        self.stop_event = threading.Event()
        self.data_points = []
        self.total_points_collected = 0
        self.start_time = None
        self.current_csv_file = None
        self.csv_writer = None
        self.csv_file_handle = None
        self.last_rotation_time = time.time()
        self.lte_module = LTEModule()
        self.mock_mode = False
        
        # Create data directory
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Try to connect to LTE module
        if not self.lte_module.connect():
            print("[WARNING] LTE module not available, using mock data")
            self.mock_mode = True
    
    def generate_mock_lte_data(self) -> LTEStatus:
        """Generate mock LTE data for testing"""
        current_time = datetime.utcnow()
        
        # Simulate realistic LTE values
        network_type = random.choice(['LTE', '3G', '2G'])
        rssi = random.randint(-110, -60)  # dBm
        ber = random.uniform(0, 2)  # Bit error rate
        
        # LTE specific values
        if network_type == 'LTE':
            rsrp = random.randint(-140, -80)  # Reference Signal Received Power
            rsrq = random.randint(-20, -3)    # Reference Signal Received Quality
            sinr = random.randint(-20, 30)    # Signal to Interference plus Noise Ratio
        else:
            rsrp = -999  # Not available for 2G/3G
            rsrq = -999
            sinr = -999
        
        return LTEStatus(
            timestamp=current_time.isoformat() + 'Z',
            rssi=rssi,
            ber=round(ber, 2),
            network_type=network_type,
            network_operator='TestOperator',
            cell_id=f"{random.randint(10000, 99999)}",
            lac=f"{random.randint(1000, 9999)}",
            registration_status='Registered',
            connection_state='Connected',
            rx_bytes=random.randint(1000000, 10000000),
            tx_bytes=random.randint(500000, 5000000),
            rsrp=rsrp,
            rsrq=rsrq,
            sinr=sinr
        )
    
    def collect_lte_data(self) -> LTEStatus:
        """Collect real LTE data from module"""
        current_time = datetime.utcnow()
        
        # For testing without hardware, use mock mode
        if self.mock_mode:
            print("[INFO] Mock mode: Generating test data")
            return self.generate_mock_lte_data()
        
        print("[INFO] Collecting real LTE data from module...")
        
        # Get signal quality
        rssi, ber = self.lte_module.get_signal_quality()
        
        # Get network info
        network_info = self.lte_module.get_network_info()
        
        # Get operator name
        operator = self.lte_module.get_operator_name()
        if operator == "Unknown" and network_info['operator'] != "Unknown":
            operator = network_info['operator']
        
        # Get registration status
        reg_status = self.lte_module.get_registration_status()
        
        # Get cell info
        cell_id, lac = self.lte_module.get_cell_info()
        
        # Get data usage
        rx_bytes, tx_bytes = self.lte_module.get_data_usage()
        
        # Get extended signal info (optional - may not be available on all modules)
        try:
            ext_signal = self.lte_module.get_extended_signal_info()
            print(f"[DEBUG] Extended Signal: RSRP={ext_signal['rsrp']}, RSRQ={ext_signal['rsrq']}, SINR={ext_signal['sinr']}")
        except:
            ext_signal = {'rsrp': -999, 'rsrq': -999, 'sinr': -999}
        
        # Determine network type from network info
        network_type = "Unknown"
        if "LTE" in network_info['type'].upper():
            network_type = "LTE"
        elif "WCDMA" in network_info['type'].upper() or "UMTS" in network_info['type'].upper():
            network_type = "3G"
        elif "GSM" in network_info['type'].upper() or "EDGE" in network_info['type'].upper():
            network_type = "2G"
        elif network_info['type'] != "Unknown":
            network_type = network_info['type']
        
        # Connection state based on registration and signal
        connection_state = "Disconnected"
        if "Registered" in reg_status and rssi > -999 and rssi != -113:
            connection_state = "Connected"
        
        # Log collected data
        print(f"[DATA] RSSI={rssi} dBm, BER={ber}, Type={network_type}, Operator={operator}")
        print(f"[DATA] Cell={cell_id}, LAC={lac}, Status={reg_status}, State={connection_state}")
        print(f"[DATA] RX={rx_bytes} bytes, TX={tx_bytes} bytes")
        
        return LTEStatus(
            timestamp=current_time.isoformat() + 'Z',
            rssi=rssi,
            ber=ber,
            network_type=network_type,
            network_operator=operator,
            cell_id=cell_id,
            lac=lac,
            registration_status=reg_status,
            connection_state=connection_state,
            rx_bytes=rx_bytes,
            tx_bytes=tx_bytes,
            rsrp=ext_signal['rsrp'],  # LTE specific signal quality
            rsrq=ext_signal['rsrq'],  # LTE specific signal quality  
            sinr=ext_signal['sinr']   # LTE specific signal quality
        )
    
    def rotate_csv_if_needed(self):
        """Rotate CSV file if time or size limit reached"""
        current_time = time.time()
        
        should_rotate = False
        
        # Check time-based rotation
        if current_time - self.last_rotation_time > (CSV_ROTATION_MINUTES * 60):
            should_rotate = True
            print(f"[INFO] Rotating CSV file (time limit: {CSV_ROTATION_MINUTES} minutes)")
        
        # Check size-based rotation
        if self.current_csv_file and os.path.exists(self.current_csv_file):
            file_size_mb = os.path.getsize(self.current_csv_file) / (1024 * 1024)
            if file_size_mb > CSV_MAX_SIZE_MB:
                should_rotate = True
                print(f"[INFO] Rotating CSV file (size: {file_size_mb:.2f} MB)")
        
        if should_rotate:
            self.close_csv()
            self.last_rotation_time = current_time
    
    def close_csv(self):
        """Close current CSV file"""
        if self.csv_file_handle:
            self.csv_file_handle.close()
            self.csv_file_handle = None
            self.csv_writer = None
            print(f"[INFO] Closed CSV file: {self.current_csv_file}")
    
    def create_new_csv(self):
        """Create new CSV file with timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        self.current_csv_file = os.path.join(DATA_DIR, f'{CSV_PREFIX}_{timestamp}.csv')
        
        self.csv_file_handle = open(self.current_csv_file, 'w', newline='')
        
        # Get field names from dataclass
        fieldnames = [field.name for field in LTEStatus.__dataclass_fields__.values()]
        
        self.csv_writer = csv.DictWriter(self.csv_file_handle, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        
        print(f"[INFO] Created new CSV file: {self.current_csv_file}")
    
    def collection_worker(self):
        """Background worker for data collection"""
        print("[INFO] LTE data collection started")
        
        while not self.stop_event.is_set():
            try:
                # Check CSV rotation
                if self.csv_writer is None:
                    self.create_new_csv()
                else:
                    self.rotate_csv_if_needed()
                
                # Collect data
                data = self.collect_lte_data()
                
                # Write to CSV
                if self.csv_writer:
                    self.csv_writer.writerow(asdict(data))
                    self.csv_file_handle.flush()
                
                # Store in memory (limited)
                self.data_points.append(data)
                if len(self.data_points) > 100:
                    self.data_points.pop(0)
                
                self.total_points_collected += 1
                
                # Sleep
                time.sleep(COLLECTION_INTERVAL)
                
            except Exception as e:
                print(f"[ERROR] Collection error: {e}")
                self.current_state = CollectorState.ERROR
                time.sleep(5)
    
    def start_collection(self):
        """Start data collection"""
        if self.current_state == CollectorState.COLLECTING:
            return False, "Already collecting"
        
        self.current_state = CollectorState.COLLECTING
        self.start_time = datetime.utcnow()
        self.stop_event.clear()
        
        self.collection_thread = threading.Thread(target=self.collection_worker, daemon=True)
        self.collection_thread.start()
        
        return True, "Collection started"
    
    def stop_collection(self):
        """Stop data collection"""
        if self.current_state != CollectorState.COLLECTING:
            return False, "Not collecting"
        
        self.stop_event.set()
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        
        self.close_csv()
        self.current_state = CollectorState.IDLE
        
        return True, "Collection stopped"
    
    def get_status(self):
        """Get current collector status"""
        return {
            'state': self.current_state.value,
            'total_points': self.total_points_collected,
            'current_file': self.current_csv_file,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'mock_mode': self.mock_mode,
            'serial_port': SERIAL_PORT,
            'collection_interval': COLLECTION_INTERVAL
        }
    
    def get_recent_data(self, count=10):
        """Get recent data points"""
        return self.data_points[-count:] if self.data_points else []

# Create global collector instance
collector = LTEDataCollector()

# API Routes
@app.route('/status')
def get_status():
    """Get collector status"""
    return jsonify(collector.get_status())

@app.route('/start', methods=['POST'])
def start_collection():
    """Start data collection"""
    success, message = collector.start_collection()
    return jsonify({'success': success, 'message': message})

@app.route('/stop', methods=['POST'])
def stop_collection():
    """Stop data collection"""
    success, message = collector.stop_collection()
    return jsonify({'success': success, 'message': message})

@app.route('/data/recent')
def get_recent_data():
    """Get recent collected data"""
    count = request.args.get('count', 10, type=int)
    data = collector.get_recent_data(count)
    return jsonify([asdict(d) for d in data])

@app.route('/data/files')
def list_data_files():
    """List available CSV files"""
    files = []
    for filename in os.listdir(DATA_DIR):
        if filename.startswith(CSV_PREFIX) and filename.endswith('.csv'):
            filepath = os.path.join(DATA_DIR, filename)
            files.append({
                'name': filename,
                'size': os.path.getsize(filepath),
                'modified': os.path.getmtime(filepath)
            })
    return jsonify(sorted(files, key=lambda x: x['modified'], reverse=True))

@app.route('/data/download/<filename>')
def download_file(filename):
    """Download specific CSV file"""
    if not filename.startswith(CSV_PREFIX) or not filename.endswith('.csv'):
        return jsonify({'error': 'Invalid filename'}), 400
    
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(filepath, as_attachment=True)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'lte-collector'})

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='LTE Remote Data Collector')
    parser.add_argument('--data-dir', default=DATA_DIR, help='Data directory')
    parser.add_argument('--control-port', type=int, default=CONTROL_PORT, help='Control API port')
    parser.add_argument('--serial-port', default=SERIAL_PORT, help='Serial port for LTE module')
    parser.add_argument('--interval', type=int, default=COLLECTION_INTERVAL, help='Collection interval in seconds')
    
    args = parser.parse_args()
    
    # Update configuration
    DATA_DIR = args.data_dir
    CONTROL_PORT = args.control_port
    SERIAL_PORT = args.serial_port
    COLLECTION_INTERVAL = args.interval
    
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print("=" * 60)
    print("LTE REMOTE DATA COLLECTOR")
    print("=" * 60)
    print(f"Control Port: {CONTROL_PORT}")
    print(f"Data Directory: {DATA_DIR}")
    print(f"Serial Port: {SERIAL_PORT}")
    print(f"Collection Interval: {COLLECTION_INTERVAL} seconds")
    print("=" * 60)
    
    # Auto-start collection
    collector.start_collection()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=CONTROL_PORT, debug=False)