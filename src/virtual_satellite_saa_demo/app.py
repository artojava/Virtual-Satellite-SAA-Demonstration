"""Streamlit presentation layer for the satellite teaching demo."""

import numpy as np
import pandas as pd
import streamlit as st

from virtual_satellite_saa_demo.orbit import OrbitConfig, simulate_orbit
from virtual_satellite_saa_demo.plotting import ground_track_figure, memory_figure
from virtual_satellite_saa_demo.radiation import generate_errors

st.set_page_config(page_title="Satellite · SAA explorer", page_icon="🛰️", layout="wide")
st.title("Satellite · SAA explorer")
st.write(
    "Follow a low Earth orbit and discover where radiation flips bits in satellite memory."
)

with st.sidebar:
    st.header("Mission controls")
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
        duration = st.slider("Duration (hours)", 0.5, 24.0, 6.0, 0.5)
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
        "Change parameters, then start a new run. The same settings and seed reproduce the same errors."
    )

if run:
    config = OrbitConfig(altitude, inclination, speed, duration, step, start_lon)
    with st.spinner("Simulating the orbit and memory upsets…"):
        track = simulate_orbit(config)
        radiation = generate_errors(
            track, altitude, int(seed), memory_sensitivity=sensitivity
        )
    st.session_state["result"] = (config, track, radiation)
    st.session_state.pop("sample_index", None)

if "result" not in st.session_state:
    st.info(
        "Choose mission settings and select Start simulation to trace the orbit and generate memory errors."
    )
else:
    config, track, radiation = st.session_state["result"]
    st.caption(
        f"Active run · {config.altitude_km:g} km · {config.speed_km_s:.2f} km/s · "
        f"{config.period_seconds / 60:.1f} min/orbit · {config.duration_hours:g} hours · "
        f"memory sensitivity {radiation.memory_sensitivity:g}×"
    )
    index = st.slider(
        "Explore the run · sample",
        0,
        len(track.time_s) - 1,
        len(track.time_s) - 1,
        key="sample_index",
    )
    memory = radiation.memory_at(index)
    total = int(radiation.counts[: index + 1].sum())
    cols = st.columns(4)
    cols[0].metric("Elapsed time", f"{track.time_s[index] / 3600:.2f} h")
    cols[1].metric("Bit upsets", f"{total:,}")
    cols[2].metric("Bits currently changed", f"{memory.sum():,}")
    cols[3].metric("Current upset rate", f"{radiation.rate_per_second[index]:.3f} /s")
    show_areas = (
        st.radio(
            "SAA and polar enhancement areas",
            ["Show", "Hide"],
            horizontal=True,
            key="radiation_areas",
        )
        == "Show"
    )
    st.pyplot(
        ground_track_figure(track, radiation, index, show_radiation_areas=show_areas),
        width="stretch",
    )
    st.caption(
        f"Satellite: {track.latitude_deg[index]:.2f}° latitude, {track.longitude_deg[index]:.2f}° longitude. "
        "Orange markers show intervals with errors; larger markers indicate more upsets. "
        + (
            "Shading shows SAA and polar radiation intensity, independent of memory sensitivity."
            if show_areas
            else "Radiation areas are hidden; simulated errors are unchanged."
        )
    )
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Onboard memory")
        st.pyplot(memory_figure(memory), width="stretch")
        st.caption(
            "Memory starts at zero. Each upset flips one random bit; a second flip restores it. "
            "Total upsets can exceed the number of changed bits."
        )
    with right:
        st.subheader("Error locations")
        events = np.flatnonzero(radiation.counts[: index + 1])
        frame = pd.DataFrame({
            "Time (min)": track.time_s[events] / 60,
            "Latitude (°)": track.latitude_deg[events],
            "Longitude (°)": track.longitude_deg[events],
            "Upsets": radiation.counts[events],
        })
        st.dataframe(frame.round(2), hide_index=True, height=240, width="stretch")
        if frame.empty:
            st.caption("No upsets recorded at this point in the run.")
        st.download_button(
            "Download error locations (CSV)",
            frame.to_csv(index=False),
            file_name="satellite-errors.csv",
            mime="text/csv",
        )

with st.expander(
    "How this demonstration works", expanded="result" not in st.session_state
):
    st.markdown("""
The orbit is circular above a spherical, rotating Earth. Its ground track is the
point directly beneath the satellite, shown in longitude and latitude.

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
