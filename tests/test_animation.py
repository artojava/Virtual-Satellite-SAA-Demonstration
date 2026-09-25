import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest

from virtual_satellite_saa_demo.animation import animation_payload
from virtual_satellite_saa_demo.orbit import OrbitConfig, SIDEREAL_DAY_S, orbit_at_times, simulate_orbit
from virtual_satellite_saa_demo.radiation import generate_errors

COMPONENT = Path(__file__).parents[1] / "src/virtual_satellite_saa_demo/orbit_component"


def test_animation_keeps_all_events_and_selected_endpoint():
    config = OrbitConfig(step_seconds=1)
    track = simulate_orbit(config)
    radiation = generate_errors(track, 550)
    payload = animation_payload(track, radiation, 10000, config, mission_id="mission",
                                virtual_time=10000, running=False, pace=300, history_hours=6)
    assert payload["track"][-1][0] == 10000
    assert sum(event[3] for event in payload["events"]) == radiation.counts[:10001].sum()
    assert len(payload["track"]) < 10001


def test_mission_error_markers_are_independent_of_trail_and_scrubbing():
    config = OrbitConfig()
    track = orbit_at_times(config, np.array([10000.0, 10010.0]))
    radiation = generate_errors(track, 550)
    archive = np.array([[10, -45, -25, 2], [20000, 30, 70, 1]])
    payload = animation_payload(track, radiation, 0, config, mission_id="mission",
                                virtual_time=10000, running=False, pace=300,
                                history_hours=0.5, mission_errors=archive)
    assert payload["events"] == archive.tolist()
    assert payload["track"][0][0] == 10000


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is needed for browser math checks")
def test_javascript_matches_python_and_animation_time_is_continuous():
    cases = []
    expected = []
    for inclination in (0, 51.6, 90, 135, 180):
        config = OrbitConfig(inclination_deg=inclination, speed_multiplier=4)
        times = np.array([0, 0.01, 15.3, 600.123, 43199.99, 864000.25])
        track = orbit_at_times(config, times)
        cases.extend({"time": float(t), "period": config.period_seconds, "inclination": inclination,
                      "startLongitude": config.start_longitude_deg, "siderealDay": SIDEREAL_DAY_S}
                     for t in times)
        expected.extend(zip(track.longitude_deg, track.latitude_deg))
    script = '''
const assert = require("node:assert/strict");
const api = require(process.argv[1]);
const cases = JSON.parse(require("node:fs").readFileSync(0, "utf8"));
const packet = {time: 100, running: true, pace: 300};
for (const correction of [-600, 0, 600]) {
  let last = -Infinity;
  for (let milliseconds = 0; milliseconds <= 2500; milliseconds += 16) {
    const time = api.displayTime(packet, 0, milliseconds, correction);
    assert.ok(time >= last, "Animation clock must not reverse");
    last = time;
  }
}
assert.equal(api.displayTime(packet, 0, 2000), api.displayTime(packet, 0, 9000));
assert.equal(api.displayTime({...packet, running: false}, 0, 99999), 100);
assert.ok(api.displayTime(packet, 0, 16) > api.displayTime(packet, 0, 0));
console.log(JSON.stringify(cases.map(c => api.position(c.time, c))));
'''
    result = subprocess.run(["node", "-e", script, str(COMPONENT / "orbit.js")],
                            input=json.dumps(cases), text=True, capture_output=True, check=True)
    np.testing.assert_allclose(json.loads(result.stdout), expected, atol=1e-8)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is needed for component checks")
def test_component_protocol_and_render_loop():
    subprocess.run(["node", str(Path(__file__).with_name("animation_render_check.cjs")),
                    str(COMPONENT)], check=True, capture_output=True, text=True)
