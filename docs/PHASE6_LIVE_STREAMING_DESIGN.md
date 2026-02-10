# Phase 6: Live Streaming Integration - Detailed Design

**Priority**: HIGH (사용자 필수 요구사항)
**Complexity**: MEDIUM (기존 엔드포인트 활용)
**Duration**: 3-4 days

---

## 🎯 Overview

기존 실시간 모니터링 시스템 (VPN 엔드포인트)을 3D 시각화에 통합하여 드론의 실시간 비행 + 신호 품질 모니터링 기능 제공.

### Existing Infrastructure

**LTE Monitoring Endpoint**:
- URL: `http://100.119.109.7:8079/`
- Protocol: HTTP (polling) or WebSocket
- Data: Real-time LTE signal quality (RSRP, RSSI, SINR, etc.)

**Starlink Monitoring Endpoint**:
- URL: `http://100.66.190.1:8080/`
- Protocol: HTTP (polling) or WebSocket
- Data: Real-time Starlink quality (SNR, Latency, Throughput, etc.)

---

## 📡 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Drone (in flight)                          │
│  ├─ GPS Module                                              │
│  ├─ LTE Modem                                               │
│  └─ Starlink Terminal                                       │
└─────────────────────────────────────────────────────────────┘
                    ↓ VPN Stream
┌─────────────────────────────────────────────────────────────┐
│              Existing Monitoring Servers                    │
│  ├─ LTE Server: 100.119.109.7:8079                         │
│  └─ Starlink Server: 100.66.190.1:8080                     │
└─────────────────────────────────────────────────────────────┘
                    ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│         Flask Backend (Proxy + Normalizer)                  │
│  /api/live/lte-stream       → Proxy to LTE server          │
│  /api/live/starlink-stream  → Proxy to Starlink server     │
│  /api/live/combined-stream  → Merged real-time data        │
└─────────────────────────────────────────────────────────────┘
                    ↓ WebSocket (Socket.IO)
┌─────────────────────────────────────────────────────────────┐
│         Frontend (React + Cesium)                           │
│  ├─ Live Drone Entity (3D)                                  │
│  ├─ Real-time KPI Dashboard                                 │
│  ├─ Live Signal Loss Alerts                                 │
│  └─ Recording/Playback Toggle                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Backend Implementation

### Step 1: Discover Existing API Format

먼저 기존 엔드포인트의 데이터 형식을 파악해야 합니다.

**Test Script**: `analysis/scripts/test_vpn_endpoints.py`

```python
"""
Test script to discover existing monitoring API format
"""
import requests
import json
from datetime import datetime

def test_lte_endpoint():
    """Test LTE monitoring endpoint"""
    try:
        response = requests.get('http://100.119.109.7:8079/', timeout=5)
        print("=== LTE Endpoint Response ===")
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Response Body:\n{response.text[:500]}")  # First 500 chars

        # Try to parse as JSON
        try:
            data = response.json()
            print(f"\nJSON Structure:")
            print(json.dumps(data, indent=2)[:500])
        except:
            print("Not JSON format")

    except Exception as e:
        print(f"Error connecting to LTE endpoint: {e}")

def test_starlink_endpoint():
    """Test Starlink monitoring endpoint"""
    try:
        response = requests.get('http://100.66.190.1:8080/', timeout=5)
        print("\n=== Starlink Endpoint Response ===")
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Response Body:\n{response.text[:500]}")

        try:
            data = response.json()
            print(f"\nJSON Structure:")
            print(json.dumps(data, indent=2)[:500])
        except:
            print("Not JSON format")

    except Exception as e:
        print(f"Error connecting to Starlink endpoint: {e}")

if __name__ == '__main__':
    test_lte_endpoint()
    test_starlink_endpoint()
```

**Run**: `python3 analysis/scripts/test_vpn_endpoints.py`

### Step 2: Backend Proxy API

**File**: `analysis/api/live/stream.py`

