# Starlink Flight Analysis 3D Visualization - Advanced Features Design

**Version**: 1.0
**Date**: 2026-02-10
**Status**: Ready for Implementation

---

## 📐 UI Layout Architecture

### Layout Principles
1. **Non-overlapping**: All UI components positioned to avoid conflicts
2. **Toggleable**: Every panel can be shown/hidden by user
3. **Minimal obstruction**: Main 3D viewer remains primary focus
4. **Consistent spacing**: 16px padding from edges, 12px between panels

### Screen Layout Map

```
┌─────────────────────────────────────────────────────────────────┐
│ [햄버거 메뉴] (좌측 상단)                   [KPI Dashboard] │
│ ⋮ 컨트롤패널 토글                              우측 상단 고정    │
│                                                  280px × auto   │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
│                        3D VIEWER                                │
│                     (Main Focus Area)                           │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
│ [Root Cause Panel]                                              │
│ 좌측 하단 (토글)                                                │
│ 360px × auto                                                    │
│                                                                 │
│ [Timeline + Playback Controls]  (하단 중앙)                    │
│            전체 폭 사용, 80px 높이                             │
└─────────────────────────────────────────────────────────────────┘
```

### Component Positioning Details

| Component | Position | Size | Z-Index | Toggle |
|-----------|----------|------|---------|--------|
| **Hamburger Menu** | `top: 16px, left: 16px` | `48px × 48px` | 30 | Always visible |
| **Control Panel** | `top: 72px, left: 16px` | `320px × auto` | 20 | Toggle (default: visible) |
| **KPI Dashboard** | `top: 16px, right: 16px` | `280px × auto` | 25 | Toggle (default: visible) |
| **Root Cause Panel** | `bottom: 120px, left: 16px` | `360px × auto` | 25 | Toggle (default: hidden) |
| **Analytics Panel** | `top: 80px, right: 16px` | `450px × 600px` | 10 | Toggle (default: hidden) |
| **Timeline Widget** | `bottom: 16px, center` | `80% width × 80px` | 15 | Always visible |
| **Signal Loss Markers** | N/A (3D objects) | N/A | N/A | Toggle via control panel |
| **Drilldown Popup** | Center overlay | `480px × 560px` | 50 | On-demand (click event) |

---

## 🎨 SVG Icon Design

### Hamburger Menu Icon
```svg
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
```

### KPI Dashboard Icon (Summary)
```svg
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
  <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
  <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
  <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
</svg>
```

### Root Cause Icon (Analyze)
```svg
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="2"/>
  <path d="M21 21l-4.35-4.35" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  <path d="M8 11h6M11 8v6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
```

### Timeline Play Icon
```svg
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M8 5v14l11-7L8 5z" fill="currentColor"/>
</svg>
```

### Timeline Pause Icon
```svg
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="6" y="4" width="4" height="16" fill="currentColor"/>
  <rect x="14" y="4" width="4" height="16" fill="currentColor"/>
</svg>
```

### Signal Loss Icon (Warning)
```svg
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 2L2 22h20L12 2z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
  <path d="M12 9v5M12 17v.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
```

### Close Icon (X)
```svg
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
```

