"""Streamlit presentation layer for the satellite teaching demo."""

import time

import numpy as np
import pandas as pd
import streamlit as st

from virtual_satellite_saa_demo.animation import smooth_orbit_map
from virtual_satellite_saa_demo.live import LiveSimulation, SimulationClock
from virtual_satellite_saa_demo.orbit import OrbitConfig
from virtual_satellite_saa_demo.plotting import memory_figure

st.set_page_config(
    page_title="Virtual Satellite · SEE Demonstration", page_icon="🛰️", layout="wide"
)
st.title("Virtual Satellite · SEE Demonstration")
st.write(
    "Follow a low Earth orbit and discover where radiation flips bits in satellite memory."
)

with st.sidebar:
    st.header("Mission controls")
    duration = st.slider("Visible history (hours)", 0.5, 24.0, 6.0, 0.5)
    st.caption(
        "Adjust the orbit trail during a run. Error markers remain from mission start."
    )
    with st.form("mission"):
        altitude = st.slider("Altitude (km)", 160, 2000, 550, 10)
        speed = st.slider("Orbital speed multiplier", 0.25, 4.0, 1.0, 0.25)
        st.caption(
            "1× uses circular-orbit speed. Other values are a teaching override."
        )
        inclination = st.slider("Inclination (°)", 0.0, 180.0, 51.6, 0.1)
        st.caption("Use 90° inclination to explore both polar regions.")
        sensitivity = st.select_slider(
            "Memory sensitivity (×)",
            options=[0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0],
            value=1.0,
            format_func=lambda value: f"{value:g}×",
        )
        st.caption(
            "Lower = fewer bit flips. Try 0.03× over 24 hours at 51.6° to highlight the SAA. "
            "Rare errors elsewhere remain possible."
        )
        step = st.select_slider(
            "Sample interval (seconds)", options=[1, 5, 10, 30, 60, 120], value=10
        )
        start_lon = st.slider("Starting longitude (°)", -180, 180, -90)
        seed = st.number_input(
            "Random seed", min_value=0, max_value=2147483647, value=42, step=1
        )
        run = st.form_submit_button(
            "Start simulation", type="primary", use_container_width=True
        )
    st.caption(
        "Start simulation begins a new mission with the selected history already generated. "
        "Orbit and memory changes apply to a new run. The same settings and seed reproduce events at the same virtual times."
    )

if run:
    config = OrbitConfig(altitude, inclination, speed, duration, step, start_lon)
    with st.spinner("Generating the initial virtual history…"):
        simulation = LiveSimulation(config, sensitivity, int(seed))
        target = duration * 3600
        while simulation.time_s + config.step_seconds <= target:
            simulation.advance_to(target)
    st.session_state["simulation"] = simulation
    st.session_state["simulation_running"] = True
    st.session_state["clock"] = SimulationClock(
        simulation.time_s, time.monotonic(), st.session_state.get("pace", 300)
    )
    st.session_state.pop("sample_index", None)