```python
"""
Live Streaming API - Proxy to VPN monitoring endpoints
"""
from flask import Blueprint, jsonify, Response
from flask_socketio import SocketIO, emit
import requests
import json
from datetime import datetime
from threading import Thread
import time

live_bp = Blueprint('live', __name__)
socketio = SocketIO(cors_allowed_origins="*")  # Initialize in app.py

# VPN endpoint configuration
LTE_ENDPOINT = 'http://100.119.109.7:8079/'
STARLINK_ENDPOINT = 'http://100.66.190.1:8080/'

# Streaming state
streaming_active = False
streaming_thread = None


@live_bp.route('/api/live/status', methods=['GET'])
def get_streaming_status():
    """Check if live streaming is available"""
    try:
        # Test connectivity to both endpoints
        lte_ok = test_endpoint(LTE_ENDPOINT)
        starlink_ok = test_endpoint(STARLINK_ENDPOINT)

        return jsonify({
            'available': lte_ok or starlink_ok,
            'endpoints': {
                'lte': {
                    'url': LTE_ENDPOINT,
                    'status': 'online' if lte_ok else 'offline'
                },
                'starlink': {
                    'url': STARLINK_ENDPOINT,
                    'status': 'online' if starlink_ok else 'offline'
                }
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def test_endpoint(url: str, timeout: int = 2) -> bool:
    """Test if endpoint is reachable"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except:
        return False


@live_bp.route('/api/live/lte-current', methods=['GET'])
def get_lte_current():
    """Get current LTE data (single poll)"""
    try:
        response = requests.get(LTE_ENDPOINT, timeout=5)
        data = response.json()

        # Normalize data format (adjust based on actual API response)
        normalized = normalize_lte_data(data)
        return jsonify(normalized)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@live_bp.route('/api/live/starlink-current', methods=['GET'])
def get_starlink_current():
    """Get current Starlink data (single poll)"""
    try:
        response = requests.get(STARLINK_ENDPOINT, timeout=5)
        data = response.json()

        # Normalize data format
        normalized = normalize_starlink_data(data)
        return jsonify(normalized)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def normalize_lte_data(raw_data: dict) -> dict:
    """
    Normalize LTE data to consistent format

    Adjust this function based on actual API response format
    """
    # Example normalization (adjust keys based on real API)
    return {
        'timestamp': raw_data.get('timestamp', datetime.utcnow().isoformat()),
        'rsrp': raw_data.get('rsrp') or raw_data.get('lte_rsrp'),
        'rssi': raw_data.get('rssi') or raw_data.get('lte_rssi'),
        'sinr': raw_data.get('sinr') or raw_data.get('lte_sinr'),
        'rsrq': raw_data.get('rsrq') or raw_data.get('lte_rsrq'),
        'latitude': raw_data.get('lat') or raw_data.get('latitude'),
        'longitude': raw_data.get('lon') or raw_data.get('longitude'),
        'altitude': raw_data.get('alt') or raw_data.get('altitude'),
        'quality': classify_lte_quality(raw_data.get('rsrp', -999))
    }


def normalize_starlink_data(raw_data: dict) -> dict:
    """Normalize Starlink data to consistent format"""
    return {
        'timestamp': raw_data.get('timestamp', datetime.utcnow().isoformat()),
        'snr': raw_data.get('snr') or raw_data.get('starlink_snr'),
        'latency': raw_data.get('latency') or raw_data.get('ping_latency_ms'),
        'throughput_down': raw_data.get('throughput_down') or raw_data.get('downlink_throughput_bps'),
        'throughput_up': raw_data.get('throughput_up') or raw_data.get('uplink_throughput_bps'),
        'packet_loss': raw_data.get('packet_loss') or raw_data.get('pop_ping_drop_rate'),
        'latitude': raw_data.get('lat') or raw_data.get('latitude'),
        'longitude': raw_data.get('lon') or raw_data.get('longitude'),
        'altitude': raw_data.get('alt') or raw_data.get('altitude'),
        'quality': classify_starlink_quality(raw_data.get('latency', 999))
    }


def classify_lte_quality(rsrp: float) -> str:
    """Classify LTE quality based on RSRP"""
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
    """Classify Starlink quality based on latency"""
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


# WebSocket Event Handlers

@socketio.on('connect')
def handle_connect():
    """Client connected to WebSocket"""
    print(f'Client connected: {request.sid}')
    emit('connected', {'status': 'ok'})


@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnected from WebSocket"""
    print(f'Client disconnected: {request.sid}')


@socketio.on('start_streaming')
def handle_start_streaming(data):
    """Start live data streaming"""
    global streaming_active, streaming_thread

    if streaming_active:
        emit('streaming_status', {'status': 'already_active'})
        return

    streaming_active = True
    streaming_thread = Thread(target=stream_worker)
    streaming_thread.daemon = True
    streaming_thread.start()

    emit('streaming_status', {'status': 'started'})


@socketio.on('stop_streaming')
def handle_stop_streaming():
    """Stop live data streaming"""
    global streaming_active
    streaming_active = False
    emit('streaming_status', {'status': 'stopped'})


def stream_worker():
    """Background thread for continuous data streaming"""
    global streaming_active

    while streaming_active:
        try:
            # Fetch LTE data
            try:
                lte_response = requests.get(LTE_ENDPOINT, timeout=2)
                lte_data = normalize_lte_data(lte_response.json())
            except:
                lte_data = None

            # Fetch Starlink data
            try:
                starlink_response = requests.get(STARLINK_ENDPOINT, timeout=2)
                starlink_data = normalize_starlink_data(starlink_response.json())
            except:
                starlink_data = None

            # Emit combined data
            if lte_data or starlink_data:
                socketio.emit('live_data', {
                    'lte': lte_data,
                    'starlink': starlink_data,
                    'timestamp': datetime.utcnow().isoformat()
                })

            # Poll every 1 second
            time.sleep(1)

        except Exception as e:
            print(f'Streaming error: {e}')
            socketio.emit('streaming_error', {'error': str(e)})
            streaming_active = False
```

