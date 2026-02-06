# Phase 1: 3D Flight Visualization Foundation Infrastructure
## Production-Ready Implementation Plan (Weeks 1-2)

**Project**: Starlink Flight Data Analysis - 3D Visualization Module
**Version**: 1.0
**Status**: Ready for Implementation
**Timeline**: 2 Weeks (10 Business Days)
**Target**: Enterprise-Grade Foundation, NOT POC

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Phase 1 Scope & Success Criteria](#2-phase-1-scope--success-criteria)
3. [Project Setup & Architecture](#3-project-setup--architecture)
4. [Technology Stack Installation](#4-technology-stack-installation)
5. [Backend Integration](#5-backend-integration)
6. [Core 3D Components](#6-core-3d-components)
7. [Code Quality Infrastructure](#7-code-quality-infrastructure)
8. [Development Workflow](#8-development-workflow)
9. [Risk Mitigation Strategy](#9-risk-mitigation-strategy)
10. [Daily Implementation Schedule](#10-daily-implementation-schedule)
11. [Acceptance Criteria Checklist](#11-acceptance-criteria-checklist)

---

## 1. Executive Summary

### 1.1 What We're Building

**Goal**: Create a production-ready 3D flight visualization system that integrates seamlessly with the existing Flask backend (port 5002) and PostgreSQL database.

**Phase 1 Deliverables**:
- Cesium.js 3D globe with terrain and buildings
- Single ULG file flight path visualization
- CZML data format pipeline (ULG → PostgreSQL → CZML)
- Clean architecture with TypeScript strict mode
- 60 FPS performance baseline
- Full test coverage (80%+)

**NOT in Phase 1**:
- Real-time data streaming (Phase 2)
- LTE base station visualization (Phase 3)
- Starlink satellite tracking (Phase 4)
- Multi-flight comparison (Future)

### 1.2 Success Metrics

| Metric | Target | Critical? |
|--------|--------|-----------|
| **Build Success** | Zero warnings, zero errors | YES |
| **Performance** | 60 FPS with 5,000+ flight points | YES |
| **Type Safety** | 100% TypeScript, no `any` | YES |
| **Test Coverage** | 80%+ (Unit + Integration) | YES |
| **Load Time** | < 3 seconds (globe + flight path) | YES |
| **Code Quality** | ESLint score > 95, no critical issues | YES |

---

## 2. Phase 1 Scope & Success Criteria

### 2.1 Functional Requirements

#### Must Have (P0)
- [x] 3D globe renders with Cesium World Terrain
- [x] OSM 3D Buildings layer visible
- [x] Single flight path from ULG file displayed in 3D
- [x] Flight path colored by altitude (gradient)
- [x] Camera controls (rotate, zoom, pan with mouse)
- [x] Loading state with progress indicator
- [x] Error handling for failed data loads

#### Should Have (P1)
- [x] Flight path hover tooltip (lat, lon, altitude)
- [x] Camera reset button
- [x] Basic layer toggles (flight path, buildings, terrain)
- [x] Responsive UI (desktop, tablet)

#### Nice to Have (P2)
- [ ] Flight path click to show details panel
- [ ] Screenshot export
- [ ] Keyboard shortcuts (R: reset, Space: toggle visibility)

### 2.2 Non-Functional Requirements

#### Performance
- **Initial Load**: < 3 seconds (median, 4G network)
- **FPS**: 60 FPS sustained with 5,000+ points
- **Memory**: < 500MB after 5 minutes of use
- **Bundle Size**: < 2MB (gzipped)

#### Quality
- **TypeScript**: Strict mode, zero `any` types in src/
- **ESLint**: Zero errors, < 5 warnings
- **Test Coverage**: 80%+ (lines, branches)
- **Accessibility**: WCAG 2.1 Level A minimum

#### Maintainability
- **Documentation**: Every public API documented (JSDoc)
- **Architecture**: Clean separation (UI, Logic, Data)
- **Modularity**: Reusable hooks, components

---

## 3. Project Setup & Architecture

### 3.1 Directory Structure (Complete Tree)

```
/Users/dykim/dev/starlink/analysis/
├── frontend/                           # NEW: React Frontend
│   ├── public/
│   │   ├── models/
│   │   │   └── aircraft.glb           # 3D aircraft model (optional Phase 1)
│   │   ├── cesium/                     # Cesium assets (CDN alternative)
│   │   │   ├── Assets/
│   │   │   ├── ThirdParty/
│   │   │   ├── Widgets/
│   │   │   └── Workers/
│   │   └── index.html
│   │
│   ├── src/
│   │   ├── components/                 # React Components
│   │   │   ├── Cesium/
│   │   │   │   ├── CesiumViewer.tsx         # Main 3D viewer
│   │   │   │   ├── FlightPathEntity.tsx     # Flight path rendering
│   │   │   │   ├── CameraControls.tsx       # Camera control UI
│   │   │   │   └── LoadingOverlay.tsx       # Loading state
│   │   │   │
│   │   │   ├── UI/
│   │   │   │   ├── Button.tsx               # Reusable button
│   │   │   │   ├── Tooltip.tsx              # Hover tooltips
│   │   │   │   ├── LayerToggle.tsx          # Layer visibility toggle
│   │   │   │   └── ErrorBoundary.tsx        # Error fallback
│   │   │   │
│   │   │   └── Layout/
│   │   │       ├── AppLayout.tsx            # Main layout wrapper
│   │   │       ├── Header.tsx               # Top navigation
│   │   │       └── Sidebar.tsx              # Control panel (Phase 2)
│   │   │
│   │   ├── hooks/                      # Custom React Hooks
│   │   │   ├── useCesiumViewer.ts           # Viewer initialization
│   │   │   ├── useFlightData.ts             # Data loading
│   │   │   ├── useCamera.ts                 # Camera control
│   │   │   └── useEntities.ts               # Entity management
│   │   │
│   │   ├── services/                   # Business Logic
│   │   │   ├── api/
│   │   │   │   ├── flightApi.ts             # Flight data API client
│   │   │   │   └── types.ts                 # API type definitions
│   │   │   │
│   │   │   ├── cesium/
│   │   │   │   ├── czmlParser.ts            # CZML parsing
│   │   │   │   ├── colorMapping.ts          # Altitude → Color
│   │   │   │   └── entityFactory.ts         # Entity creation
│   │   │   │
│   │   │   └── utils/
│   │   │       ├── coordinates.ts           # Geo calculations
│   │   │       └── formatters.ts            # Data formatting
│   │   │
│   │   ├── store/                      # State Management (Zustand)
│   │   │   ├── viewerStore.ts               # Viewer state
│   │   │   ├── flightDataStore.ts           # Flight data cache
│   │   │   └── uiStore.ts                   # UI state
│   │   │
│   │   ├── types/                      # TypeScript Definitions
│   │   │   ├── cesium.d.ts                  # Cesium type augmentations
│   │   │   ├── flight.ts                    # Flight data types
│   │   │   └── api.ts                       # API response types
│   │   │
│   │   ├── styles/                     # Global Styles
│   │   │   ├── globals.css                  # Tailwind directives
│   │   │   └── cesium-overrides.css         # Cesium widget styles
│   │   │
│   │   ├── App.tsx                     # Root component
│   │   ├── main.tsx                    # Entry point
│   │   └── vite-env.d.ts               # Vite types
│   │
│   ├── tests/                          # Test Files
│   │   ├── unit/
│   │   │   ├── hooks/
│   │   │   │   ├── useCesiumViewer.test.ts
│   │   │   │   └── useFlightData.test.ts
│   │   │   │
│   │   │   └── services/
│   │   │       ├── czmlParser.test.ts
│   │   │       └── colorMapping.test.ts
│   │   │
│   │   ├── integration/
│   │   │   └── CesiumViewer.test.tsx
│   │   │
│   │   ├── e2e/
│   │   │   └── flight-visualization.spec.ts
│   │   │
│   │   └── setup.ts                    # Test configuration
│   │
│   ├── .eslintrc.cjs                   # ESLint config
│   ├── .prettierrc.json                # Prettier config
│   ├── package.json                    # Dependencies
│   ├── tsconfig.json                   # TypeScript config
│   ├── tsconfig.node.json              # Node TypeScript config
│   ├── vite.config.ts                  # Vite build config
│   ├── tailwind.config.js              # Tailwind config
│   ├── postcss.config.js               # PostCSS config
│   └── README.md                       # Frontend documentation
│
├── backend/                            # EXISTING: Flask Backend
│   ├── api/
│   │   ├── 3d/                         # NEW: 3D API Blueprint
│   │   │   ├── __init__.py
│   │   │   ├── flights.py              # Flight data endpoints
│   │   │   ├── czml.py                 # CZML generation
│   │   │   └── validation.py           # Request validation
│   │   │
│   │   ├── sessions.py                 # EXISTING
│   │   ├── upload.py                   # EXISTING
│   │   └── results.py                  # EXISTING
│   │
│   ├── services/                       # NEW: Service Layer
│   │   ├── czml_generator.py           # ULG → CZML conversion
│   │   ├── flight_data_service.py      # Flight data processing
│   │   └── ulg_parser.py               # ULG file parsing (reuse existing)
│   │
│   ├── models/
│   │   └── database.py                 # EXISTING: Add new schema
│   │
│   ├── app.py                          # EXISTING: Add 3D blueprint
│   └── requirements.txt                # EXISTING: Add dependencies
│
├── docs/                               # Project Documentation
│   ├── API.md                          # API endpoints documentation
│   ├── ARCHITECTURE.md                 # System architecture
│   ├── DEVELOPMENT.md                  # Development guide
│   └── DEPLOYMENT.md                   # Deployment instructions
│
└── scripts/                            # Utility Scripts
    ├── dev.sh                          # Start dev servers
    ├── build.sh                        # Production build
    └── test.sh                         # Run all tests
```

### 3.2 Architecture Decision Records (ADRs)

#### ADR-001: Frontend Framework - React 18

**Decision**: Use React 18 with TypeScript

**Rationale**:
- Existing 2D dashboard uses vanilla JavaScript (easy migration)
- React ecosystem has mature Cesium integrations (Resium)
- TypeScript provides type safety for Cesium API (complex 3D APIs)
- Zustand for lightweight state management (no Redux boilerplate)

**Alternatives Considered**:
- Vue 3: Less Cesium ecosystem support
- Svelte: Smaller community, fewer examples
- Vanilla JS: No type safety, harder to maintain

#### ADR-002: 3D Library - Cesium.js

**Decision**: Use Cesium.js (not Three.js, Deck.gl, Babylon.js)

**Rationale**:
- Native geospatial support (WGS84, terrain, globe projection)
- CZML format designed for time-series flight data
- FAA ActiveFlight uses Cesium (aviation industry standard)
- Built-in satellite tracking (future Phase 4)

**Trade-offs**:
- Bundle size: 1.4MB (mitigated with CDN + code splitting)
- Learning curve: Moderate (mitigated with official tutorials)

#### ADR-003: State Management - Zustand

**Decision**: Use Zustand over Redux Toolkit

**Rationale**:
- Minimal boilerplate (3-5x less code than Redux)
- React hooks-based API (modern, intuitive)
- No context provider wrapping (simpler setup)
- Good TypeScript support

**When to Reconsider**:
- If we need Redux DevTools time-travel debugging (can use Zustand middleware)
- If state management becomes very complex (10+ stores)

#### ADR-004: Data Format - CZML

**Decision**: Use CZML (Cesium Language) for flight data

**Rationale**:
- Native Cesium format (zero parsing overhead)
- Time-series animation built-in (SampledPositionProperty)
- Server-side generation (Python libraries available)
- Supports custom properties (LTE RSRP, Starlink latency)

**Alternative**: GeoJSON + manual time handling (more work, less performant)

#### ADR-005: Backend API - RESTful + JSON

**Decision**: RESTful API with JSON (NOT GraphQL)

**Rationale**:
- Existing Flask app uses REST (consistency)
- Simple caching strategies (HTTP headers)
- No over-fetching concerns (specific endpoints)

**Future**: Consider WebSocket for Phase 2 (real-time streaming)

### 3.3 Git Workflow & Branching Strategy

**Branch Structure**:
```
main                    # Production-ready code
├── develop             # Integration branch
│   ├── feature/3d-viewer-setup
│   ├── feature/czml-pipeline
│   ├── feature/flight-path-rendering
│   └── feature/ui-components
└── hotfix/*            # Critical production fixes
```

**Commit Convention** (Conventional Commits):
```
feat: Add Cesium viewer initialization hook
fix: Correct altitude color mapping calculation
docs: Update API endpoint documentation
test: Add unit tests for CZML parser
refactor: Extract camera control to custom hook
chore: Update dependencies to latest versions
```

**Pull Request Template**:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Refactoring

## Checklist
- [ ] Tests pass (`npm test`)
- [ ] ESLint passes (`npm run lint`)
- [ ] TypeScript compiles (`npm run type-check`)
- [ ] Documentation updated
- [ ] No console.log statements
- [ ] Backward compatible

## Screenshots (if UI changes)
```

---

## 4. Technology Stack Installation

### 4.1 Frontend Dependencies

#### 4.1.1 `package.json` (Complete, Production-Ready)

```json
{
  "name": "starlink-3d-visualization",
  "version": "1.0.0",
  "description": "3D Flight Communication Quality Visualization",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "lint:fix": "eslint . --ext ts,tsx --fix",
    "type-check": "tsc --noEmit",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\"",
    "format:check": "prettier --check \"src/**/*.{ts,tsx,css}\"",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "prepare": "husky install"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "cesium": "^1.120.0",
    "resium": "^1.17.3",
    "zustand": "^4.5.2",
    "@radix-ui/react-tooltip": "^1.0.7",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-switch": "^1.0.3",
    "@radix-ui/react-slider": "^1.1.2",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.2",
    "date-fns": "^3.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.2.66",
    "@types/react-dom": "^18.2.22",
    "@typescript-eslint/eslint-plugin": "^7.2.0",
    "@typescript-eslint/parser": "^7.2.0",
    "@vitejs/plugin-react-swc": "^3.5.0",
    "autoprefixer": "^10.4.19",
    "eslint": "^8.57.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.6",
    "husky": "^9.0.11",
    "lint-staged": "^15.2.2",
    "postcss": "^8.4.38",
    "prettier": "^3.2.5",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.4.3",
    "vite": "^5.2.0",
    "vite-plugin-cesium": "^1.2.22",
    "vitest": "^1.4.0",
    "@vitest/ui": "^1.4.0",
    "@vitest/coverage-v8": "^1.4.0",
    "@testing-library/react": "^14.2.2",
    "@testing-library/jest-dom": "^6.4.2",
    "@testing-library/user-event": "^14.5.2",
    "@playwright/test": "^1.42.1",
    "jsdom": "^24.0.0"
  },
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ]
  }
}
```

**Why These Versions?**:
- `cesium@1.120.0`: Latest stable (2024 Feb), WebGL 2 optimizations
- `react@18.2.0`: Concurrent rendering, automatic batching
- `resium@1.17.3`: Latest Cesium-React integration (TypeScript support)
- `zustand@4.5.2`: Latest with improved TypeScript inference
- `@radix-ui/*`: Unstyled, accessible primitives (WCAG 2.1 compliant)
- `vite@5.2.0`: 10x faster than Webpack, native ESM

#### 4.1.2 `tsconfig.json` (Strict Mode)

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting (STRICT MODE) */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noImplicitOverride": true,

    /* Path Aliases */
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@components/*": ["./src/components/*"],
      "@hooks/*": ["./src/hooks/*"],
      "@services/*": ["./src/services/*"],
      "@store/*": ["./src/store/*"],
      "@types/*": ["./src/types/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**Critical Settings**:
- `strict: true`: All strict type-checking options enabled
- `noImplicitAny: true`: No implicit `any` types allowed
- `noUncheckedIndexedAccess: true`: Array access safety
- `exactOptionalPropertyTypes: true`: Strict optional property handling

#### 4.1.3 `vite.config.ts` (Cesium Integration)

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import cesium from 'vite-plugin-cesium';
import path from 'path';

export default defineConfig({
  plugins: [
    react(),
    cesium()
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@services': path.resolve(__dirname, './src/services'),
      '@store': path.resolve(__dirname, './src/store'),
      '@types': path.resolve(__dirname, './src/types')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5002',
        changeOrigin: true
      }
    }
  },
  build: {
    target: 'esnext',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
    rollupOptions: {
      output: {
        manualChunks: {
          'cesium': ['cesium', 'resium'],
          'vendor': ['react', 'react-dom'],
          'ui': ['@radix-ui/react-tooltip', '@radix-ui/react-dialog']
        }
      }
    },
    chunkSizeWarningLimit: 2000
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV)
  }
});
```

**Performance Optimizations**:
- Code splitting: Cesium in separate chunk (1.4MB isolated)
- SWC compiler: 20x faster than Babel
- Proxy to Flask backend: No CORS issues
- Terser minification: Drop console logs in production

#### 4.1.4 `tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cesium: {
          dark: '#303336',
          light: '#f0f0f0'
        }
      },
      zIndex: {
        'cesium-overlay': '9999'
      }
    },
  },
  plugins: [],
}
```

#### 4.1.5 `.eslintrc.cjs` (Strict Linting)

```javascript
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended-type-checked',
    'plugin:@typescript-eslint/stylistic-type-checked',
    'plugin:react-hooks/recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime'
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs', 'vite.config.ts'],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    project: ['./tsconfig.json', './tsconfig.node.json'],
    tsconfigRootDir: __dirname,
  },
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    '@typescript-eslint/no-unused-vars': ['error', {
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_'
    }],
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/explicit-function-return-type': 'off',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    'no-console': ['warn', { allow: ['warn', 'error'] }]
  },
  settings: {
    react: {
      version: 'detect'
    }
  }
}
```

**Strict Rules**:
- `@typescript-eslint/no-explicit-any: 'error'`: Ban `any` type
- `no-console: 'warn'`: Warn on console.log (allow warn/error)
- Type-checked linting enabled (requires project references)

### 4.2 Backend Dependencies

#### 4.2.1 Updated `requirements.txt`

```txt
# Existing Dependencies
Flask==3.0.2
Flask-CORS==4.0.0
pandas==2.2.1
numpy==1.26.4
pyulog==1.1.0
folium==0.16.0
matplotlib==3.8.3
seaborn==0.13.2
python-docx==1.1.0

# NEW: 3D Visualization Dependencies
czml3==1.0.1              # CZML generation library
pydantic==2.6.3           # Data validation
pytz==2024.1              # Timezone handling
```

**Why These Libraries?**:
- `czml3`: Python library for CZML generation (type-safe)
- `pydantic`: Validate API requests/responses (auto-generate docs)
- `pytz`: Timezone conversion for UTC timestamps

---

## 5. Backend Integration

### 5.1 Database Schema Updates

#### 5.1.1 New Tables (Add to `models/database.py`)

```sql
-- 3D flight data cache table
CREATE TABLE IF NOT EXISTS flight_3d_data (
    session_id TEXT PRIMARY KEY,
    czml_data TEXT NOT NULL,           -- Serialized CZML JSON
    geometry_hash TEXT NOT NULL,       -- Hash for cache invalidation
    min_altitude REAL,
    max_altitude REAL,
    duration_seconds REAL,
    total_points INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_flight_3d_session ON flight_3d_data(session_id);
CREATE INDEX IF NOT EXISTS idx_flight_3d_hash ON flight_3d_data(geometry_hash);
```

**Why This Schema?**:
- **czml_data**: Pre-generated CZML (avoid regeneration)
- **geometry_hash**: MD5 of ULG file (detect changes)
- **min/max_altitude**: For color scale calculation
- **total_points**: For performance warnings (> 10,000 points)

#### 5.1.2 Database Migration Script

```python
# migrations/001_add_3d_tables.py
"""
Migration: Add 3D flight data tables
"""
from models.database import get_db

def upgrade():
    """Apply migration"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flight_3d_data (
            session_id TEXT PRIMARY KEY,
            czml_data TEXT NOT NULL,
            geometry_hash TEXT NOT NULL,
            min_altitude REAL,
            max_altitude REAL,
            duration_seconds REAL,
            total_points INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_flight_3d_session ON flight_3d_data(session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_flight_3d_hash ON flight_3d_data(geometry_hash)')

    conn.commit()
    conn.close()
    print("✅ Migration 001_add_3d_tables completed")

def downgrade():
    """Rollback migration"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS flight_3d_data')
    conn.commit()
    conn.close()
    print("✅ Rollback 001_add_3d_tables completed")

if __name__ == '__main__':
    upgrade()
```

### 5.2 CZML Generator Service

#### 5.2.1 `services/czml_generator.py` (Core Logic)

```python
"""
ULG Flight Data → CZML Converter
Generates Cesium-compatible time-series data
"""
from pathlib import Path
from typing import Dict, List, Any
import json
import hashlib
from datetime import datetime, timezone
import pandas as pd
from czml3 import Document, Packet, Preamble
from czml3.properties import (
    Position, Color, Material, PolylineGradientMaterial,
    Billboard, Label, Path
)
from czml3.types import IntervalValue, TimeInterval, Cartesian3Value

class CZMLGenerator:
    """
    Converts ULG flight data to CZML format

    Features:
    - Altitude-based color gradient
    - Time interpolation
    - Metadata properties
    """

    def __init__(self, session_id: str, ulg_file_path: Path):
        self.session_id = session_id
        self.ulg_file_path = ulg_file_path
        self.flight_data = None
        self.czml_document = None

    def load_flight_data(self) -> pd.DataFrame:
        """Load ULG data from CSV (processed by existing analyzer)"""
        # Reuse existing ULG parser
        from flight_data_analyzer import FlightDataAnalyzer

        analyzer = FlightDataAnalyzer(str(self.ulg_file_path))
        df = analyzer.get_processed_dataframe()

        # Ensure required columns
        required_cols = ['timestamp', 'latitude', 'longitude', 'altitude']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns: {required_cols}")

        self.flight_data = df
        return df

    def calculate_altitude_color(self, altitude: float, min_alt: float, max_alt: float) -> List[int]:
        """
        Map altitude to RGBA color (Viridis colormap)

        Args:
            altitude: Current altitude (meters)
            min_alt: Minimum altitude in dataset
            max_alt: Maximum altitude in dataset

        Returns:
            [R, G, B, A] values (0-255)
        """
        # Normalize altitude to [0, 1]
        normalized = (altitude - min_alt) / (max_alt - min_alt) if max_alt > min_alt else 0.5

        # Viridis colormap approximation
        # Low altitude (0.0): Purple [68, 1, 84, 255]
        # Mid altitude (0.5): Green [33, 144, 140, 255]
        # High altitude (1.0): Yellow [253, 231, 37, 255]

        if normalized < 0.5:
            # Purple to Green
            t = normalized * 2
            r = int(68 + (33 - 68) * t)
            g = int(1 + (144 - 1) * t)
            b = int(84 + (140 - 84) * t)
        else:
            # Green to Yellow
            t = (normalized - 0.5) * 2
            r = int(33 + (253 - 33) * t)
            g = int(144 + (231 - 144) * t)
            b = int(140 + (37 - 140) * t)

        return [r, g, b, 255]

    def generate_czml(self) -> str:
        """
        Generate CZML document

        Returns:
            JSON string of CZML document
        """
        if self.flight_data is None:
            self.load_flight_data()

        df = self.flight_data

        # Calculate time range
        start_time = df['timestamp'].min()
        end_time = df['timestamp'].max()
        duration = (end_time - start_time).total_seconds()

        # Calculate altitude range
        min_altitude = df['altitude'].min()
        max_altitude = df['altitude'].max()

        # Create CZML document
        packets = []

        # 1. Document preamble
        preamble = Preamble(
            name=f"Flight {self.session_id}",
            clock=IntervalValue(
                start=start_time.isoformat(),
                end=end_time.isoformat(),
                currentTime=start_time.isoformat(),
                multiplier=1,
                range="LOOP_STOP",
                step="SYSTEM_CLOCK_MULTIPLIER"
            )
        )
        packets.append(preamble)

        # 2. Flight path entity
        position_values = []

        for _, row in df.iterrows():
            # Time in seconds since start
            time_offset = (row['timestamp'] - start_time).total_seconds()

            # Position: [time, longitude, latitude, altitude]
            position_values.extend([
                time_offset,
                row['longitude'],
                row['latitude'],
                row['altitude']
            ])

        flight_packet = Packet(
            id=f"flight_{self.session_id}",
            name=f"Flight Path {self.session_id}",
            availability=TimeInterval(start=start_time, end=end_time),
            position=Position(
                epoch=start_time.isoformat(),
                cartographicDegrees=position_values,
                interpolationAlgorithm="LAGRANGE",
                interpolationDegree=2
            ),
            path=Path(
                show=True,
                width=3,
                material=Material(
                    solidColor=Color(rgba=[255, 0, 0, 255])  # Red (Phase 1: solid color)
                    # Phase 2: Use PolylineGradientMaterial for altitude colors
                ),
                resolution=60,
                leadTime=0,
                trailTime=3600  # Show 1 hour trail
            ),
            billboard=Billboard(
                image="/aircraft_icon.png",  # Optional: 2D icon
                scale=0.5,
                show=True
            ),
            label=Label(
                text=f"Flight {self.session_id}",
                font="12pt sans-serif",
                fillColor=Color(rgba=[255, 255, 255, 255]),
                outlineColor=Color(rgba=[0, 0, 0, 255]),
                outlineWidth=2,
                pixelOffset=Cartesian3Value(values=[0, -30, 0]),
                show=False  # Hidden by default
            ),
            properties={
                "session_id": self.session_id,
                "min_altitude": min_altitude,
                "max_altitude": max_altitude,
                "duration_seconds": duration,
                "total_points": len(df)
            }
        )
        packets.append(flight_packet)

        # 3. Create CZML document
        document = Document(packets=packets)
        czml_json = document.dumps()

        self.czml_document = json.loads(czml_json)
        return czml_json

    def save_to_cache(self, czml_json: str) -> None:
        """Save generated CZML to database cache"""
        from models.database import get_db

        # Calculate file hash for cache invalidation
        file_hash = hashlib.md5(self.ulg_file_path.read_bytes()).hexdigest()

        df = self.flight_data
        min_altitude = float(df['altitude'].min())
        max_altitude = float(df['altitude'].max())
        duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
        total_points = len(df)

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO flight_3d_data
            (session_id, czml_data, geometry_hash, min_altitude, max_altitude, duration_seconds, total_points, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (self.session_id, czml_json, file_hash, min_altitude, max_altitude, duration, total_points))

        conn.commit()
        conn.close()

    @staticmethod
    def load_from_cache(session_id: str) -> str | None:
        """Load CZML from database cache"""
        from models.database import get_db

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('SELECT czml_data FROM flight_3d_data WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()

        conn.close()

        return row['czml_data'] if row else None

# Example usage
if __name__ == '__main__':
    generator = CZMLGenerator(
        session_id='test_session_123',
        ulg_file_path=Path('/path/to/flight.ulg')
    )

    czml = generator.generate_czml()
    print(f"Generated CZML: {len(czml)} bytes")

    generator.save_to_cache(czml)
    print("✅ Saved to cache")
```

### 5.3 REST API Endpoints

#### 5.3.1 `api/3d/__init__.py`

```python
"""
3D Visualization API Blueprint
"""
from flask import Blueprint

bp_3d = Blueprint('3d', __name__, url_prefix='/api/3d')

from . import flights, czml
```

#### 5.3.2 `api/3d/flights.py`

```python
"""
Flight data endpoints for 3D visualization
"""
from flask import jsonify, request
from pathlib import Path
from . import bp_3d
from models.database import get_db
from services.czml_generator import CZMLGenerator
import config

@bp_3d.route('/flights/<session_id>', methods=['GET'])
def get_flight_data(session_id: str):
    """
    Get flight data for 3D visualization

    Response:
    {
        "session_id": "abc123",
        "name": "Flight 2024-02-06",
        "created_at": "2024-02-06T10:30:00Z",
        "metadata": {
            "duration_seconds": 1250.5,
            "total_points": 5432,
            "min_altitude": 5.2,
            "max_altitude": 123.7
        },
        "czml_url": "/api/3d/czml/abc123"
    }
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get session info
    cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
    session = cursor.fetchone()

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # Get 3D data metadata
    cursor.execute('SELECT * FROM flight_3d_data WHERE session_id = ?', (session_id,))
    flight_3d = cursor.fetchone()

    conn.close()

    response = {
        'session_id': session['id'],
        'name': session['name'],
        'created_at': session['created_at'],
        'metadata': {
            'duration_seconds': flight_3d['duration_seconds'] if flight_3d else None,
            'total_points': flight_3d['total_points'] if flight_3d else None,
            'min_altitude': flight_3d['min_altitude'] if flight_3d else None,
            'max_altitude': flight_3d['max_altitude'] if flight_3d else None
        },
        'czml_url': f'/api/3d/czml/{session_id}'
    }

    return jsonify(response), 200

@bp_3d.route('/czml/<session_id>', methods=['GET'])
def get_czml(session_id: str):
    """
    Get CZML data for session (cached or generate)

    Query Parameters:
    - force_regenerate: bool (default: false)

    Response:
    CZML JSON array
    """
    force_regenerate = request.args.get('force_regenerate', 'false').lower() == 'true'

    # Try cache first
    if not force_regenerate:
        cached_czml = CZMLGenerator.load_from_cache(session_id)
        if cached_czml:
            return cached_czml, 200, {'Content-Type': 'application/json'}

    # Generate CZML
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT file_paths FROM sessions WHERE id = ?', (session_id,))
    session = cursor.fetchone()
    conn.close()

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    import json
    file_paths = json.loads(session['file_paths'])
    ulg_file = Path(config.UPLOAD_FOLDER) / session_id / file_paths.get('ulg')

    if not ulg_file.exists():
        return jsonify({'error': 'ULG file not found'}), 404

    try:
        generator = CZMLGenerator(session_id, ulg_file)
        czml_json = generator.generate_czml()
        generator.save_to_cache(czml_json)

        return czml_json, 200, {'Content-Type': 'application/json'}

    except Exception as e:
        return jsonify({'error': f'CZML generation failed: {str(e)}'}), 500

@bp_3d.route('/flights', methods=['GET'])
def list_flights():
    """
    List all flights with 3D data available

    Response:
    {
        "flights": [
            {
                "session_id": "abc123",
                "name": "Flight 2024-02-06",
                "created_at": "2024-02-06T10:30:00Z",
                "total_points": 5432
            }
        ],
        "total": 10
    }
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.id, s.name, s.created_at, f.total_points
        FROM sessions s
        LEFT JOIN flight_3d_data f ON s.id = f.session_id
        WHERE s.status = 'completed'
        ORDER BY s.created_at DESC
        LIMIT 50
    ''')

    flights = [
        {
            'session_id': row['id'],
            'name': row['name'],
            'created_at': row['created_at'],
            'total_points': row['total_points']
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    return jsonify({
        'flights': flights,
        'total': len(flights)
    }), 200
```

#### 5.3.3 Register Blueprint in `app.py`

```python
# app.py (existing file, add these lines)

from api.3d import bp_3d  # NEW

# ... existing blueprints ...

app.register_blueprint(bp_3d)  # NEW
```

---

## 6. Core 3D Components

### 6.1 Custom React Hooks

#### 6.1.1 `hooks/useCesiumViewer.ts`

```typescript
/**
 * Cesium Viewer initialization and lifecycle management
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import * as Cesium from 'cesium';

interface UseCesiumViewerOptions {
  containerId: string;
  cesiumIonAccessToken?: string;
  enableTerrain?: boolean;
  enableBuildings?: boolean;
}

interface UseCesiumViewerReturn {
  viewer: Cesium.Viewer | null;
  isReady: boolean;
  error: Error | null;
  resetCamera: () => void;
}

export function useCesiumViewer({
  containerId,
  cesiumIonAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN,
  enableTerrain = true,
  enableBuildings = true
}: UseCesiumViewerOptions): UseCesiumViewerReturn {
  const [viewer, setViewer] = useState<Cesium.Viewer | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const homePositionRef = useRef<Cesium.Cartesian3 | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function initializeViewer() {
      try {
        // Set Cesium Ion token
        if (cesiumIonAccessToken) {
          Cesium.Ion.defaultAccessToken = cesiumIonAccessToken;
        }

        // Create viewer
        const cesiumViewer = new Cesium.Viewer(containerId, {
          // Terrain
          terrainProvider: enableTerrain
            ? await Cesium.createWorldTerrainAsync({
                requestWaterMask: true,
                requestVertexNormals: true
              })
            : undefined,

          // Imagery
          baseLayerPicker: false,
          imageryProvider: new Cesium.IonImageryProvider({ assetId: 2 }),

          // UI Controls (hide default, use custom)
          animation: false,
          timeline: false,
          homeButton: false,
          geocoder: false,
          sceneModePicker: false,
          navigationHelpButton: false,
          fullscreenButton: false,

          // Scene options
          sceneMode: Cesium.SceneMode.SCENE3D,
          requestRenderMode: true,  // Render only when needed (performance)
          maximumRenderTimeChange: Infinity
        });

        // Add OSM Buildings
        if (enableBuildings) {
          const osmBuildingsTileset = await Cesium.createOsmBuildingsAsync();
          cesiumViewer.scene.primitives.add(osmBuildingsTileset);
        }

        // Configure scene
        cesiumViewer.scene.globe.enableLighting = false;  // No shadows (performance)
        cesiumViewer.scene.globe.depthTestAgainstTerrain = false;

        // Store initial camera position
        homePositionRef.current = cesiumViewer.camera.position.clone();

        if (isMounted) {
          viewerRef.current = cesiumViewer;
          setViewer(cesiumViewer);
          setIsReady(true);
        }
      } catch (err) {
        console.error('Cesium initialization error:', err);
        if (isMounted) {
          setError(err as Error);
        }
      }
    }

    initializeViewer();

    return () => {
      isMounted = false;
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        viewerRef.current.destroy();
      }
    };
  }, [containerId, cesiumIonAccessToken, enableTerrain, enableBuildings]);

  const resetCamera = useCallback(() => {
    if (viewer && homePositionRef.current) {
      viewer.camera.flyTo({
        destination: homePositionRef.current,
        duration: 2
      });
    }
  }, [viewer]);

  return { viewer, isReady, error, resetCamera };
}
```

#### 6.1.2 `hooks/useFlightData.ts`

```typescript
/**
 * Flight data fetching and caching
 */
import { useEffect, useState } from 'react';
import type { FlightData, CZMLDocument } from '@types/flight';

interface UseFlightDataOptions {
  sessionId: string;
  enabled?: boolean;
}

interface UseFlightDataReturn {
  flightData: FlightData | null;
  czmlData: CZMLDocument | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useFlightData({
  sessionId,
  enabled = true
}: UseFlightDataOptions): UseFlightDataReturn {
  const [flightData, setFlightData] = useState<FlightData | null>(null);
  const [czmlData, setCzmlData] = useState<CZMLDocument | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = async () => {
    if (!enabled) return;

    setLoading(true);
    setError(null);

    try {
      // 1. Fetch flight metadata
      const metadataResponse = await fetch(`/api/3d/flights/${sessionId}`);
      if (!metadataResponse.ok) {
        throw new Error(`Failed to fetch flight metadata: ${metadataResponse.statusText}`);
      }
      const metadata = await metadataResponse.json();

      // 2. Fetch CZML data
      const czmlResponse = await fetch(`/api/3d/czml/${sessionId}`);
      if (!czmlResponse.ok) {
        throw new Error(`Failed to fetch CZML data: ${czmlResponse.statusText}`);
      }
      const czml = await czmlResponse.json();

      setFlightData(metadata);
      setCzmlData(czml);
    } catch (err) {
      console.error('Flight data fetch error:', err);
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [sessionId, enabled]);

  return {
    flightData,
    czmlData,
    loading,
    error,
    refetch: fetchData
  };
}
```

#### 6.1.3 `hooks/useEntities.ts`

```typescript
/**
 * Cesium entity management
 */
import { useEffect, useCallback } from 'react';
import * as Cesium from 'cesium';
import type { CZMLDocument } from '@types/flight';

interface UseEntitiesOptions {
  viewer: Cesium.Viewer | null;
  czmlData: CZMLDocument | null;
  enabled?: boolean;
}

interface UseEntitiesReturn {
  dataSource: Cesium.CzmlDataSource | null;
  clearEntities: () => void;
  showFlightPath: (show: boolean) => void;
}

export function useEntities({
  viewer,
  czmlData,
  enabled = true
}: UseEntitiesOptions): UseEntitiesReturn {
  const [dataSource, setDataSource] = useState<Cesium.CzmlDataSource | null>(null);

  useEffect(() => {
    if (!viewer || !czmlData || !enabled) return;

    let czmlDataSource: Cesium.CzmlDataSource | null = null;

    async function loadCZML() {
      try {
        czmlDataSource = await Cesium.CzmlDataSource.load(czmlData);
        viewer!.dataSources.add(czmlDataSource);
        setDataSource(czmlDataSource);

        // Zoom to flight path
        viewer!.zoomTo(czmlDataSource);
      } catch (err) {
        console.error('CZML loading error:', err);
      }
    }

    loadCZML();

    return () => {
      if (czmlDataSource && viewer && !viewer.isDestroyed()) {
        viewer.dataSources.remove(czmlDataSource, true);
      }
    };
  }, [viewer, czmlData, enabled]);

  const clearEntities = useCallback(() => {
    if (viewer && dataSource) {
      viewer.dataSources.remove(dataSource, true);
      setDataSource(null);
    }
  }, [viewer, dataSource]);

  const showFlightPath = useCallback((show: boolean) => {
    if (dataSource) {
      dataSource.show = show;
    }
  }, [dataSource]);

  return {
    dataSource,
    clearEntities,
    showFlightPath
  };
}
```

### 6.2 React Components

#### 6.2.1 `components/Cesium/CesiumViewer.tsx` (Main Component)

```typescript
/**
 * Main 3D Cesium Viewer Component
 */
import React from 'react';
import { useCesiumViewer } from '@hooks/useCesiumViewer';
import { useFlightData } from '@hooks/useFlightData';
import { useEntities } from '@hooks/useEntities';
import { LoadingOverlay } from './LoadingOverlay';
import { CameraControls } from './CameraControls';
import { ErrorBoundary } from '@components/UI/ErrorBoundary';
import './CesiumViewer.css';

interface CesiumViewerProps {
  sessionId: string;
  className?: string;
}

export const CesiumViewer: React.FC<CesiumViewerProps> = ({
  sessionId,
  className = ''
}) => {
  const containerId = 'cesium-container';

  // Initialize Cesium viewer
  const { viewer, isReady, error: viewerError, resetCamera } = useCesiumViewer({
    containerId,
    enableTerrain: true,
    enableBuildings: true
  });

  // Fetch flight data
  const {
    flightData,
    czmlData,
    loading: dataLoading,
    error: dataError
  } = useFlightData({ sessionId, enabled: isReady });

  // Manage entities
  const { showFlightPath } = useEntities({
    viewer,
    czmlData,
    enabled: isReady && !!czmlData
  });

  // Combined loading state
  const loading = !isReady || dataLoading;
  const error = viewerError || dataError;

  return (
    <ErrorBoundary>
      <div className={`cesium-viewer-wrapper ${className}`}>
        {/* Cesium container */}
        <div
          id={containerId}
          className="cesium-container"
          style={{ width: '100%', height: '100%' }}
        />

        {/* Loading overlay */}
        {loading && (
          <LoadingOverlay
            message={!isReady ? 'Initializing 3D globe...' : 'Loading flight data...'}
            progress={!isReady ? 50 : 75}
          />
        )}

        {/* Error display */}
        {error && (
          <div className="cesium-error-overlay">
            <h3>Error Loading Visualization</h3>
            <p>{error.message}</p>
            <button onClick={() => window.location.reload()}>
              Reload Page
            </button>
          </div>
        )}

        {/* Camera controls */}
        {isReady && !loading && (
          <CameraControls
            viewer={viewer}
            onReset={resetCamera}
            onToggleFlightPath={(show) => showFlightPath(show)}
          />
        )}

        {/* Flight info panel (optional) */}
        {flightData && (
          <div className="cesium-info-panel">
            <h4>{flightData.name}</h4>
            <p>Duration: {flightData.metadata.duration_seconds}s</p>
            <p>Points: {flightData.metadata.total_points}</p>
            <p>Altitude: {flightData.metadata.min_altitude?.toFixed(1)}m - {flightData.metadata.max_altitude?.toFixed(1)}m</p>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
};
```

#### 6.2.2 `components/Cesium/LoadingOverlay.tsx`

```typescript
/**
 * Loading state overlay
 */
import React from 'react';
import './LoadingOverlay.css';

interface LoadingOverlayProps {
  message?: string;
  progress?: number;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  message = 'Loading...',
  progress
}) => {
  return (
    <div className="loading-overlay">
      <div className="loading-content">
        <div className="loading-spinner" />
        <p className="loading-message">{message}</p>
        {progress !== undefined && (
          <div className="loading-progress-bar">
            <div
              className="loading-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
};
```

#### 6.2.3 `components/Cesium/CameraControls.tsx`

```typescript
/**
 * Camera control buttons
 */
import React from 'react';
import * as Cesium from 'cesium';
import { Button } from '@components/UI/Button';
import { Home, Eye, EyeOff } from 'lucide-react';  // Icon library

interface CameraControlsProps {
  viewer: Cesium.Viewer | null;
  onReset: () => void;
  onToggleFlightPath: (show: boolean) => void;
}

export const CameraControls: React.FC<CameraControlsProps> = ({
  viewer,
  onReset,
  onToggleFlightPath
}) => {
  const [flightPathVisible, setFlightPathVisible] = React.useState(true);

  const handleToggleFlightPath = () => {
    const newState = !flightPathVisible;
    setFlightPathVisible(newState);
    onToggleFlightPath(newState);
  };

  return (
    <div className="camera-controls">
      <Button
        onClick={onReset}
        title="Reset camera to home position"
        className="camera-control-btn"
      >
        <Home size={20} />
      </Button>

      <Button
        onClick={handleToggleFlightPath}
        title={flightPathVisible ? 'Hide flight path' : 'Show flight path'}
        className="camera-control-btn"
      >
        {flightPathVisible ? <Eye size={20} /> : <EyeOff size={20} />}
      </Button>
    </div>
  );
};
```

### 6.3 TypeScript Type Definitions

#### 6.3.1 `types/flight.ts`

```typescript
/**
 * Flight data type definitions
 */

export interface FlightMetadata {
  duration_seconds: number | null;
  total_points: number | null;
  min_altitude: number | null;
  max_altitude: number | null;
}

export interface FlightData {
  session_id: string;
  name: string;
  created_at: string;
  metadata: FlightMetadata;
  czml_url: string;
}

export interface CZMLDocument {
  id: string;
  version: string;
  name?: string;
  clock?: CZMLClock;
  [key: string]: any;  // CZML packets are dynamic
}

export interface CZMLClock {
  interval: string;
  currentTime: string;
  multiplier: number;
  range: 'LOOP_STOP' | 'UNBOUNDED' | 'CLAMPED';
  step: 'SYSTEM_CLOCK_MULTIPLIER' | 'SYSTEM_CLOCK' | 'TICK_DEPENDENT';
}

export interface FlightListResponse {
  flights: {
    session_id: string;
    name: string;
    created_at: string;
    total_points: number | null;
  }[];
  total: number;
}
```

---

## 7. Code Quality Infrastructure

### 7.1 Testing Setup

#### 7.1.1 `tests/setup.ts` (Vitest Configuration)

```typescript
/**
 * Vitest test setup
 */
import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock Cesium (heavy library, not needed in unit tests)
vi.mock('cesium', () => ({
  Viewer: vi.fn(),
  Ion: {
    defaultAccessToken: ''
  },
  // Add other mocks as needed
}));
```

#### 7.1.2 `vitest.config.ts`

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react-swc';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData/*'
      ]
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@services': path.resolve(__dirname, './src/services'),
      '@store': path.resolve(__dirname, './src/store'),
      '@types': path.resolve(__dirname, './src/types')
    }
  }
});
```

#### 7.1.3 Example Unit Test: `tests/unit/hooks/useCesiumViewer.test.ts`

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useCesiumViewer } from '@hooks/useCesiumViewer';

describe('useCesiumViewer', () => {
  beforeEach(() => {
    // Reset DOM
    document.body.innerHTML = '<div id="test-container"></div>';
  });

  it('should initialize with null viewer and not ready', () => {
    const { result } = renderHook(() =>
      useCesiumViewer({ containerId: 'test-container' })
    );

    expect(result.current.viewer).toBeNull();
    expect(result.current.isReady).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should become ready after initialization', async () => {
    const { result } = renderHook(() =>
      useCesiumViewer({ containerId: 'test-container' })
    );

    await waitFor(() => {
      expect(result.current.isReady).toBe(true);
    }, { timeout: 5000 });

    expect(result.current.viewer).not.toBeNull();
  });

  it('should clean up viewer on unmount', async () => {
    const { result, unmount } = renderHook(() =>
      useCesiumViewer({ containerId: 'test-container' })
    );

    await waitFor(() => {
      expect(result.current.isReady).toBe(true);
    });

    const viewerDestroySpy = vi.spyOn(result.current.viewer!, 'destroy');
    unmount();

    expect(viewerDestroySpy).toHaveBeenCalled();
  });
});
```

### 7.2 Pre-commit Hooks (Husky + Lint-Staged)

#### 7.2.1 `.husky/pre-commit`

```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

# Run lint-staged
npx lint-staged

# Run type checking
npm run type-check
```

#### 7.2.2 `package.json` (lint-staged config)

```json
{
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write",
      "vitest related --run"
    ],
    "*.{css,md,json}": [
      "prettier --write"
    ]
  }
}
```

### 7.3 GitHub Actions CI/CD

#### 7.3.1 `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npm run type-check

      - name: Unit tests
        run: npm run test:coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/coverage-final.json

      - name: Build
        run: npm run build

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: Run E2E tests
        run: npm run test:e2e

      - name: Upload test results
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-results
          path: playwright-report/
```

---

## 8. Development Workflow

### 8.1 Environment Variables

#### 8.1.1 `.env.example` (Template)

```bash
# Cesium Ion Access Token (Sign up at https://ion.cesium.com/)
VITE_CESIUM_ION_TOKEN=your_token_here

# API Base URL (Development)
VITE_API_BASE_URL=http://localhost:5002

# Environment
VITE_NODE_ENV=development

# Debugging
VITE_DEBUG_MODE=false
```

#### 8.1.2 `.env.development` (Local Development)

```bash
VITE_CESIUM_ION_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
VITE_API_BASE_URL=http://localhost:5002
VITE_NODE_ENV=development
VITE_DEBUG_MODE=true
```

### 8.2 Development Scripts

#### 8.2.1 `scripts/dev.sh` (Start All Services)

```bash
#!/bin/bash

echo "🚀 Starting Starlink 3D Visualization Development Environment"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
  lsof -i :$1 > /dev/null 2>&1
}

# Kill existing processes
echo -e "${BLUE}Checking for existing processes...${NC}"
if check_port 5002; then
  echo "❌ Port 5002 in use, stopping Flask server..."
  lsof -ti:5002 | xargs kill -9 2>/dev/null
fi

if check_port 5173; then
  echo "❌ Port 5173 in use, stopping Vite dev server..."
  lsof -ti:5173 | xargs kill -9 2>/dev/null
fi

# Start Flask backend
echo -e "${GREEN}Starting Flask backend (port 5002)...${NC}"
cd /Users/dykim/dev/starlink/analysis
source venv/bin/activate
python app.py &
FLASK_PID=$!
echo "✅ Flask started (PID: $FLASK_PID)"

# Wait for Flask to start
sleep 3

# Start Vite frontend
echo -e "${GREEN}Starting Vite frontend (port 5173)...${NC}"
cd /Users/dykim/dev/starlink/analysis/frontend
npm run dev &
VITE_PID=$!
echo "✅ Vite started (PID: $VITE_PID)"

# Wait for Vite to start
sleep 5

echo ""
echo -e "${GREEN}✅ Development environment ready!${NC}"
echo ""
echo "📋 Services:"
echo "  - Frontend: http://localhost:5173"
echo "  - Backend:  http://localhost:5002"
echo ""
echo "🛑 To stop all services: Ctrl+C"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $FLASK_PID $VITE_PID 2>/dev/null; exit" SIGINT SIGTERM

wait
```

#### 8.2.2 `scripts/build.sh` (Production Build)

```bash
#!/bin/bash

echo "🏗️ Building for Production"

# Frontend build
cd /Users/dykim/dev/starlink/analysis/frontend
npm run lint
npm run type-check
npm run build

echo "✅ Frontend build complete: frontend/dist"

# Backend (no build needed, Python)
echo "✅ Backend ready"

echo ""
echo "📦 Production build complete!"
echo "Deploy contents of frontend/dist to web server"
```

### 8.3 VS Code Configuration

#### 8.3.1 `.vscode/settings.json`

```json
{
  "typescript.tsdk": "node_modules/typescript/lib",
  "typescript.enablePromptUseWorkspaceTsdk": true,
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "eslint.validate": [
    "javascript",
    "javascriptreact",
    "typescript",
    "typescriptreact"
  ],
  "files.associations": {
    "*.css": "tailwindcss"
  },
  "tailwindCSS.experimental.classRegex": [
    ["cva\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"],
    ["cn\\(([^)]*)\\)", "(?:'|\"|`)([^']*)(?:'|\"|`)"]
  ]
}
```

#### 8.3.2 `.vscode/launch.json` (Debugging)

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Frontend: Chrome Debug",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}/frontend/src",
      "sourceMapPathOverrides": {
        "webpack:///src/*": "${webRoot}/*"
      }
    },
    {
      "name": "Backend: Flask Debug",
      "type": "python",
      "request": "launch",
      "module": "flask",
      "env": {
        "FLASK_APP": "app.py",
        "FLASK_ENV": "development",
        "FLASK_DEBUG": "1"
      },
      "args": [
        "run",
        "--no-debugger",
        "--no-reload",
        "--port",
        "5002"
      ],
      "jinja": true,
      "justMyCode": false,
      "cwd": "${workspaceFolder}/analysis"
    }
  ]
}
```

---

## 9. Risk Mitigation Strategy

### 9.1 Performance Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Cesium bundle > 2MB** | High | Medium | - CDN hosting for Cesium assets<br>- Code splitting (manual chunks)<br>- Lazy load 3D viewer |
| **Frame rate < 60 FPS** | Medium | High | - Limit initial points to 5,000<br>- Implement data downsampling (LTTB)<br>- Use requestRenderMode |
| **Memory leak** | Medium | High | - Proper entity cleanup in useEffect<br>- Destroy viewer on unmount<br>- Monitor with Chrome DevTools |

**Mitigation Actions**:
1. **Bundle Size Monitoring**: Add webpack-bundle-analyzer
2. **Performance Budget**: < 2MB gzipped (enforce in CI)
3. **E2E Performance Tests**: Playwright with performance metrics

### 9.2 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **CZML generation errors** | Medium | High | - Extensive unit tests (czmlGenerator)<br>- Schema validation (Pydantic)<br>- Fallback to simple polyline |
| **Cesium API breaking changes** | Low | Medium | - Pin exact version (1.120.0)<br>- Test before upgrading<br>- Monitor release notes |
| **Browser compatibility** | Low | Low | - WebGL 2 feature detection<br>- Fallback message for unsupported browsers |

**Mitigation Actions**:
1. **CZML Validation**: JSON schema validation before sending to frontend
2. **Browser Support Matrix**: Test on Chrome 90+, Firefox 88+, Safari 14+
3. **Error Boundaries**: Catch React errors gracefully

### 9.3 UX Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Users confused by 3D controls** | High | Medium | - Add tutorial overlay (first visit)<br>- Tooltips on all controls<br>- "Reset camera" button prominent |
| **Mobile performance poor** | High | Medium | - Detect mobile, show warning<br>- Reduce quality (lower LOD)<br>- Offer 2D fallback link |

**Mitigation Actions**:
1. **Onboarding Tutorial**: First-time user walkthrough (skip button)
2. **Mobile Detection**: Show "Desktop recommended" banner
3. **Accessibility**: Keyboard navigation (Tab, Enter, Arrow keys)

---

## 10. Daily Implementation Schedule

### Day 1-2: Project Setup (Critical Path)

**Day 1 Morning (4h)**:
- [ ] Create `frontend/` directory structure
- [ ] Initialize `package.json` with exact versions
- [ ] Run `npm install` (verify no errors)
- [ ] Configure `tsconfig.json`, `vite.config.ts`, `tailwind.config.js`
- [ ] Create `.env.example` and `.env.development`
- [ ] Sign up for Cesium Ion token, add to `.env`

**Day 1 Afternoon (4h)**:
- [ ] Setup ESLint + Prettier configs
- [ ] Install Husky + lint-staged
- [ ] Create basic `App.tsx` (Hello World)
- [ ] Verify Vite dev server runs (`npm run dev`)
- [ ] Verify build works (`npm run build`)

**Day 2 Morning (4h)**:
- [ ] Backend: Create `api/3d/` blueprint structure
- [ ] Backend: Add `flight_3d_data` table to database
- [ ] Backend: Run migration script
- [ ] Backend: Create `services/czml_generator.py` skeleton
- [ ] Test: Generate CZML from existing ULG file (manual script)

**Day 2 Afternoon (4h)**:
- [ ] Backend: Implement `/api/3d/flights/<session_id>` endpoint
- [ ] Backend: Implement `/api/3d/czml/<session_id>` endpoint
- [ ] Backend: Register 3D blueprint in `app.py`
- [ ] Test: `curl http://localhost:5002/api/3d/flights/test` (verify response)

**Day 2 Deliverable**: Working API endpoints serving CZML data

---

### Day 3-4: Core 3D Components

**Day 3 Morning (4h)**:
- [ ] Frontend: Implement `useCesiumViewer` hook
- [ ] Frontend: Create `CesiumViewer.tsx` component
- [ ] Frontend: Add Cesium container div
- [ ] Test: Verify globe renders (no errors in console)

**Day 3 Afternoon (4h)**:
- [ ] Frontend: Implement `useFlightData` hook
- [ ] Frontend: Implement `useEntities` hook
- [ ] Frontend: Connect hooks to `CesiumViewer`
- [ ] Test: Load CZML data, verify flight path appears

**Day 4 Morning (4h)**:
- [ ] Frontend: Implement `LoadingOverlay` component
- [ ] Frontend: Implement `CameraControls` component
- [ ] Frontend: Add error boundary
- [ ] Test: Verify loading states work correctly

**Day 4 Afternoon (4h)**:
- [ ] Frontend: Implement `ErrorBoundary` component
- [ ] Frontend: Add flight info panel (optional)
- [ ] Frontend: Style components with Tailwind
- [ ] Test: End-to-end flow (select session → view 3D)

**Day 4 Deliverable**: Fully functional 3D viewer displaying flight path

---

### Day 5-6: CZML Enhancement & Color Mapping

**Day 5 Morning (4h)**:
- [ ] Backend: Implement altitude color calculation (Viridis)
- [ ] Backend: Add color gradient to CZML path material
- [ ] Backend: Cache CZML in database
- [ ] Test: Verify color gradient appears correctly

**Day 5 Afternoon (4h)**:
- [ ] Frontend: Add color legend component
- [ ] Frontend: Display altitude range in UI
- [ ] Frontend: Add layer toggle (flight path, buildings, terrain)
- [ ] Test: Verify toggles work

**Day 6 Full Day (8h)**:
- [ ] Performance testing: Load 10,000+ point dataset
- [ ] Optimize: Implement data downsampling if needed
- [ ] Optimize: Code splitting (Cesium in separate chunk)
- [ ] Optimize: Enable requestRenderMode in Cesium
- [ ] Test: Verify 60 FPS maintained
- [ ] Test: Verify bundle size < 2MB gzipped

**Day 6 Deliverable**: Performance-optimized 3D viewer with color-coded flight paths

---

### Day 7-8: Testing & Documentation

**Day 7 Morning (4h)**:
- [ ] Write unit tests: `useCesiumViewer.test.ts`
- [ ] Write unit tests: `useFlightData.test.ts`
- [ ] Write unit tests: `czml_generator.test.py` (backend)
- [ ] Run tests, achieve 80%+ coverage

**Day 7 Afternoon (4h)**:
- [ ] Write integration tests: `CesiumViewer.test.tsx`
- [ ] Setup Playwright E2E tests
- [ ] Write E2E test: Load session, verify 3D renders
- [ ] All tests passing

**Day 8 Morning (4h)**:
- [ ] Write `README.md` (frontend)
- [ ] Write `docs/API.md` (API endpoints documentation)
- [ ] Write `docs/ARCHITECTURE.md` (system architecture)
- [ ] Write `docs/DEVELOPMENT.md` (development guide)

**Day 8 Afternoon (4h)**:
- [ ] Setup CI/CD (GitHub Actions)
- [ ] Create production build script
- [ ] Final QA: Test on Chrome, Firefox, Safari
- [ ] Final QA: Test on tablet (iPad)

**Day 8 Deliverable**: Fully tested, documented, production-ready Phase 1

---

### Day 9-10: Polish & Handoff

**Day 9 Full Day (8h)**:
- [ ] UI polish: Consistent spacing, colors, typography
- [ ] Accessibility: Keyboard navigation, ARIA labels
- [ ] Performance audit: Lighthouse score > 90
- [ ] Security audit: No console.log in production build
- [ ] Code review: Ensure no `any` types, no ESLint warnings

**Day 10 Full Day (8h)**:
- [ ] Create deployment guide
- [ ] Record demo video (screen recording)
- [ ] Handoff meeting: Demo to stakeholders
- [ ] Document known issues (if any)
- [ ] Plan Phase 2 features

**Day 10 Deliverable**: Production deployment + stakeholder approval

---

## 11. Acceptance Criteria Checklist

### 11.1 Functional Criteria

#### Core Functionality
- [ ] 3D globe renders with Cesium World Terrain
- [ ] OSM 3D Buildings visible (toggleable)
- [ ] Single flight path from ULG file displayed
- [ ] Flight path colored by altitude (gradient)
- [ ] Camera controls work (mouse rotate, zoom, pan)
- [ ] "Reset camera" button returns to home position
- [ ] Loading state shows during data fetch
- [ ] Error handling for missing sessions
- [ ] Error handling for invalid CZML

#### Data Integrity
- [ ] Flight path matches 2D Folium visualization (±10m accuracy)
- [ ] Timestamps align correctly (UTC timezone)
- [ ] Altitude values accurate (±1m)
- [ ] No missing data points (compare with ULG row count)

### 11.2 Performance Criteria

#### Load Time
- [ ] Initial globe load < 3 seconds (median, 4G)
- [ ] Flight path load < 2 seconds (5,000 points)
- [ ] Total time to interactive < 5 seconds

#### Runtime Performance
- [ ] 60 FPS sustained with 5,000 points
- [ ] 30+ FPS with 10,000 points
- [ ] Memory usage < 500MB after 5 minutes
- [ ] No memory leaks (stable memory over 10 minutes)

#### Bundle Size
- [ ] Total bundle < 2MB (gzipped)
- [ ] Initial chunk < 500KB
- [ ] Cesium chunk < 1.5MB

### 11.3 Code Quality Criteria

#### TypeScript
- [ ] 100% TypeScript in `src/` (no JavaScript files)
- [ ] Zero `any` types in application code (tests OK)
- [ ] Strict mode enabled, no type errors
- [ ] All public APIs have JSDoc comments

#### Linting & Formatting
- [ ] ESLint score > 95 (zero errors, < 5 warnings)
- [ ] Prettier formatting consistent (no format errors)
- [ ] No `console.log` in production build
- [ ] No commented-out code

#### Testing
- [ ] Unit test coverage > 80% (lines, branches)
- [ ] All hooks have unit tests
- [ ] All services have unit tests
- [ ] Integration test for main component
- [ ] E2E test for full user flow
- [ ] All tests passing in CI

### 11.4 Documentation Criteria

- [ ] README.md (frontend) complete
- [ ] API.md (endpoints documented)
- [ ] ARCHITECTURE.md (diagrams + explanations)
- [ ] DEVELOPMENT.md (setup instructions)
- [ ] Inline comments for complex logic
- [ ] Type definitions documented (JSDoc)

### 11.5 Security Criteria

- [ ] No API keys in source code (use .env)
- [ ] No sensitive data in console logs
- [ ] CORS properly configured
- [ ] Input validation on backend (Pydantic)
- [ ] SQL injection protection (parameterized queries)

### 11.6 Accessibility Criteria

- [ ] WCAG 2.1 Level A compliant
- [ ] Keyboard navigation works (Tab, Enter, Esc)
- [ ] ARIA labels on interactive elements
- [ ] Color contrast ratio > 4.5:1 (text)
- [ ] Focus indicators visible

### 11.7 Browser Compatibility

- [ ] Chrome 90+ (tested)
- [ ] Firefox 88+ (tested)
- [ ] Safari 14+ (tested)
- [ ] Edge 90+ (tested)
- [ ] Graceful fallback for WebGL 1-only browsers

---

## Appendix A: Quick Start Commands

```bash
# Clone repository (if needed)
cd /Users/dykim/dev/starlink/analysis

# Initialize frontend
mkdir frontend
cd frontend
npm init -y
npm install <paste dependencies from package.json>

# Setup environment
cp .env.example .env.development
# Edit .env.development, add Cesium Ion token

# Start development
./scripts/dev.sh

# Run tests
npm test

# Build for production
./scripts/build.sh
```

---

## Appendix B: Troubleshooting Guide

### Issue: Cesium fails to initialize

**Symptoms**: "Cesium is not defined" error

**Solutions**:
1. Verify `vite-plugin-cesium` is installed
2. Check `vite.config.ts` includes `cesium()` plugin
3. Clear Vite cache: `rm -rf node_modules/.vite`
4. Restart dev server

### Issue: CZML data not loading

**Symptoms**: Blank globe, no flight path

**Solutions**:
1. Check browser console for CORS errors
2. Verify backend API is running (port 5002)
3. Test API manually: `curl http://localhost:5002/api/3d/czml/<session_id>`
4. Check CZML validity: Paste into [CZML Validator](https://sandcastle.cesium.com/)

### Issue: Low FPS (< 30)

**Symptoms**: Choppy camera movement

**Solutions**:
1. Check point count: Reduce to < 5,000 for Phase 1
2. Enable `requestRenderMode` in Cesium viewer
3. Disable terrain temporarily: `enableTerrain: false`
4. Check GPU usage in Chrome Task Manager (Shift+Esc)

---

## Appendix C: Cesium Ion Token Setup

1. Go to [https://ion.cesium.com/signup](https://ion.cesium.com/signup)
2. Sign up for free account
3. Navigate to "Access Tokens"
4. Click "Create Token"
5. Name: "Starlink 3D Visualization"
6. Scopes: Select "assets:read" and "assets:list"
7. Copy token
8. Paste into `.env.development`:
   ```
   VITE_CESIUM_ION_TOKEN=eyJhbGciOiJI...
   ```

**Free Tier Limits**:
- 30,000 requests/month
- Sufficient for development and small deployments

---

## Appendix D: Architecture Diagrams

### Component Hierarchy

```
App
├── Router
│   └── Viewer3D (/3d/:sessionId)
│       ├── CesiumViewer
│       │   ├── Hooks: useCesiumViewer
│       │   ├── Hooks: useFlightData
│       │   └── Hooks: useEntities
│       ├── LoadingOverlay
│       ├── CameraControls
│       └── ErrorBoundary
└── (Future: Sidebar, Timeline, etc.)
```

### Data Flow Diagram

```
┌─────────┐     GET /api/3d/flights/:id     ┌─────────┐
│ Browser │ ───────────────────────────────> │  Flask  │
│         │                                   │         │
│         │ <─────────────────────────────── │         │
└─────────┘    { metadata, czml_url }        └─────────┘
     │                                             │
     │                                             │
     │         GET /api/3d/czml/:id               │
     │ ───────────────────────────────────────────>│
     │                                             │
     │                                        ┌────▼────┐
     │                                        │ CZML    │
     │                                        │ Cache   │
     │                                        │ (DB)    │
     │                                        └────┬────┘
     │                                             │
     │ <───────────────────────────────────────────┘
     │            CZML JSON array
     │
     ▼
┌─────────┐
│ Cesium  │ Parse CZML → Render Entities
│ Viewer  │
└─────────┘
```

---

**End of Phase 1 Implementation Plan**

**Next Steps After Phase 1**:
1. Phase 2: Time-based animation and playback controls
2. Phase 3: LTE base station visualization
3. Phase 4: Starlink satellite tracking

**Document Prepared By**: Claude Sonnet 4.5
**Review Status**: Ready for Developer Handoff
**Estimated Effort**: 10 business days (1 senior full-stack developer)
