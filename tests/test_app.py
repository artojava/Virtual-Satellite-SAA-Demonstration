from pathlib import Path

from streamlit.testing.v1 import AppTest

import virtual_satellite_saa_demo


def test_run_and_time_exploration():
    path = Path(virtual_satellite_saa_demo.__file__).with_name("app.py")
    app = AppTest.from_file(str(path)).run(timeout=30)
    assert not app.exception
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert int(app.metric[1].value.replace(",", "")) > 0
    original_count = int(app.metric[1].value.replace(",", ""))
    sensitivity = next(slider for slider in app.select_slider if slider.label == "Memory sensitivity (×)")
    sensitivity.set_value(0.01)
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert int(app.metric[1].value.replace(",", "")) < original_count
    assert app.session_state["result"][2].memory_sensitivity == 0.01
    sensitivity = next(slider for slider in app.select_slider if slider.label == "Memory sensitivity (×)")
    sensitivity.set_value(1.0)
    app.button[0].click().run(timeout=30)
    timeline = next(slider for slider in app.slider if slider.label == "Explore the run · sample")
    timeline.set_value(0).run(timeout=30)
    assert not app.exception
    assert app.metric[1].value == "0"
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert int(app.metric[1].value.replace(",", "")) > 0