### Expand/Collapse Icon
```svg
<!-- Expand (chevron down) -->
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>

<!-- Collapse (chevron up) -->
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M18 15l-6-6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

---

## 🏗️ Implementation Phases

### **Phase 1: KPI Dashboard (Days 1-2)**

**Priority**: HIGH
**Complexity**: LOW
**Dependencies**: None

#### Backend Implementation

**File**: `analysis/api/threed/kpi.py`

```python
"""
KPI Summary API
Provides flight statistics and signal quality summary
"""
from flask import Blueprint, jsonify
import pandas as pd
import numpy as np
from pathlib import Path
import config

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
                'quality': str,  # 'excellent', 'good', 'fair', 'poor', 'very_poor'
                'color': str     # hex color
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
        merged_csv_path = config.RESULTS_FOLDER / session_id / 'merged_flight_data.csv'
        if not merged_csv_path.exists():
            return jsonify({'error': 'Session data not found'}), 404

        df = pd.read_csv(merged_csv_path, parse_dates=['timestamp'])

        # Flight metrics
        duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
        distance = calculate_total_distance(df)
        max_altitude = df['altitude'].max()
        avg_speed = df['speed_mps'].mean() * 3.6  # Convert m/s to km/h

        # LTE metrics
        lte_avg_rsrp = df['lte_rsrp'].mean() if 'lte_rsrp' in df.columns else None
        lte_quality = classify_lte_quality(lte_avg_rsrp) if lte_avg_rsrp else None
        lte_color = quality_to_color(lte_quality) if lte_quality else '#cccccc'

        # Starlink metrics
        starlink_avg_latency = df['starlink_latency'].mean() if 'starlink_latency' in df.columns else None
        starlink_quality = classify_starlink_quality(starlink_avg_latency) if starlink_avg_latency else None
        starlink_color = quality_to_color(starlink_quality) if starlink_quality else '#cccccc'

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
        return jsonify({'error': str(e)}), 500


def calculate_total_distance(df: pd.DataFrame) -> float:
    """Calculate total flight distance in kilometers using Haversine formula"""
    from math import radians, sin, cos, sqrt, atan2

    total_distance = 0.0
    for i in range(1, len(df)):
        lat1, lon1 = radians(df.iloc[i-1]['latitude']), radians(df.iloc[i-1]['longitude'])
        lat2, lon2 = radians(df.iloc[i]['latitude']), radians(df.iloc[i]['longitude'])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        total_distance += 6371 * c  # Earth radius = 6371 km

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
    poor_lte = df['lte_rsrp'] < -110 if 'lte_rsrp' in df.columns else pd.Series([False] * len(df))
    poor_starlink = df['starlink_latency'] > 160 if 'starlink_latency' in df.columns else pd.Series([False] * len(df))

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
    total_duration = poor_count  # seconds

    return {
        'percentage': round((poor_count / len(df)) * 100, 2),
        'segment_count': segment_count,
        'total_duration_seconds': total_duration
    }
```

**Register Blueprint** in `analysis/app.py`:
```python
from api.threed.kpi import kpi_bp
app.register_blueprint(kpi_bp)
```

#### Frontend Implementation

**File**: `frontend/src/components/KPIDashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { getKPISummary } from '@/services/api';

interface KPIData {
  flight: {
    duration_seconds: number;
    distance_km: number;
    max_altitude_m: number;
    avg_speed_kmh: number;
  };
  lte: {
    avg_rsrp: number | null;
    quality: string | null;
    color: string;
  };
  starlink: {
    avg_latency: number | null;
    quality: string | null;
    color: string;
  };
  signal_loss: {
    percentage: number;
    segment_count: number;
    total_duration_seconds: number;
  };
}

interface KPIDashboardProps {
  sessionId: string | null;
  isVisible: boolean;
  onToggle: () => void;
}

