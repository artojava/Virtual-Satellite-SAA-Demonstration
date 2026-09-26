"""Persistent browser animation; Python remains the authority for radiation events."""

import base64
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import numpy as np
import streamlit.components.v1 as components
from matplotlib.backends.backend_agg import FigureCanvasAgg

from virtual_satellite_saa_demo.orbit import SIDEREAL_DAY_S, GroundTrack, OrbitConfig
from virtual_satellite_saa_demo.plotting import ground_track_figure
from virtual_satellite_saa_demo.radiation import RadiationResult

_component = components.declare_component(
    "smooth_orbit", path=str(Path(__file__).with_name("orbit_component"))
)


@lru_cache(maxsize=2)
def map_background(show_areas: bool) -> dict:
    """Render the static map once per overlay setting, with exact plot bounds."""
    empty = np.empty(0, dtype=int)
    figure = ground_track_figure(
        GroundTrack(empty, empty, empty),
        RadiationResult(empty, empty, empty, empty),
        0,
        show_radiation_areas=show_areas,
        background_only=True,
    )
    canvas = FigureCanvasAgg(figure)
    canvas.draw()
    # Freeze constrained layout so the PNG and overlay use identical coordinates.
    figure.set_layout_engine("none")
    box = figure.axes[0].get_position()
    output = BytesIO()
    canvas.print_png(output)
    return {
        "image": "data:image/png;base64,"
        + base64.b64encode(output.getvalue()).decode(),
        "bounds": [box.x0, 1 - box.y1, box.width, box.height],
    }


def animation_payload(
    track: GroundTrack,
    radiation: RadiationResult,
    index: int,
    config: OrbitConfig,
    *,
    mission_id: str,
    virtual_time: float,
    running: bool,
    pace: float,
    history_hours: float,
    mission_errors: np.ndarray | None = None,
) -> dict:
    """Send sampled history plus orbital parameters for exact sub-sample motion."""
    stop = index + 1
    events = np.flatnonzero(radiation.counts[:stop])
    # Bound visual detail independently from simulation/event accuracy. Five-second
    # samples already give >1,000 segments per physical orbit at the default speed.
    stride = max(1, int(np.ceil(5 / config.step_seconds)))
    samples = np.unique(np.r_[np.arange(0, stop, stride), index])
    return {
        "mission": mission_id,
        "time": virtual_time,
        "running": running,
        "pace": pace,
        "historySeconds": history_hours * 3600,
        "period": config.period_seconds,
        "inclination": config.inclination_deg,
        "startLongitude": config.start_longitude_deg,
        "siderealDay": SIDEREAL_DAY_S,
        "track": np.column_stack((
            track.time_s[samples],
            track.longitude_deg[samples],
            track.latitude_deg[samples],
        )).tolist(),
        "events": (
            mission_errors
            if mission_errors is not None
            else np.column_stack((
                track.time_s[events],
                track.longitude_deg[events],
                track.latitude_deg[events],
                radiation.counts[events],
            ))
        ).tolist(),
    }


def smooth_orbit_map(track, radiation, index, config, *, show_areas, **kwargs):
    payload = animation_payload(track, radiation, index, config, **kwargs)
    _component(
        payload=payload,
        background=map_background(show_areas),
        key="orbit_animation",
        default=None,
    )
