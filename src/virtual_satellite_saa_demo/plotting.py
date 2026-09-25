"""Matplotlib views, independent of the web interface."""

from functools import lru_cache
from importlib.resources import files
import json

import numpy as np
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.patches import PathPatch

from virtual_satellite_saa_demo.orbit import GroundTrack
from virtual_satellite_saa_demo.radiation import RadiationResult, radiation_intensity, saa_intensity


@lru_cache(maxsize=1)
def _land_paths() -> tuple[Path, ...]:
    """Load bundled Natural Earth land once; retain interior rings (lakes)."""
    resource = files("virtual_satellite_saa_demo").joinpath("data/ne_110m_land.geojson")
    data = json.loads(resource.read_text(encoding="utf-8"))
    paths = []
    for feature in data["features"]:
        geometry = feature["geometry"]
        polygons = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
                    else geometry["coordinates"])
        for polygon in polygons:
            rings = []
            for ring in polygon:
                vertices = np.asarray(ring, dtype=float)
                codes = np.full(len(vertices), Path.LINETO, dtype=np.uint8)
                codes[0], codes[-1] = Path.MOVETO, Path.CLOSEPOLY
                rings.append(Path(vertices, codes))
            paths.append(Path.make_compound_path(*rings))
    return tuple(paths)


def ground_track_figure(track: GroundTrack, radiation: RadiationResult, index: int,
                        *, show_radiation_areas: bool = True) -> Figure:
    fig = Figure(figsize=(12, 5.5), layout="constrained", facecolor="#0e1726")
    ax = fig.subplots()
    ax.set_facecolor("#0e1726")
    # Longitude/latitude land geometry shares the ground track's coordinates.
    for path in _land_paths():
        ax.add_patch(PathPatch(path, facecolor="#26394b", edgecolor="#718497",
                               linewidth=0.55, zorder=0))
    if show_radiation_areas:
        lon, lat = np.meshgrid(np.linspace(-180, 180, 361), np.linspace(-90, 90, 181))
        # Leave low-intensity areas clear so the global map remains legible.
        intensity = np.ma.masked_less(radiation_intensity(lat, lon), 0.05)
        ax.contourf(lon, lat, intensity, levels=np.linspace(0.05, 1.25, 20),
                    cmap="magma", alpha=0.45, zorder=1)
        contour = ax.contour(lon, lat, saa_intensity(lat, lon), levels=[0.2], colors=["#fcbe66"], linewidths=0.8)
        ax.clabel(contour, fmt={0.2: "SAA teaching region"}, fontsize=9)
        for latitude in (-76, 76):
            ax.text(-172, latitude, "Polar enhancement", color="#fcbe66", fontsize=9,
                    bbox={"facecolor": "#0e1726", "alpha": 0.7, "edgecolor": "none"}, zorder=2)
    x, y = track.longitude_deg[:index + 1], track.latitude_deg[:index + 1]
    # Insert breaks rather than drawing lines across the map at the dateline.
    breaks = np.flatnonzero(np.abs(np.diff(x)) > 180) + 1
    ax.plot(np.insert(x, breaks, np.nan), np.insert(y, breaks, np.nan),
            color="#67dce5", lw=1.0, alpha=0.35, label="Ground track", zorder=2)
    counts = radiation.counts[:index + 1]
    events = counts > 0
    ax.scatter(x[events], y[events], s=12 + 9 * np.sqrt(counts[events]), c="#ffb45b", alpha=0.8, label="Bit upsets", zorder=3)
    ax.scatter(x[-1], y[-1], s=95, marker="D", color="white", edgecolors="#0e1726", label="Satellite", zorder=4)
    ax.set(xlim=(-180, 180), ylim=(-90, 90), xlabel="Longitude (°)", ylabel="Latitude (°)")
    ax.set_xticks(np.arange(-180, 181, 60))
    ax.set_yticks(np.arange(-90, 91, 30))
    ax.tick_params(colors="#cad6e6")
    ax.xaxis.label.set_color("#cad6e6")
    ax.yaxis.label.set_color("#cad6e6")
    ax.grid(alpha=0.15, color="white")
    for spine in ax.spines.values():
        spine.set_color("#344256")
    ax.legend(loc="upper right", facecolor="#142238", labelcolor="white", edgecolor="#344256", fontsize=9)
    return fig


def memory_figure(memory: np.ndarray) -> Figure:
    fig = Figure(figsize=(6, 2.6), layout="constrained")
    ax = fig.subplots()
    ax.imshow(memory.reshape(32, 128), cmap="cividis", vmin=0, vmax=1, aspect="auto", interpolation="nearest")
    ax.set(xlabel="Bit column", ylabel="Row", title="4,096 bits · blue = 0 · yellow = 1")
    return fig