export const KPIDashboard: React.FC<KPIDashboardProps> = ({
  sessionId,
  isVisible,
  onToggle
}) => {
  const [kpi, setKpi] = useState<KPIData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const loadKPI = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getKPISummary(sessionId);
        setKpi(data);
      } catch (err) {
        console.error('Failed to load KPI:', err);
        setError('Failed to load KPI data');
      } finally {
        setLoading(false);
      }
    };

    loadKPI();
  }, [sessionId]);

  if (!isVisible) {
    return (
      <button
        onClick={onToggle}
        className="absolute top-4 right-4 bg-white rounded-lg shadow-lg p-2 hover:bg-gray-50 transition-colors z-25"
        title="Show KPI Dashboard"
      >
        <SummaryIcon className="w-6 h-6 text-gray-700" />
      </button>
    );
  }

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  return (
    <div className="absolute top-4 right-4 bg-white rounded-lg shadow-xl p-4 w-[280px] z-25">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-gray-800 flex items-center gap-2">
          <SummaryIcon className="w-5 h-5 text-blue-600" />
          Flight Summary
        </h3>
        <button
          onClick={onToggle}
          className="text-gray-500 hover:text-gray-700 transition-colors"
          title="Hide KPI Dashboard"
        >
          <CloseIcon className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center text-gray-500 text-sm py-8">Loading...</div>
      ) : error ? (
        <div className="text-center text-red-500 text-sm py-4">{error}</div>
      ) : kpi ? (
        <>
          {/* Flight Metrics */}
          <div className="space-y-2 mb-3 pb-3 border-b border-gray-200">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-600">✈️ Duration</span>
              <span className="font-semibold text-gray-900">
                {formatDuration(kpi.flight.duration_seconds)}
              </span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-600">📏 Distance</span>
              <span className="font-semibold text-gray-900">
                {kpi.flight.distance_km.toFixed(1)} km
              </span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-600">⛰️ Max Altitude</span>
              <span className="font-semibold text-gray-900">
                {kpi.flight.max_altitude_m.toFixed(0)} m
              </span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-600">🚀 Avg Speed</span>
              <span className="font-semibold text-gray-900">
                {kpi.flight.avg_speed_kmh.toFixed(1)} km/h
              </span>
            </div>
          </div>

          {/* LTE Quality */}
          {kpi.lte.quality && (
            <div className="mb-2 p-2 rounded-lg" style={{ backgroundColor: kpi.lte.color + '15' }}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-700">LTE Quality</span>
                <span
                  className="px-2 py-0.5 rounded text-xs font-bold text-white uppercase"
                  style={{ backgroundColor: kpi.lte.color }}
                >
                  {kpi.lte.quality}
                </span>
              </div>
              <div className="text-xs text-gray-600">
                Avg RSRP: {kpi.lte.avg_rsrp?.toFixed(1)} dBm
              </div>
            </div>
          )}

          {/* Starlink Quality */}
          {kpi.starlink.quality && (
            <div className="mb-2 p-2 rounded-lg" style={{ backgroundColor: kpi.starlink.color + '15' }}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-700">Starlink Quality</span>
                <span
                  className="px-2 py-0.5 rounded text-xs font-bold text-white uppercase"
                  style={{ backgroundColor: kpi.starlink.color }}
                >
                  {kpi.starlink.quality}
                </span>
              </div>
              <div className="text-xs text-gray-600">
                Avg Latency: {kpi.starlink.avg_latency?.toFixed(0)} ms
              </div>
            </div>
          )}

          {/* Signal Loss */}
          <div
            className={`p-2 rounded-lg ${
              kpi.signal_loss.percentage > 10
                ? 'bg-red-50 border border-red-200'
                : 'bg-green-50 border border-green-200'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-gray-700 flex items-center gap-1">
                <SignalLossIcon className="w-3 h-3" />
                Signal Loss
              </span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-bold text-white ${
                  kpi.signal_loss.percentage > 10 ? 'bg-red-600' : 'bg-green-600'
                }`}
              >
                {kpi.signal_loss.percentage.toFixed(1)}%
              </span>
            </div>
            <div className="text-xs text-gray-600">
              {kpi.signal_loss.segment_count} segment{kpi.signal_loss.segment_count !== 1 ? 's' : ''}
              {' '}({formatDuration(kpi.signal_loss.total_duration_seconds)})
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
};

// SVG Icon Components
const SummaryIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
    <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
    <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
    <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
  </svg>
);

const CloseIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const SignalLossIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2L2 22h20L12 2z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
    <path d="M12 9v5M12 17v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);
