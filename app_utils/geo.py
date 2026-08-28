"""
app/utils/geo.py

Geographic calculations for geofenced lecture check-ins.
Computes Haversine distance and checks if a student is within range.
"""

import math
from typing import Tuple, Optional


def haversine_metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth
    in metres using the Haversine formula.
    """
    R = 6371000.0  # Earth's radius in metres

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def effective_radius(
    base_radius: float,
    host_accuracy: Optional[float] = None,
    student_accuracy: Optional[float] = None,
    max_radius: float = 200.0,
) -> float:
    """
    Dynamically adjust allowed radius based on GPS accuracy bounds.
    """
    radius = float(base_radius)
    if host_accuracy is not None:
        radius += min(float(host_accuracy), 50.0)
    if student_accuracy is not None:
        radius += min(float(student_accuracy), 50.0)

    return min(radius, max_radius)


def within_check_in_range(
    host_lat: float,
    host_lon: float,
    student_lat: float,
    student_lon: float,
    base_radius: float = 50.0,
    host_acc: Optional[float] = None,
    student_acc: Optional[float] = None,
) -> Tuple[bool, float, float]:
    """
    Check if student is within the allowed geofence range of the session host.
    Returns (is_within_range, distance_metres, max_allowed_metres).
    """
    distance = haversine_metres(host_lat, host_lon, student_lat, student_lon)
    max_allowed = effective_radius(base_radius, host_acc, student_acc)
    return distance <= max_allowed, distance, max_allowed


def is_session_geofenced(session_type: str) -> bool:
    """
    Utility to determine if location verification is required based on session type.
    """
    return str(session_type).lower() not in ["online", "virtual", "remote"]