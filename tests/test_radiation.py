import numpy as np
import pytest

from virtual_satellite_saa_demo.orbit import GroundTrack, OrbitConfig, simulate_orbit
from virtual_satellite_saa_demo.radiation import RadiationResult, generate_errors, polar_intensity, saa_intensity


def stationary_track(lat, lon, step=10):
    time = np.arange(0, 36001, step, dtype=float)
    return GroundTrack(time, np.full_like(time, lat), np.full_like(time, lon))


def test_intensity_center_and_wrapping():
    assert saa_intensity(-25, -45) == 1
    assert saa_intensity(-25, 315) == 1
    assert saa_intensity(70, 120) < 0.001


def test_reproducibility_and_no_initial_exposure():
    track = simulate_orbit(OrbitConfig())
    first = generate_errors(track, 550, seed=9)
    second = generate_errors(track, 550, seed=9)
    np.testing.assert_array_equal(first.counts, second.counts)
    np.testing.assert_array_equal(first.bit_addresses, second.bit_addresses)
    assert first.counts[0] == 0
    assert len(first.bit_addresses) == first.counts.sum()
    assert not first.memory_at(0).any()


def test_anomaly_increases_errors_and_exposure_is_time_scaled():
    center = generate_errors(stationary_track(-25, -45), 550)
    outside = generate_errors(stationary_track(0, 120), 550)
    assert center.counts.sum() > 50 * outside.counts.sum()
    # Many expected events make a six-standard-deviation check robust.
    expected = 0.252 * 36000
    for step in (1, 10, 120):
        result = generate_errors(stationary_track(-25, -45, step), 550)
        assert abs(result.counts.sum() - expected) < 6 * np.sqrt(expected)


def test_repeated_flips_cancel():
    result = RadiationResult(np.zeros(3), np.zeros(3), np.array([0, 2, 1]), np.array([7, 7, 9]))
    assert not result.memory_at(1).any()
    assert result.memory_at(2).sum() == 1
    assert result.memory_at(2)[9]


def test_zero_rates_and_altitude_scaling():
    track = stationary_track(-25, -45)
    assert generate_errors(track, 550, background_rate=0, saa_peak_rate=0, polar_peak_rate=0).counts.sum() == 0
    assert np.all(generate_errors(track, 1000).rate_per_second > generate_errors(track, 550).rate_per_second)
    with pytest.raises(ValueError):
        generate_errors(track, 550, background_rate=-1)


def test_polar_enhancement_is_symmetric_and_increases_toward_poles():
    latitudes = np.array([0, 55, 60, 70, 80, 90])
    north = polar_intensity(latitudes)
    np.testing.assert_array_equal(north, polar_intensity(-latitudes))
    assert np.all(np.diff(north) >= 0)
    assert north[0] == north[1] == 0
    assert north[-1] == north[-2] == 1
    equator = generate_errors(stationary_track(0, 120), 550, saa_peak_rate=0)
    for latitude in (-90, 90):
        pole = generate_errors(stationary_track(latitude, 120), 550, saa_peak_rate=0)
        np.testing.assert_allclose(pole.rate_per_second, 31 * equator.rate_per_second)
        assert pole.counts.sum() > 20 * equator.counts.sum()


def test_sensitivity_scales_rates_but_not_radiation_field():
    track = simulate_orbit(OrbitConfig(inclination_deg=90, duration_hours=24))
    reference = generate_errors(track, 550)
    low = generate_errors(track, 550, memory_sensitivity=0.01)
    np.testing.assert_allclose(low.rate_per_second, 0.01 * reference.rate_per_second)
    np.testing.assert_array_equal(low.intensity, reference.intensity)
    assert low.memory_sensitivity == 0.01
    assert low.counts.sum() < reference.counts.sum()
    for pole in (track.latitude_deg > 70, track.latitude_deg < -70):
        assert reference.counts[pole].sum() > 0


@pytest.mark.parametrize("sensitivity", [0, -1, 11, np.nan, np.inf])
def test_invalid_sensitivity(sensitivity):
    with pytest.raises(ValueError, match="memory_sensitivity"):
        generate_errors(stationary_track(0, 0), 550, memory_sensitivity=sensitivity)