@st.fragment(run_every=1.0)
def live_dashboard():
    """Refresh only the live view, without resubmitting mission settings."""
    if "simulation" not in st.session_state:
        st.info(
            "Choose mission settings and select Start simulation to begin a continuous run."
        )
        return
    simulation = st.session_state["simulation"]
    config = simulation.config
    map_tab, memory_tab = st.tabs(["Global map", "Onboard memory & errors"])
    controls = st.columns([1, 3])
    running = controls[0].toggle("Running", key="simulation_running")
    pace = controls[1].select_slider(
        "Virtual seconds per real second",
        options=[1, 60, 300, 600, 1800, 3600],
        value=300,
        key="pace",
    )
    clock = st.session_state["clock"]
    target = clock.update(time.monotonic(), running=running, pace=pace)
    simulation.advance_to(target)
    catching_up = target - simulation.time_s >= config.step_seconds
    if catching_up:
        st.info(
            "Catching up virtual history in batches; no exposure intervals are skipped."
        )
    view = simulation.view(duration)
    track, radiation = view.track, view.radiation
    st.caption(
        f"Active run · {config.altitude_km:g} km · {config.speed_km_s:.2f} km/s · "
        f"{config.period_seconds / 60:.1f} min/orbit · last {duration:g} hours · "
        f"memory sensitivity {radiation.memory_sensitivity:g}×"
    )
    index = len(track.time_s) - 1
    if not running and not catching_up and index > 0:
        index = st.slider(
            "Explore retained history · sample", 0, index, index, key="sample_index"
        )
    else:
        st.caption(
            "Live position follows virtual time. Pause Running to inspect retained history."
        )
    memory = view.memory_at(index)
    mission_errors = simulation.error_history()
    with map_tab:
        map_column, metrics_column = st.columns([3, 1])
        with map_column:
            show_areas = (
                st.radio(
                    "SAA and polar enhancement areas",
                    ["Show", "Hide"],
                    horizontal=True,
                    key="radiation_areas",
                )
                == "Show"
            )
            smooth_orbit_map(
                track,
                radiation,
                index,
                config,
                show_areas=show_areas,
                mission_id=str(id(simulation)),
                virtual_time=target
                if running and not catching_up
                else float(track.time_s[index]),
                running=running and not catching_up,
                pace=pace,
                history_hours=duration,
                mission_errors=mission_errors,
            )
            st.caption(
                f"Satellite: {track.latitude_deg[index]:.2f}° latitude, {track.longitude_deg[index]:.2f}° longitude. "
                "Orange markers show all errors since mission start, including while browsing older positions. "
                "Larger markers indicate more upsets. "
                + (
                    "Shading shows SAA and polar radiation intensity, independent of memory sensitivity."
                    if show_areas
                    else "Radiation areas are hidden; simulated errors are unchanged."
                )
            )
            st.caption(
                f"Showing mission hours {track.time_s[0] / 3600:.2f}–{track.time_s[index] / 3600:.2f}. "
                "Older orbit points roll off the map; error markers remain until a new simulation starts."
            )
        with metrics_column:
            st.metric("Mission time", f"{track.time_s[index] / 3600:.2f} h")
            st.metric("Mission bit upsets", f"{simulation.total_upsets:,}")
            st.metric("Trail interval upsets", f"{radiation.counts[: index + 1].sum():,}")
            st.metric("Bits currently changed", f"{memory.sum():,}")
            st.metric(
                "Current upset rate",
                f"{radiation.rate_per_second[index] * 3600:.2f} /hour",
            )
    with memory_tab:
        left, right = st.columns([1, 1])
        with left:
            st.subheader("Onboard memory")
            st.pyplot(memory_figure(memory), width="stretch")
            st.caption(
                "Memory starts at zero. Each upset flips one random bit; a second flip restores it. "
                "Memory and mission totals include events older than the visible history."
            )
        with right:
            st.subheader("Mission error locations")
            frame = pd.DataFrame({
                "Time (min)": mission_errors[:, 0] / 60,
                "Latitude (°)": mission_errors[:, 2],
                "Longitude (°)": mission_errors[:, 1],
                "Upsets": mission_errors[:, 3].astype(np.int64),
            })
            st.dataframe(frame.round(2), hide_index=True, height=240, width="stretch")
            if frame.empty:
                st.caption("No upsets recorded in this mission yet.")
            st.download_button(
                "Download error locations (CSV)",
                frame.to_csv(index=False),
                file_name="satellite-errors.csv",
                mime="text/csv",
            )


live_dashboard()

with st.expander(
    "How this demonstration works", expanded="simulation" not in st.session_state
):
    st.markdown("""
The orbit is circular above a spherical, rotating Earth. Its ground track is the
point directly beneath the satellite, shown in longitude and latitude.

The simulation starts with the selected virtual history and then advances
continuously while this browser session is active. **Virtual seconds per real
second** controls the pace of the demonstration; the orbital speed multiplier
changes the orbit itself. **Visible history** changes only the orbit trail window.
All recorded error locations stay on the map and in the table/CSV until a new
simulation starts, even when browsing earlier satellite positions.
Pause **Running** to browse the retained orbit history, then resume
to continue from the same state. Closing/reloading the session or restarting the
server can discard the run; this demonstration does not save missions to disk.

The **South Atlantic Anomaly** is represented here by a broad Gaussian centered
at **25° S, 45° W**. At 550 km and 1× sensitivity, the whole-memory upset rate
is 0.002/s plus up to 0.25/s in the anomaly and up to 0.06/s near either pole.
Polar enhancement rises smoothly between **55° and 80° absolute latitude**.
Geographic latitude is a simplified proxy for geomagnetic access to energetic
particles, not a calculation of radiation-belt geometry.

**Memory sensitivity** multiplies all upset rates: 0.03× gives 3% of the expected
upsets at 1×. Less sensitive memory often shows only the strongest hotspot over
a finite run, but it is not immune outside the SAA. A polar orbit can still
exhibit polar errors. Try 51.6° inclination, 24 hours, and 0.03× sensitivity for
the SAA demonstration; use 90° and 1× to see both polar regions.

An illustrative exponential factor increases rates with altitude.
Poisson draws use the exposure time between samples. Shorter sample intervals
resolve the path and error positions more precisely.

This is an **educational model**, not a mission radiation prediction. It omits
real particle spectra, shielding, solar activity, field evolution, and orbital
perturbations. Error positions are sampling-interval endpoints, not exact event times.
""")
