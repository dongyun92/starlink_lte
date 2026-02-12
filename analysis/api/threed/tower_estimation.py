"""
High-Accuracy Cell Tower Position Estimation

Uses multiple methods to estimate LTE tower positions from drone GPS and signal strength data:
1. Trilateration with RSRP-to-distance path loss model
2. Weighted centroid with RSRP weighting
3. Top-N signal averaging
4. Hybrid consensus with confidence scoring
"""

import numpy as np
import pandas as pd
from scipy.optimize import least_squares


def rsrp_to_distance_m(rsrp_dbm: float, frequency_mhz: float = 1800, tx_power_dbm: float = 43) -> float:
    """
    Convert RSRP to estimated distance using Urban COST-231 Hata path loss model

    Args:
        rsrp_dbm: Received Signal Reference Power in dBm
        frequency_mhz: LTE frequency (default 1800 MHz for Band 3)
        tx_power_dbm: Base station transmission power (default 43 dBm)

    Returns:
        Estimated distance in meters

    Formula:
        PL(dB) = TX_power - RSRP
        PL = 46.3 + 33.9*log10(f) - 13.82*log10(hb) + [44.9 - 6.55*log10(hb)]*log10(d)
        d = 10^((PL - A) / B)
    """
    # Path loss = TX power - RX power
    path_loss = tx_power_dbm - rsrp_dbm

    # Urban COST-231 Hata parameters
    hb = 30  # Base station antenna height (m)
    A = 46.3 + 33.9 * np.log10(frequency_mhz) - 13.82 * np.log10(hb)
    B = 44.9 - 6.55 * np.log10(hb)

    # Solve for distance: d = 10^((PL - A) / B)
    distance_km = 10 ** ((path_loss - A) / B)
    distance_m = distance_km * 1000

    # Clamp to realistic range (50m ~ 10km)
    return max(50, min(distance_m, 10000))