**Register in `analysis/app.py`**:

```python
from api.live.stream import live_bp, socketio

# Register blueprint
app.register_blueprint(live_bp)

# Initialize SocketIO
socketio.init_app(app)

# Run with SocketIO
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5002, debug=True)
```

**Install Dependencies**:
```bash
pip install flask-socketio python-socketio requests
```

---

## 🎨 Frontend Implementation

### Step 1: Socket.IO Client Setup

**File**: `frontend/src/services/liveStream.ts`

```typescript
import { io, Socket } from 'socket.io-client';

interface LiveData {
  lte: {
    timestamp: string;
    rsrp: number;
    rssi: number;
    sinr: number;
    latitude: number;
    longitude: number;
    altitude: number;
    quality: string;
  } | null;
  starlink: {
    timestamp: string;
    snr: number;
    latency: number;
    throughput_down: number;
    throughput_up: number;
    latitude: number;
    longitude: number;
    altitude: number;
    quality: string;
  } | null;
  timestamp: string;
}

class LiveStreamService {
  private socket: Socket | null = null;
  private onDataCallback: ((data: LiveData) => void) | null = null;

  connect(backendUrl: string = 'http://localhost:5002') {
    this.socket = io(backendUrl, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5
    });

    this.socket.on('connected', (data) => {
      console.log('✅ Connected to live stream:', data);
    });

    this.socket.on('live_data', (data: LiveData) => {
      if (this.onDataCallback) {
        this.onDataCallback(data);
      }
    });

    this.socket.on('streaming_error', (error) => {
      console.error('❌ Streaming error:', error);
    });

    this.socket.on('disconnect', () => {
      console.log('🔌 Disconnected from live stream');
    });
  }

  startStreaming() {
    if (this.socket) {
      this.socket.emit('start_streaming', {});
      console.log('▶️ Started live streaming');
    }
  }

  stopStreaming() {
    if (this.socket) {
      this.socket.emit('stop_streaming', {});
      console.log('⏸️ Stopped live streaming');
    }
  }

  onData(callback: (data: LiveData) => void) {
    this.onDataCallback = callback;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}

export const liveStreamService = new LiveStreamService();
export type { LiveData };
```

**Install Dependencies**:
```bash
cd frontend
npm install socket.io-client
```

### Step 2: Live Drone Entity Component

**File**: `frontend/src/components/LiveDroneEntity.tsx`

