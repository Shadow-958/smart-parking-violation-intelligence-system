"""
Tests for app.services.geo_math. Deliberately dependency-free (stdlib
`math` only) so these run in any environment, unlike the rest of
gis_service which needs geoalchemy2/sqlalchemy/httpx installed.
"""

from app.services.geo_math import haversine_meters


def test_zero_distance_for_identical_points():
    assert haversine_meters(19.076, 72.877, 19.076, 72.877) == 0.0


def test_known_distance_one_degree_of_latitude():
    # One degree of latitude is ~111.19km everywhere on Earth (unlike a
    # degree of longitude, which shrinks toward the poles).
    distance = haversine_meters(0.0, 0.0, 1.0, 0.0)
    assert 110_000 < distance < 112_000


def test_symmetric():
    a = haversine_meters(19.0, 72.8, 19.1, 72.9)
    b = haversine_meters(19.1, 72.9, 19.0, 72.8)
    assert abs(a - b) < 1e-6


def test_short_urban_distance_is_small():
    # Two points ~150m apart (roughly a city block)
    distance = haversine_meters(19.0760, 72.8777, 19.0773, 72.8777)
    assert 100 < distance < 200
