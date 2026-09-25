"""Toy SAA/polar radiation and sensitivity-scaled Poisson bit upsets."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from virtual_satellite_saa_demo.orbit import GroundTrack

MEMORY_BITS = 4096
SAA_PEAK_RATE = 0.25
POLAR_PEAK_RATE = 0.06


def saa_intensity(latitude_deg, longitude_deg):
    """Unitless Gaussian centered at 25° S, 45° W (not a radiation map)."""
    dlon = (np.asarray(longitude_deg) + 45 + 180) % 360 - 180
    dlat = np.asarray(latitude_deg) + 25
    return np.exp(-0.5 * ((dlon / 30) ** 2 + (dlat / 15) ** 2))


def polar_intensity(latitude_deg):
    """Smooth enhancement from |latitude| 55° to 80°, symmetric at both poles.

    Geographic latitude is a teaching proxy for geomagnetic latitude; this
    does not trace the radiation belts or represent a measured particle flux.
    """
    fraction = np.clip((np.abs(np.asarray(latitude_deg)) - 55) / 25, 0, 1)
    return fraction ** 2 * (3 - 2 * fraction)


def radiation_intensity(latitude_deg, longitude_deg):
    """Combined environmental field relative to the default SAA peak rate."""
    return (saa_intensity(latitude_deg, longitude_deg)
            + POLAR_PEAK_RATE / SAA_PEAK_RATE * polar_intensity(latitude_deg))


@dataclass(frozen=True)
class RadiationResult:
    intensity: NDArray[np.float64]
    rate_per_second: NDArray[np.float64]
    counts: NDArray[np.int64]
    bit_addresses: NDArray[np.int64]
    memory_sensitivity: float = 1.0

    def memory_at(self, sample_index: int) -> NDArray[np.bool_]:
        """Reconstruct memory initially filled with zeros; repeated flips cancel."""
        total = int(self.counts[:sample_index + 1].sum())
        return (np.bincount(self.bit_addresses[:total], minlength=MEMORY_BITS) % 2).astype(bool)


def generate_errors(track: GroundTrack, altitude_km: float, seed: int = 42,
                    background_rate: float = 0.002, saa_peak_rate: float = SAA_PEAK_RATE,
                    *, polar_peak_rate: float = POLAR_PEAK_RATE,
                    memory_sensitivity: float = 1.0) -> RadiationResult:
    """Rates are for the whole memory, in upsets/s, at a 550 km reference.

    Trapezoidal integration approximates the exposure per sampling interval.
    Events are plotted at interval endpoints. Altitude scaling is illustrative.
    Sensitivity linearly scales all upset rates, not the environmental field;
    lower sensitivity reduces expected counts but does not exclude any region.
    """
    if not np.isfinite(altitude_km) or not 160 <= altitude_km <= 2000:
        raise ValueError("altitude_km must be between 160 and 2000.")
    if not np.isfinite(memory_sensitivity) or not 0.001 <= memory_sensitivity <= 10:
        raise ValueError("memory_sensitivity must be between 0.001 and 10.")
    if any(not np.isfinite(rate) or not 0 <= rate <= 1
           for rate in (background_rate, saa_peak_rate, polar_peak_rate)):
        raise ValueError("Rates must be finite and between 0 and 1 upset/s.")
    if (track.time_s.ndim != 1 or len(track.time_s) == 0
            or track.time_s.shape != track.latitude_deg.shape
            or track.time_s.shape != track.longitude_deg.shape
            or not all(np.isfinite(a).all() for a in (track.time_s, track.latitude_deg, track.longitude_deg))
            or np.any(np.diff(track.time_s) <= 0)):
        raise ValueError("Track must contain matching finite arrays with increasing times.")
    saa = saa_intensity(track.latitude_deg, track.longitude_deg)
    polar = polar_intensity(track.latitude_deg)
    intensity = radiation_intensity(track.latitude_deg, track.longitude_deg)
    scale = np.exp((altitude_km - 550) / 1000)
    rates = memory_sensitivity * (background_rate + saa_peak_rate * saa + polar_peak_rate * polar) * scale
    exposure = np.zeros_like(track.time_s, dtype=float)
    exposure[1:] = (rates[:-1] + rates[1:]) * 0.5 * np.diff(track.time_s)
    rng = np.random.default_rng(seed)
    counts = rng.poisson(exposure)
    addresses = rng.integers(0, MEMORY_BITS, size=int(counts.sum()))
    return RadiationResult(intensity, rates, counts, addresses, memory_sensitivity)
