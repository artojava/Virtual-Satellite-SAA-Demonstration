import numpy as np
import pytest

from virtual_satellite_saa_demo.orbit import OrbitConfig, SIDEREAL_DAY_S, simulate_orbit


def test_circular_orbit_and_earth_rotation():
    config = OrbitConfig()
    assert 90 < config.period_seconds / 60 < 100
    assert 7 < config.speed_km_s < 8
    track = simulate_orbit(OrbitConfig(duration_hours=config.period_seconds / 3600))
    assert track.latitude_deg[-1] == pytest.approx(0, abs=1e-10)
    assert track.longitude_deg[-1] == pytest.approx(-90 - 360 * config.period_seconds / SIDEREAL_DAY_S)


def test_bounds_and_exact_duration():
    config = OrbitConfig(duration_hours=0.123, step_seconds=10)
    track = simulate_orbit(config)
    assert track.time_s[0] == 0
    assert track.time_s[-1] == config.duration_hours * 3600
    assert np.all(np.diff(track.time_s) > 0)
    assert np.max(np.abs(track.latitude_deg)) <= config.inclination_deg
    assert np.all((-180 <= track.longitude_deg) & (track.longitude_deg < 180))


def test_equatorial_orbit_and_speed():
    assert np.all(simulate_orbit(OrbitConfig(inclination_deg=0)).latitude_deg == 0)
    assert OrbitConfig(speed_multiplier=2).period_seconds == OrbitConfig().period_seconds / 2
    assert OrbitConfig(altitude_km=1500).period_seconds > OrbitConfig().period_seconds


@pytest.mark.parametrize("kwargs", [{"altitude_km": -1}, {"speed_multiplier": 0},
                                    {"step_seconds": 0}, {"duration_hours": 25},
                                    {"inclination_deg": float("nan")}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        OrbitConfig(**kwargs)
