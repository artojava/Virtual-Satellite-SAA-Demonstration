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

1. Set altitude, speed multiplier, inclination, duration, sample interval, and memory sensitivity.
2. Select **Start simulation**. Changes to controls apply only to a new run.
3. Move the sample slider to explore elapsed time, position, cumulative upsets,
   and memory state. The initial result shows the completed run.
4. Inspect the error locations table or download its CSV. Each row groups all
   upsets from one sampling interval at that interval's endpoint.

Use the **SAA and polar enhancement areas** Show/Hide radio control above the map
to toggle the radiation shading and region labels without rerunning the simulation.

Transparent cyan shows the ground track over a bundled Natural Earth world map;
orange markers show upsets; the white diamond is the satellite. The shaded field
is relative SAA and polar radiation intensity. Natural Earth land data is public domain (see
`src/virtual_satellite_saa_demo/data/README.md` for attribution). Memory starts at
zero: an upset flips a randomly selected bit, and repeated flips can restore it.
Consequently, cumulative upsets and currently changed bits are different counts.
Identical parameters and random seeds reproduce results. Changing the sample
interval changes random draws, so it does not preserve individual events.

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

The model uses vectorized NumPy calculations and caps runs at 24 hours with a
minimum one-second step (86,401 samples). Smaller intervals improve spatial
resolution; the default ten seconds is a useful balance for interactive use.
Dateline crossings are broken in the plot to avoid misleading connecting lines.

## Development

```sh
uv sync --dev
uv run pytest
uv build
```

Modules under `src/virtual_satellite_saa_demo/` separate the orbit (`orbit.py`),
radiation and memory (`radiation.py`), plots (`plotting.py`), and web interface
(`app.py`). Tests cover orbital behavior, validation, exposure scaling,
reproducibility, memory flips, sensitivity scaling, polar enhancement, and
running/scrubbing/restarting the interface.