def haversine_distance_m(lat1: float, lon1: float, alt1: float,
                        lat2: float, lon2: float, alt2: float) -> float:
    """
    Calculate 3D distance between two GPS points including altitude

    Args:
        lat1, lon1, alt1: First point (degrees, degrees, meters)
        lat2, lon2, alt2: Second point (degrees, degrees, meters)

    Returns:
        Distance in meters
    """
    # Horizontal distance using flat-earth approximation (accurate for <10km)
    dx = (lon2 - lon1) * 111320 * np.cos(np.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 110540
    dz = alt2 - alt1

    return np.sqrt(dx**2 + dy**2 + dz**2)


def estimate_tower_trilateration(cell_data: pd.DataFrame) -> dict:
    """
    Trilateration-based tower position estimation using least-squares optimization

    Args:
        cell_data: DataFrame with columns: latitude, longitude, altitude, lte_rsrp

    Returns:
        dict with keys: lat, lon, alt, method, confidence, uncertainty_m
        or None if estimation fails
    """
    # Use top 10 strongest signal points for trilateration
    top_points = cell_data.nlargest(min(10, len(cell_data)), 'lte_rsrp')

    if len(top_points) < 3:
        return None  # Need at least 3 points for trilateration

    # Convert RSRP to distances using path loss model
    distances = top_points['lte_rsrp'].apply(rsrp_to_distance_m).values
    lats = top_points['latitude'].values
    lons = top_points['longitude'].values
    alts = top_points['altitude'].values

    # Initial guess: strongest signal point (closest to tower)
    idx_max = top_points['lte_rsrp'].idxmax()
    init_lat = top_points.loc[idx_max, 'latitude']
    init_lon = top_points.loc[idx_max, 'longitude']
    init_alt = 30.0  # Typical LTE tower height

    def residuals(tower_pos):
        """
        Residual function: measured distance - calculated distance
        Optimization minimizes sum of squared residuals
        """
        tower_lat, tower_lon, tower_alt = tower_pos
        errors = []

        for i in range(len(lats)):
            calc_dist = haversine_distance_m(
                lats[i], lons[i], alts[i],
                tower_lat, tower_lon, tower_alt
            )
            error = distances[i] - calc_dist
            errors.append(error)

        return errors

    try:
        # Least-squares optimization with soft_l1 loss (robust to outliers)
        result = least_squares(
            residuals,
            [init_lat, init_lon, init_alt],
            bounds=([-90, -180, 0], [90, 180, 100]),
            loss='soft_l1',  # Robust to outliers
            ftol=1e-6,
            xtol=1e-6
        )

        tower_lat, tower_lon, tower_alt = result.x

        # Calculate confidence: inverse of optimization cost
        # Lower cost = better fit = higher confidence
        confidence = 1.0 / (result.cost + 1)

        # Calculate uncertainty (std of residual errors)
        final_errors = residuals(result.x)
        uncertainty_m = float(np.std(final_errors))

        return {
            'lat': float(tower_lat),
            'lon': float(tower_lon),
            'alt': float(tower_alt),
            'method': 'trilateration',
            'confidence': float(confidence),
            'uncertainty_m': uncertainty_m
        }

    except Exception as e:
        print(f"      ⚠️ Trilateration optimization failed: {e}")
        return None


def estimate_tower_weighted_centroid(cell_data: pd.DataFrame) -> dict:
    """
    Weighted centroid using RSRP as weights
    Stronger signals (higher RSRP) = closer to tower = higher weight

    Args:
        cell_data: DataFrame with columns: latitude, longitude, lte_rsrp

    Returns:
        dict with keys: lat, lon, alt, method, confidence, uncertainty_m
    """
    # Convert RSRP to linear weights (-140 dBm = weight 0, -40 dBm = weight 100)
    weights = cell_data['lte_rsrp'] + 140
    weights = np.maximum(weights, 1)  # Prevent negative weights

    # Weighted average position
    tower_lat = float(np.average(cell_data['latitude'], weights=weights))
    tower_lon = float(np.average(cell_data['longitude'], weights=weights))

    # Estimate uncertainty from weighted standard deviation
    lat_std = float(np.sqrt(np.average((cell_data['latitude'] - tower_lat)**2, weights=weights)))
    lon_std = float(np.sqrt(np.average((cell_data['longitude'] - tower_lon)**2, weights=weights)))
    uncertainty_m = np.sqrt(lat_std**2 + lon_std**2) * 111000  # Convert degrees to meters

    return {
        'lat': tower_lat,
        'lon': tower_lon,
        'alt': 30.0,  # Default LTE tower height
        'method': 'weighted_centroid',
        'confidence': 0.7,  # Baseline confidence
        'uncertainty_m': uncertainty_m
    }


def estimate_tower_top_average(cell_data: pd.DataFrame, top_n: int = 3) -> dict:
    """
    Simple average of top N strongest signal points
    Most robust method to GPS noise and outliers

    Args:
        cell_data: DataFrame with columns: latitude, longitude, lte_rsrp
        top_n: Number of top signal points to average (default 3)

    Returns:
        dict with keys: lat, lon, alt, method, confidence, uncertainty_m
    """
    top_points = cell_data.nlargest(min(top_n, len(cell_data)), 'lte_rsrp')

    tower_lat = float(top_points['latitude'].mean())
    tower_lon = float(top_points['longitude'].mean())

    # Standard deviation of top points as uncertainty
    lat_std = float(top_points['latitude'].std()) if len(top_points) > 1 else 0.001
    lon_std = float(top_points['longitude'].std()) if len(top_points) > 1 else 0.001
    uncertainty_m = np.sqrt(lat_std**2 + lon_std**2) * 111000

    return {
        'lat': tower_lat,
        'lon': tower_lon,
        'alt': 30.0,
        'method': f'top{top_n}_average',
        'confidence': 0.8,  # Higher baseline confidence (robust method)
        'uncertainty_m': uncertainty_m
    }


def estimate_tower_hybrid(cell_data: pd.DataFrame, verbose: bool = True) -> dict:
    """
    Hybrid approach: Combine multiple estimation methods with confidence weighting

    Uses consensus of:
    1. Weighted centroid (fast, stable)
    2. Top-3 average (robust to noise)
    3. Trilateration (most accurate if enough data)

    Args:
        cell_data: DataFrame with columns: latitude, longitude, altitude, lte_rsrp
        verbose: Print detailed estimation results

    Returns:
        dict with keys:
            - latitude, longitude, altitude: Final estimated position
            - uncertainty_m: Position uncertainty in meters
            - num_methods: Number of methods used
            - avg_confidence: Average confidence score
            - position_method: Description of method used
    """
    results = []

    # Method 1: Weighted Centroid (fast, stable)
    result1 = estimate_tower_weighted_centroid(cell_data)
    results.append(result1)
    if verbose:
        print(f"      📊 Weighted Centroid: ({result1['lat']:.6f}, {result1['lon']:.6f}) ±{result1['uncertainty_m']:.0f}m")

    # Method 2: Top 3 Average (robust to noise)
    result2 = estimate_tower_top_average(cell_data, top_n=3)
    results.append(result2)
    if verbose:
        print(f"      📊 Top 3 Average: ({result2['lat']:.6f}, {result2['lon']:.6f}) ±{result2['uncertainty_m']:.0f}m")

    # Method 3: Trilateration (most accurate if enough points)
    if len(cell_data) >= 5:
        result3 = estimate_tower_trilateration(cell_data)
        if result3:
            results.append(result3)
            if verbose:
                print(f"      📊 Trilateration: ({result3['lat']:.6f}, {result3['lon']:.6f}) "
                      f"±{result3['uncertainty_m']:.0f}m, confidence={result3['confidence']:.2f}")

    # Confidence-weighted average position
    total_conf = sum(r['confidence'] for r in results)
    final_lat = sum(r['lat'] * r['confidence'] for r in results) / total_conf
    final_lon = sum(r['lon'] * r['confidence'] for r in results) / total_conf
    final_alt = sum(r['alt'] * r['confidence'] for r in results) / total_conf

    # Calculate consensus uncertainty (std across methods)
    method_lats = [r['lat'] for r in results]
    method_lons = [r['lon'] for r in results]
    consensus_std_lat = float(np.std(method_lats)) if len(method_lats) > 1 else 0
    consensus_std_lon = float(np.std(method_lons)) if len(method_lons) > 1 else 0
    consensus_uncertainty_m = np.sqrt(consensus_std_lat**2 + consensus_std_lon**2) * 111000

    # Average uncertainty from all methods
    avg_uncertainty_m = sum(r['uncertainty_m'] for r in results) / len(results)

    # Final uncertainty: max of consensus and average (conservative estimate)
    final_uncertainty_m = max(consensus_uncertainty_m, avg_uncertainty_m)

    if verbose:
        print(f"      ✅ Final Position: ({final_lat:.6f}, {final_lon:.6f}) ±{final_uncertainty_m:.0f}m "
              f"({len(results)} methods, avg conf={total_conf/len(results):.2f})")

    return {
        'latitude': final_lat,
        'longitude': final_lon,
        'altitude': final_alt,
        'uncertainty_m': final_uncertainty_m,
        'num_methods': len(results),
        'avg_confidence': total_conf / len(results),
        'position_method': f'Hybrid ({len(results)} methods)'
    }


def compute_flight_boundary(gps_data: pd.DataFrame, buffer_km: float = 5.0):
    """
    Compute flight path boundary (Convex Hull + buffer) to constrain tower positions

    Args:
        gps_data: DataFrame with 'latitude' and 'longitude' columns
        buffer_km: Buffer distance in kilometers (default 5km)

    Returns:
        Shapely Polygon representing the valid area for tower positions
    """
    try:
        from scipy.spatial import ConvexHull
        from shapely.geometry import Polygon, Point
    except ImportError:
        print("⚠️ scipy or shapely not installed, skipping boundary calculation")
        return None

    # Get GPS coordinates
    coords = gps_data[['latitude', 'longitude']].values

    if len(coords) < 3:
        return None  # Need at least 3 points for convex hull

    # Compute Convex Hull
    try:
        hull = ConvexHull(coords)
        hull_points = coords[hull.vertices]

        # Create polygon (lon, lat order for Shapely)
        polygon = Polygon([(lon, lat) for lat, lon in hull_points])

        # Add buffer (convert km to degrees, approximately)
        # 1 degree latitude ≈ 111 km
        buffer_degrees = buffer_km / 111.0
        buffered_polygon = polygon.buffer(buffer_degrees)

        return buffered_polygon

    except Exception as e:
        print(f"⚠️ Failed to compute convex hull: {e}")
        return None


def filter_by_signal_quality(cell_data: pd.DataFrame, rsrp_percentile: float = 50.0) -> pd.DataFrame:
    """
    Filter GPS points to use only high-quality signal measurements

    Args:
        cell_data: DataFrame with LTE signal quality columns
        rsrp_percentile: Use only top N% of RSRP values (default 50%)

    Returns:
        Filtered DataFrame with high-quality signal points only
    """
    if 'lte_rsrp' not in cell_data.columns:
        return cell_data

    # Calculate RSRP threshold (top N%)
    threshold = cell_data['lte_rsrp'].quantile(rsrp_percentile / 100.0)
    filtered = cell_data[cell_data['lte_rsrp'] >= threshold].copy()

    # Additional filters for signal quality
    # 1. Remove very weak signals (< -110 dBm)
    filtered = filtered[filtered['lte_rsrp'] >= -110]

    # 2. Remove high-noise signals (SINR < 0 dB if available)
    if 'lte_sinr' in filtered.columns:
        filtered = filtered[filtered['lte_sinr'] >= 0]

    # 3. Reduce weight for high-altitude measurements (signal can be misleading)
    if 'altitude' in filtered.columns:
        # Flights above 150m get reduced weighting (not filtered, just noted)
        high_alt_count = len(filtered[filtered['altitude'] > 150])
        if high_alt_count > 0:
            print(f"      ⚠️ {high_alt_count} high-altitude points (>150m) detected")

    return filtered


def validate_tower_position(tower_lat: float, tower_lon: float,
                           flight_boundary,
                           flight_center_lat: float, flight_center_lon: float,
                           max_distance_km: float = 15.0) -> tuple:
    """
    Validate tower position against physical constraints

    Args:
        tower_lat, tower_lon: Estimated tower position
        flight_boundary: Shapely Polygon from compute_flight_boundary()
        flight_center_lat, flight_center_lon: Center of flight path
        max_distance_km: Maximum allowed distance from flight center (default 15km)

    Returns:
        (is_valid, reason) tuple
    """
    try:
        from shapely.geometry import Point
    except ImportError:
        # If shapely not available, skip boundary check
        print("⚠️ shapely not installed, skipping boundary validation")
        flight_boundary = None

    # Check 1: Within flight boundary (if available)
    if flight_boundary is not None:
        tower_point = Point(tower_lon, tower_lat)
        if not flight_boundary.contains(tower_point):
            return False, "Outside flight boundary (likely ocean/mountain)"

    # Check 2: Distance from flight center
    distance_km = haversine_distance_m(
        flight_center_lat, flight_center_lon, 0,
        tower_lat, tower_lon, 0
    ) / 1000.0

    if distance_km > max_distance_km:
        return False, f"Too far from flight center ({distance_km:.1f}km > {max_distance_km}km)"

    # Check 3: Valid GPS coordinates
    if not (-90 <= tower_lat <= 90) or not (-180 <= tower_lon <= 180):
        return False, "Invalid GPS coordinates"

    return True, "Valid"


def estimate_tower_by_enodeb(merged_data: pd.DataFrame, enodeb_id: int,
                             sector_cells: dict, verbose: bool = True) -> dict:
    """
    Estimate tower position by combining data from all sectors of the same eNodeB

    Physical Reality: Same eNodeB = Same physical tower location
    - Multiple sectors (0, 1, 2, ...) are just different directional antennas
    - All sectors share the same GPS coordinates
    - Combining all sector data improves estimation accuracy

    Args:
        merged_data: DataFrame with GPS and LTE data
        enodeb_id: eNodeB identifier (physical tower ID)
        sector_cells: Dict mapping sector_id → cell_id for this eNodeB
        verbose: Print debug information

    Returns:
        dict with keys:
            - latitude, longitude, altitude: Estimated tower position
            - uncertainty_m: Position uncertainty in meters
            - sector_count: Number of sectors detected
            - total_samples: Total GPS samples across all sectors
            - sector_directions: Dict of sector_id → estimated_azimuth
            - position_method: Description of estimation method
    """
    # Collect all GPS points where drone was connected to ANY sector of this eNodeB
    all_sector_data = []
    sector_directions = {}

    for sector_id, cell_id in sector_cells.items():
        # Get GPS points for this sector
        sector_data = merged_data[merged_data['lte_cell_id'] == cell_id].copy()

        if len(sector_data) == 0:
            continue

        # Filter valid RSRP range
        sector_data = sector_data[(sector_data['lte_rsrp'] >= -140) & (sector_data['lte_rsrp'] <= -40)]

        if len(sector_data) > 0:
            all_sector_data.append(sector_data)

            # Calculate average bearing from tower to drone for this sector
            # (This tells us which direction the sector antenna points)
            sector_center_lat = sector_data['latitude'].mean()
            sector_center_lon = sector_data['longitude'].mean()

            # Store for later sector direction analysis
            sector_directions[sector_id] = {
                'center_lat': sector_center_lat,
                'center_lon': sector_center_lon,
                'sample_count': len(sector_data),
                'avg_rsrp': float(sector_data['lte_rsrp'].mean())
            }

    if len(all_sector_data) == 0:
        return None

    # Combine all sector data into unified dataset
    combined_data = pd.concat(all_sector_data, ignore_index=True)

    if verbose:
        print(f"  📡 eNodeB {enodeb_id}: {len(all_sector_data)} sectors, {len(combined_data)} total GPS samples")

    # Signal quality filtering (use top 50% RSRP across all sectors)
    combined_data = filter_by_signal_quality(combined_data, rsrp_percentile=50.0)

    if len(combined_data) < 3:
        if verbose:
            print(f"  ⚠️  eNodeB {enodeb_id}: Insufficient data after filtering ({len(combined_data)} points)")
        return None

    # Hybrid estimation using combined sector data
    estimation = estimate_tower_hybrid(combined_data, verbose=False)

    return {
        'latitude': estimation['latitude'],
        'longitude': estimation['longitude'],
        'altitude': estimation['altitude'],
        'uncertainty_m': estimation['uncertainty_m'],
        'sector_count': len(all_sector_data),
        'total_samples': len(combined_data),
        'sector_directions': sector_directions,
        'position_method': f'eNodeB-based ({len(all_sector_data)} sectors combined)',
        'avg_confidence': estimation['avg_confidence'],
        'num_methods': estimation['num_methods']
    }