```typescript
import React, { useEffect, useRef } from 'react';
import { liveStreamService, LiveData } from '@/services/liveStream';

interface LiveDroneEntityProps {
  viewer: any;  // Cesium.Viewer
  isActive: boolean;
}

export const LiveDroneEntity: React.FC<LiveDroneEntityProps> = ({
  viewer,
  isActive
}) => {
  const droneEntityRef = useRef<any>(null);

  useEffect(() => {
    if (!viewer || !isActive) return;

    // Create live drone entity
    const Cesium = (window as any).Cesium;
    droneEntityRef.current = viewer.entities.add({
      id: 'live_drone',
      name: 'Live Drone',
      position: Cesium.Cartesian3.fromDegrees(127.0, 37.5, 1000),
      model: {
        uri: '/models/drone.glb',  // 3D drone model
        minimumPixelSize: 64,
        maximumScale: 20000
      },
      label: {
        text: 'LIVE',
        font: '14px bold sans-serif',
        fillColor: Cesium.Color.RED,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -50),
        showBackground: true,
        backgroundColor: new Cesium.Color(0, 0, 0, 0.7)
      },
      // Add billboard as fallback if model doesn't load
      billboard: {
        image: '/icons/drone-icon.png',
        width: 48,
        height: 48
      }
    });

    // Setup live data listener
    liveStreamService.onData((data: LiveData) => {
      updateDronePosition(data);
    });

    // Cleanup
    return () => {
      if (droneEntityRef.current) {
        viewer.entities.remove(droneEntityRef.current);
        droneEntityRef.current = null;
      }
    };
  }, [viewer, isActive]);

  const updateDronePosition = (data: LiveData) => {
    if (!droneEntityRef.current) return;

    const Cesium = (window as any).Cesium;

    // Use LTE position if available, fallback to Starlink
    const latitude = data.lte?.latitude || data.starlink?.latitude;
    const longitude = data.lte?.longitude || data.starlink?.longitude;
    const altitude = data.lte?.altitude || data.starlink?.altitude;

    if (latitude && longitude && altitude) {
      // Update position smoothly
      droneEntityRef.current.position = Cesium.Cartesian3.fromDegrees(
        longitude,
        latitude,
        altitude
      );

      // Update label with quality info
      const lteQuality = data.lte?.quality || 'N/A';
      const starlinkQuality = data.starlink?.quality || 'N/A';
      droneEntityRef.current.label.text = `LIVE\nLTE: ${lteQuality.toUpperCase()}\nStarlink: ${starlinkQuality.toUpperCase()}`;

      console.log('🛸 Updated drone position:', {
        lat: latitude,
        lon: longitude,
        alt: altitude
      });
    }
  };

  return null;  // No UI, just 3D entity management
};
```

### Step 3: Live Streaming Control Panel

