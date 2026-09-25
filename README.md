# Virtual satellite · SAA explorer

A Python web application for demonstrating single-event effects in a mock
low Earth orbit satellite. Follow the satellite's 2D ground track, see errors
cluster near an illustrative South Atlantic Anomaly (SAA), and inspect the
effect of random bit flips on 4,096 bits of onboard memory.

## Setup and run

Install Python 3.13 or later and [uv](https://docs.astral.sh/uv/), then run from
this directory:

```sh
uv sync
uv run virtual-satellite-saa-demo
```

Open the local URL printed by Streamlit (normally http://localhost:8501).
Stop the server with Ctrl+C. Server options can be passed through the launcher:

```sh
uv run virtual-satellite-saa-demo --server.port 8502 --server.headless true
```

The runtime dependencies are NumPy, Matplotlib, pandas, and Streamlit.
`uv.lock` records their resolved versions. No map downloads, API keys, or
external services are required during a run.

## Using the application

1. Set altitude, orbital speed multiplier, inclination, sample interval, memory
   sensitivity, and **Visible history (hours)**.
2. Select **Start simulation**. The app generates the selected initial history,
   then keeps advancing the satellite and drawing fresh random errors.
3. Set **Virtual seconds per real second** to control the demonstration pace
   (default 300: five virtual minutes per real second). This is separate from
   orbital speed: time acceleration speeds up both motion and radiation exposure.
4. Change **Visible history** at any time to shorten or extend the visible trail
   within the retained data. Switch **Running** off to pause and use the sample
   slider to inspect historical position, errors, and memory. Switch it on to resume.
5. Inspect all mission error locations or download their CSV. Each row groups
   upsets at one interval endpoint; times are minutes since virtual mission start.

Orbit, sensitivity, sample interval, and seed changes apply when **Start simulation**
is pressed again, resetting mission time, random generators, and memory. Display
changes do not reset a mission or regenerate past errors.

The satellite marker and leading trail animate at the browser's frame rate using
the same orbital equations as Python, including Earth rotation and date-line
wrapping. Recorded history, errors, and counters update approximately once per
second. The map background stays fixed between updates. Animation does not change
the sample interval or generate extra radiation events. Pause and history browsing
freeze the marker at the selected sample. If server updates stop, the marker stops
after two seconds and displays “Waiting for update”. Leave the app running
to accumulate virtual history: the orbit continues past the selected history
length, and old orbit points roll off. At most 24 hours of detailed orbit/memory
samples are retained; expanding the window reveals whatever track is available.
**All error locations remain visible from mission start**, including errors older
than 24 hours. The table and CSV also include the complete mission error history.
Changing the trail window, hiding radiation areas, pausing, or browsing earlier
positions never clears error markers. Starting a new simulation resets this archive.
Mission totals include all recorded upsets, while **Trail interval upsets** counts
only events within the displayed orbit interval. Memory inspection still reflects
the selected historical time, including effects of earlier events.

The simulation is session-local, not a background service or disk archive. Keep
the server and browser session open. Closing/reloading the session or restarting
the server can discard it. Delayed refreshes catch up in bounded batches without
skipping radiation exposure; pause/resume does not count paused wall time.

The **Global map** tab contains the animated world map; **Onboard memory & errors**
contains the memory bitmap, complete mission error table, and CSV download.
The map preserves its aspect ratio and scales to the available page width and
remaining window height, so resizing does not crop the world map. Shared live
controls and mission metrics sit below the tab content.

Use the **SAA and polar enhancement areas** Show/Hide radio control below the map
to toggle the radiation shading and region labels without rerunning the simulation.

Transparent cyan shows the ground track over a bundled Natural Earth world map;
orange markers show upsets; the white diamond is the satellite. The shaded field
is relative SAA and polar radiation intensity. Natural Earth land data is public domain (see
`src/virtual_satellite_saa_demo/data/README.md` for attribution). Memory starts at
zero: an upset flips a randomly selected bit, and repeated flips can restore it.
Consequently, cumulative upsets and currently changed bits are different counts.
Identical parameters and random seeds reproduce events at the same virtual
mission times regardless of refresh frequency or time acceleration. Independent
random streams for counts and bit addresses prevent refresh batching from changing
the outcome. Changing the sample interval changes random draws, so it does not
preserve individual events. Live runs use different random streams from the
original finite-run implementation, but use the same probability and memory rules.

### Demonstrating memory sensitivity and polar exposure

The **Memory sensitivity (×)** control ranges from 0.001× to 10×; 1× is the
reference memory. It multiplies every upset rate without changing the radiation
environment. For example, 0.03× gives 3% of the expected upsets of 1×.

Use 550 km, 51.6° inclination, and 24 hours, then compare 1× with 0.03× or lower
to highlight the SAA as background errors become sparse. Very low sensitivity
can produce no errors, especially on short runs. Errors outside the SAA remain
possible: reducing sensitivity does not create geographical immunity.

Use **90° inclination and 1× sensitivity** to demonstrate increased errors in
both polar regions. The default 51.6° orbit does not reach the polar enhancement.

## Model and limitations

- Circular orbit over a spherical Earth of radius 6,371 km, with Earth rotation
  over a sidereal day. The starting point is the ascending equator crossing.
- At 1×, speed is `sqrt(mu / radius)` and period is `2π radius / speed`.
  Other speed multipliers deliberately override circular-orbit physics for teaching.
- SAA intensity is a Gaussian centered at 25° S, 45° W, with latitude/longitude
  widths of 15°/30°. This is an illustrative field, not measured radiation data.
- Polar intensity `P` rises smoothly from zero at |latitude| ≤55° to one at
  |latitude| ≥80° using `u²(3 - 2u)`, where `u = clip((|latitude| - 55) / 25, 0, 1)`.
  The same enhancement applies north and south. Geographic latitude is an
  illustrative proxy for geomagnetic particle access, not radiation-belt geometry.
- Whole-memory upset rate is
  `sensitivity * (0.002 + 0.25 * SAA + 0.06 * P) * exp((altitude - 550) / 1000)`
  per second. Rates and altitude scaling are demonstration choices, not calibrated
  predictions for a real memory device.
- Map shading shows `SAA + 0.24 * P`, independently of memory sensitivity.
- Poisson counts use trapezoidal integration of the rate over each time interval.
  Each event flips one of 4,096 equally likely memory bits. No error correction is modeled.
- Particle spectra, shielding, solar activity, evolving magnetic fields, and
  orbital perturbations are omitted. This is not a mission-design tool.

For physical context, the [BGS State of the Geomagnetic Field report](https://www.geomag.bgs.ac.uk/documents/WMM_Report_2023.pdf)
discusses satellite radiation effects in the SAA and polar exposure to energetic
particles. The numerical rates and latitude boundaries above are teaching choices.

The model uses vectorized NumPy calculations. Live runs have no fixed duration;
detailed orbit/memory history is capped at 24 hours with a minimum one-second step
(86,401 retained samples). Error intervals are stored separately as compact
time/longitude/latitude/count rows for the entire mission; this archive and its
display grow with mission duration. Individual bit addresses older than 24 hours
are not retained, but error locations and counts are preserved.
Each update processes at most 4,096 new samples so long
catch-up periods can be split across refreshes. Smaller intervals improve spatial
resolution; the default ten seconds is a useful balance for interactive use.
Dateline crossings are broken in the plot to avoid misleading connecting lines.

## Development

```sh
uv sync --dev
uv run pytest
uv build
```

Modules under `src/virtual_satellite_saa_demo/` separate the orbit (`orbit.py`),
radiation and memory (`radiation.py`), incremental state and clock (`live.py`),
plots (`plotting.py`), browser animation (`animation.py` and `orbit_component/`),
and web interface (`app.py`). The browser component is bundled and needs no CDN or
frontend build. Tests cover orbital behavior, validation, exposure scaling,
reproducibility, memory flips, sensitivity scaling, polar enhancement, and
refresh-independent randomness, history retention, pause/resume, and the interface.

With Node.js installed, `uv run pytest` also checks that browser orbital coordinates
match Python and tests animation timing and the component's update handling.