```

**API Service** (`frontend/src/services/api.ts`):
```typescript
export async function getKPISummary(sessionId: string): Promise<any> {
  const response = await fetch(`/api/3d/kpi/${sessionId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch KPI summary');
  }
  return response.json();
}
```

#### Integration

**Modify** `frontend/src/App.tsx`:
```typescript
import { KPIDashboard } from './components/KPIDashboard';

function App() {
  const [showKPI, setShowKPI] = useState(true);

  return (
    <>
      <CesiumViewer ... />
      <KPIDashboard
        sessionId={selectedSessionId}
        isVisible={showKPI}
        onToggle={() => setShowKPI(!showKPI)}
      />
    </>
  );
}
```

**Testing Checklist**:
- [ ] Backend: `/api/3d/kpi/<session_id>` returns correct data
- [ ] Frontend: KPI Dashboard displays correctly in top-right corner
- [ ] Toggle button shows/hides panel
- [ ] No overlap with existing Control Panel (left side)
- [ ] Data updates when session changes
- [ ] Signal loss percentage calculation correct
- [ ] Quality color coding matches thresholds

---

### **Phase 2: Signal Loss 3D Markers (Days 3-4)**

[Similar detailed structure for remaining phases...]

---

## 📋 Development Checklist

### Pre-Implementation
- [ ] Review UI layout mockups with stakeholders
- [ ] Confirm color scheme and icon designs
- [ ] Set up development branch: `feature/advanced-ui`
- [ ] Create component storybook entries

### Phase 1: KPI Dashboard
- [ ] Backend API implementation
- [ ] Frontend component development
- [ ] SVG icon integration
- [ ] Toggle functionality
- [ ] Unit tests
- [ ] Integration tests
- [ ] Documentation

### Phase 2: Signal Loss Markers
- [ ] Backend detection algorithm
- [ ] CZML cylinder generation
- [ ] Frontend 3D rendering
- [ ] Toggle in Control Panel
- [ ] Performance testing

### Phase 3: Cesium Timeline
- [ ] CZML time availability
- [ ] Timeline widget integration
- [ ] Playback controls
- [ ] Speed adjustment
- [ ] Jump to time feature

### Phase 4: Root Cause Analysis
- [ ] Statistical analysis logic
- [ ] Cell tower distance calculation
- [ ] Recommendation engine
- [ ] Frontend panel component
- [ ] Pie chart visualization

### Phase 5: Drilldown Popup
- [ ] Click event handler
- [ ] Point detail API
- [ ] Popup modal component
- [ ] Jump to location feature
- [ ] Performance optimization

### Phase 6: Live Streaming Integration (CRITICAL - Real-time Monitoring)
- [ ] VPN endpoint integration (100.119.109.7:8079, 100.66.190.1:8080)
- [ ] WebSocket/SSE connection to existing monitoring system
- [ ] Real-time data parser and normalizer
- [ ] 3D entity animation (live drone position)
- [ ] Live KPI Dashboard updates
- [ ] Signal quality alerts
- [ ] Recording/Playback mode
- [ ] Connection status indicator

---

## 🚀 Deployment Strategy

### Development Environment
1. Implement on `feature/advanced-ui` branch
2. Test each phase independently
3. Merge to `develop` after phase completion

### Production Rollout
1. Deploy Phase 1-2 (Week 1)
2. Collect user feedback
3. Deploy Phase 3-4 (Week 2)
4. Deploy Phase 5 (Week 3)
5. Monitor performance metrics

---

## 📊 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **UI Responsiveness** | <100ms interaction | Chrome DevTools Performance |
| **3D Rendering FPS** | >30 FPS | Cesium.Scene.debugShowFramesPerSecond |
| **API Response Time** | <500ms | Flask logs + Browser Network tab |
| **Component Load Time** | <200ms | React Profiler |
| **Memory Usage** | <500MB additional | Chrome Task Manager |
| **User Adoption** | >80% toggle usage | Analytics tracking |

---

## 🔧 Technical Debt Prevention

### Code Quality
- TypeScript strict mode enabled
- ESLint + Prettier configuration
- Component prop validation
- Comprehensive error handling

### Performance
- React.memo for expensive components
- useMemo for heavy calculations
- Debounce for user interactions
- Lazy loading for large datasets

### Maintainability
- Component documentation (JSDoc)
- API endpoint documentation (Swagger)
- Consistent naming conventions
- Modular file structure

---

## 📚 References

- [Cesium Timeline Documentation](https://cesium.com/learn/cesiumjs/ref-doc/Timeline.html)
- [React Performance Optimization](https://react.dev/learn/render-and-commit)
- [Flask Blueprint Best Practices](https://flask.palletsprojects.com/en/stable/blueprints/)
- [SVG Optimization Guidelines](https://jakearchibald.github.io/svgomg/)

---

**End of Design Document**