**File**: `frontend/src/components/LiveStreamingPanel.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { liveStreamService } from '@/services/liveStream';

interface LiveStreamingPanelProps {
  onStatusChange: (isLive: boolean) => void;
}

export const LiveStreamingPanel: React.FC<LiveStreamingPanelProps> = ({
  onStatusChange
}) => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [endpointStatus, setEndpointStatus] = useState<any>(null);

  useEffect(() => {
    // Check endpoint availability
    fetch('/api/live/status')
      .then(res => res.json())
      .then(data => {
        setEndpointStatus(data);
        setIsConnected(data.available);
      })
      .catch(err => {
        console.error('Failed to check live streaming status:', err);
      });
  }, []);

  const handleToggleStreaming = () => {
    if (!isStreaming) {
      // Start streaming
      liveStreamService.connect();
      liveStreamService.startStreaming();
      setIsStreaming(true);
      onStatusChange(true);
    } else {
      // Stop streaming
      liveStreamService.stopStreaming();
      liveStreamService.disconnect();
      setIsStreaming(false);
      onStatusChange(false);
    }
  };

  return (
    <div className="absolute top-20 left-4 bg-white rounded-lg shadow-xl p-4 w-[280px] z-20">
      <h3 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
        <LiveIcon className={`w-5 h-5 ${isStreaming ? 'text-red-600 animate-pulse' : 'text-gray-400'}`} />
        Live Streaming
      </h3>

      {/* Endpoint Status */}
      <div className="mb-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-600">LTE Endpoint</span>
          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
            endpointStatus?.endpoints?.lte?.status === 'online'
              ? 'bg-green-100 text-green-700'
              : 'bg-red-100 text-red-700'
          }`}>
            {endpointStatus?.endpoints?.lte?.status || 'unknown'}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-600">Starlink Endpoint</span>
          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
            endpointStatus?.endpoints?.starlink?.status === 'online'
              ? 'bg-green-100 text-green-700'
              : 'bg-red-100 text-red-700'
          }`}>
            {endpointStatus?.endpoints?.starlink?.status || 'unknown'}
          </span>
        </div>
      </div>

      {/* Control Buttons */}
      <button
        onClick={handleToggleStreaming}
        disabled={!isConnected}
        className={`w-full py-2 rounded-lg text-sm font-semibold transition-colors ${
          isStreaming
            ? 'bg-red-600 hover:bg-red-700 text-white'
            : 'bg-green-600 hover:bg-green-700 text-white disabled:bg-gray-300 disabled:cursor-not-allowed'
        }`}
      >
        {isStreaming ? '⏹ Stop Live Stream' : '▶️ Start Live Stream'}
      </button>

      {isStreaming && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          🔴 Streaming active - Real-time data visible on map
        </div>
      )}
    </div>
  );
};

// SVG Icon Component
const LiveIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="8" />
    <circle cx="12" cy="12" r="4" fill="white" />
  </svg>
);
```

### Step 4: Integration

**Modify** `frontend/src/App.tsx`:

```typescript
import { LiveDroneEntity } from './components/LiveDroneEntity';
import { LiveStreamingPanel } from './components/LiveStreamingPanel';

function App() {
  const [isLiveStreaming, setIsLiveStreaming] = useState(false);
  const cesiumViewerRef = useRef<any>(null);

  return (
    <>
      <CesiumViewer viewerRef={cesiumViewerRef} ... />

      <LiveStreamingPanel
        onStatusChange={(isLive) => setIsLiveStreaming(isLive)}
      />

      <LiveDroneEntity
        viewer={cesiumViewerRef.current}
        isActive={isLiveStreaming}
      />

      {/* Other components */}
    </>
  );
}
```

---

## ✅ Testing Checklist

### Backend Testing
- [ ] VPN connectivity test: `python3 analysis/scripts/test_vpn_endpoints.py`
- [ ] API proxy working: `curl http://localhost:5002/api/live/lte-current`
- [ ] WebSocket connection: Test with Socket.IO client
- [ ] Data normalization: Verify LTE/Starlink formats match
- [ ] Error handling: Test with endpoints offline

### Frontend Testing
- [ ] Socket.IO connection successful
- [ ] Live drone entity appears on 3D globe
- [ ] Position updates in real-time (1Hz)
- [ ] KPI Dashboard reflects live data
- [ ] Start/Stop streaming works
- [ ] Reconnection after network interruption

### Integration Testing
- [ ] End-to-end: VPN → Backend → Frontend → Cesium
- [ ] Multiple concurrent clients
- [ ] Performance: <100ms latency, >30 FPS
- [ ] Recording mode (save live stream to session)

---

## 🎯 Success Criteria

1. **Real-time Updates**: Drone position updates every 1 second
2. **Low Latency**: <500ms from VPN to 3D display
3. **Stable Connection**: Auto-reconnect on network issues
4. **Visual Clarity**: Live drone clearly distinguishable from historical data
5. **User Control**: Easy start/stop streaming interface

---

## 📊 Performance Targets

| Metric | Target |
|--------|--------|
| **Update Frequency** | 1 Hz (1 update/sec) |
| **End-to-end Latency** | <500ms |
| **WebSocket Reconnect** | <3 seconds |
| **Memory Overhead** | <100MB |
| **CPU Usage** | <10% additional |
| **3D Rendering FPS** | Maintain >30 FPS |

---

**End of Phase 6 Design**
