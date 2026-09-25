import numpy as np
import pytest

from virtual_satellite_saa_demo.live import (
    FLIGHT_PATH_RETENTION_SECONDS,
    MISSION_ERROR_RETENTION_SECONDS,
    LiveSimulation,
    SimulationClock,
    RETENTION_SECONDS,
)
from virtual_satellite_saa_demo.orbit import OrbitConfig, simulate_orbit
from virtual_satellite_saa_demo.radiation import upset_rates


def advance(simulation, target, batch=4096):
    while simulation.time_s + simulation.config.step_seconds <= target:
        simulation.advance_to(target, max_samples=batch)


def test_live_matches_orbit_and_rate_rules():
    config = OrbitConfig(inclination_deg=90)
    simulation = LiveSimulation(config, sensitivity=0.03)
    advance(simulation, config.duration_hours * 3600)
    view = simulation.view(24)
    expected = simulate_orbit(config)
    np.testing.assert_array_equal(view.track.time_s, expected.time_s)
    np.testing.assert_allclose(view.track.latitude_deg, expected.latitude_deg)
    np.testing.assert_allclose(view.track.longitude_deg, expected.longitude_deg)
    np.testing.assert_allclose(view.radiation.rate_per_second, upset_rates(expected, 550, 0.03))
    assert view.radiation.counts[0] == 0


def test_randomness_is_independent_of_refresh_batches():
    first = LiveSimulation(OrbitConfig(), seed=123)
    second = LiveSimulation(OrbitConfig(), seed=123)
    advance(first, 43200, batch=4096)
    advance(second, 43200, batch=7)
    a, b = first.view(24), second.view(24)
    np.testing.assert_array_equal(a.radiation.counts, b.radiation.counts)
    np.testing.assert_array_equal(a.radiation.bit_addresses, b.radiation.bit_addresses)
    np.testing.assert_array_equal(first.memory, second.memory)
    old_count = first.total_upsets
    first.advance_to(first.time_s)
    assert first.total_upsets == old_count
    np.testing.assert_array_equal(first.memory, second.memory)


def test_rollover_preserves_memory_and_cumulative_counts():
    simulation = LiveSimulation(OrbitConfig(step_seconds=60))
    advance(simulation, 2 * RETENTION_SECONDS)
    assert len(simulation.samples) == RETENTION_SECONDS // 60 + 1
    assert simulation.samples[0].time == RETENTION_SECONDS
    full = simulation.view(24)
    short = simulation.view(0.5)
    assert short.track.time_s[0] == simulation.time_s - 1800
    for view in (full, short):
        np.testing.assert_array_equal(view.memory_at(len(view.track.time_s) - 1), simulation.memory)
        assert view.total_at(len(view.track.time_s) - 1) == simulation.total_upsets
        assert view.total_before > 0
    offset = np.searchsorted(full.track.time_s, short.track.time_s[0])
    np.testing.assert_array_equal(full.memory_at(offset), short.memory_at(0))
    assert full.total_at(offset) == short.total_at(0)


def test_clock_pause_resume_and_pace_changes():
    clock = SimulationClock(0, 100, pace=60)
    assert clock.update(102, running=False, pace=60) == 120
    assert clock.update(1000, running=False, pace=60) == 120
    assert clock.update(2000, running=True, pace=300) == 120
    assert clock.update(2002, running=True, pace=1) == 720
    assert clock.update(2003, running=True, pace=1) == 721


def test_partial_intervals_and_bounded_catchup():
    simulation = LiveSimulation(OrbitConfig(step_seconds=10))
    simulation.advance_to(9)
    assert simulation.time_s == 0
    simulation.advance_to(19)
    assert simulation.time_s == 10
    simulation.advance_to(10000, max_samples=2)
    assert simulation.time_s == 30
    advance(simulation, 10000)
    assert simulation.time_s == 10000
    with pytest.raises(ValueError):
        simulation.advance_to(float("nan"))


def test_mission_errors_survive_rollover_and_only_new_mission_starts_empty():
    config = OrbitConfig(step_seconds=60)
    simulation = LiveSimulation(config)
    advance(simulation, RETENTION_SECONDS)
    first_day = simulation.error_history()
    assert len(first_day) > 0
    advance(simulation, 3 * RETENTION_SECONDS)
    entire_mission = simulation.error_history()
    np.testing.assert_array_equal(entire_mission[:len(first_day)], first_day)
    assert entire_mission[0, 0] < simulation.samples[0].time
    assert entire_mission[:, 3].sum() == simulation.total_upsets
    simulation.view(0.5)
    simulation.view(24)
    np.testing.assert_array_equal(simulation.error_history(), entire_mission)
    # Equal-time updates and reads never duplicate or remove past events.
    simulation.advance_to(simulation.time_s)
    np.testing.assert_array_equal(simulation.error_history(), entire_mission)
    replacement = LiveSimulation(config)
    assert replacement.error_history().shape == (0, 4)
    assert replacement.total_upsets == 0


def test_flight_path_and_mission_error_histories_have_separate_horizons():
    config = OrbitConfig(step_seconds=60)
    simulation = LiveSimulation(config)
    advance(simulation, MISSION_ERROR_RETENTION_SECONDS + RETENTION_SECONDS)

    assert simulation.samples[0].time == simulation.time_s - FLIGHT_PATH_RETENTION_SECONDS
    errors = simulation.error_history()
    assert errors[0, 0] >= simulation.time_s - MISSION_ERROR_RETENTION_SECONDS
    assert errors[-1, 0] <= simulation.time_s
