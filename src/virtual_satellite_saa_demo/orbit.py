"""Vectorized circular orbit, projected onto a rotating spherical Earth."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

EARTH_RADIUS_KM = 6371.0
MU_KM3_S2 = 398600.4418
SIDEREAL_DAY_S = 86164.0905


@dataclass(frozen=True)
class OrbitConfig:
    altitude_km: float = 550.0
    inclination_deg: float = 51.6
    speed_multiplier: float = 1.0
    duration_hours: float = 6.0
    step_seconds: float = 10.0
    start_longitude_deg: float = -90.0

    def __post_init__(self) -> None:
        limits = {
            "altitude_km": (160, 2000),
            "inclination_deg": (0, 180),
            "speed_multiplier": (0.25, 4),
            "duration_hours": (0.1, 24),
            "step_seconds": (1, 120),
            "start_longitude_deg": (-180, 180),
        }
        for name, (low, high) in limits.items():
            value = getattr(self, name)
            if not np.isfinite(value) or not low <= value <= high:
                raise ValueError(f"{name} must be between {low} and {high}.")

    @property
    def speed_km_s(self) -> float:
        return (
            float(np.sqrt(MU_KM3_S2 / (EARTH_RADIUS_KM + self.altitude_km)))
            * self.speed_multiplier
        )

    @property
    def period_seconds(self) -> float:
        return 2 * np.pi * (EARTH_RADIUS_KM + self.altitude_km) / self.speed_km_s


@dataclass(frozen=True)
class GroundTrack:
    time_s: NDArray[np.float64]
    latitude_deg: NDArray[np.float64]
    longitude_deg: NDArray[np.float64]


def simulate_orbit(config: OrbitConfig) -> GroundTrack:
    """Begin at the ascending equator crossing; include the exact end time.

    The speed multiplier is a teaching control, not orbital mechanics at a
    fixed altitude. At 1× the angular rate follows the circular-orbit equation.
    """
    end = config.duration_hours * 3600
    time = np.append(np.arange(0, end, config.step_seconds), end)
    return orbit_at_times(config, time)


def orbit_at_times(config: OrbitConfig, time: NDArray[np.float64]) -> GroundTrack:
    """Evaluate absolute mission times so live updates never reset orbital phase."""
    time = np.asarray(time, dtype=float)
    if time.ndim != 1 or not np.isfinite(time).all() or np.any(time < 0):
        raise ValueError("Times must be a finite, nonnegative one-dimensional array.")
    phase = 2 * np.pi * time / config.period_seconds
    inclination = np.deg2rad(config.inclination_deg)
    latitude = np.rad2deg(
        np.arcsin(np.clip(np.sin(inclination) * np.sin(phase), -1, 1))
    )
    longitude = np.rad2deg(
        np.arctan2(np.cos(inclination) * np.sin(phase), np.cos(phase))
    )
    longitude += config.start_longitude_deg - 360 * time / SIDEREAL_DAY_S
    longitude = (longitude + 180) % 360 - 180
    return GroundTrack(time, latitude, longitude)
