from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

import virtual_satellite_saa_demo


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_live_run_pause_history_and_restart():
    path = Path(virtual_satellite_saa_demo.__file__).with_name("app.py")
    app = AppTest.from_file(str(path)).run(timeout=30)
    button(app, "Start simulation").click().run(timeout=30)
    assert not app.exception
    simulation = app.session_state["simulation"]
    assert [tab.label for tab in app.tabs] == ["Global map", "Onboard memory & errors"]
    assert len(app.tabs[0].dataframe) == 0
    assert len(app.tabs[1].dataframe) == 1
    assert app.tabs[1].subheader[0].value == "Onboard memory"
    assert simulation.total_upsets > 0
    before = simulation.time_s
    app.session_state["clock"].last_wall_seconds -= 2
    app.run(timeout=30)
    assert not app.exception
    assert simulation.time_s > before

    app.toggle[0].set_value(False).run(timeout=30)
    stopped_time = simulation.time_s
    stopped_memory = simulation.memory.copy()
    next(s for s in app.slider if s.label == "Visible history (hours)").set_value(0.5).run(timeout=30)
    app.radio[0].set_value("Hide").run(timeout=30)
    assert not app.exception
    assert simulation.time_s == stopped_time
    np.testing.assert_array_equal(simulation.memory, stopped_memory)
    assert app.session_state["simulation"] is simulation
    timeline = next(s for s in app.slider if s.label == "Explore retained history · sample")
    timeline.set_value(0).run(timeout=30)
    assert not app.exception
    assert simulation.time_s == stopped_time

    app.toggle[0].set_value(True).run(timeout=30)
    app.session_state["clock"].last_wall_seconds -= 2
    app.run(timeout=30)
    assert simulation.time_s > stopped_time
    next(s for s in app.select_slider if s.label == "Memory sensitivity (×)").set_value(0.01)
    button(app, "Start simulation").click().run(timeout=30)
    assert not app.exception
    restarted = app.session_state["simulation"]
    assert restarted is not simulation
    assert restarted.sensitivity == 0.01
    assert restarted.time_s < stopped_time
    assert app.toggle[0].value is True
