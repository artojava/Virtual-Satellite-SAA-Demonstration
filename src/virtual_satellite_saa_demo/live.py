"""Incremental simulation with bounded history and refresh-independent randomness."""

from collections import deque
from dataclasses import dataclass

import numpy as np

from virtual_satellite_saa_demo.orbit import GroundTrack, OrbitConfig, orbit_at_times
from virtual_satellite_saa_demo.radiation import (
    MEMORY_BITS,
    RadiationResult,
    radiation_intensity,
    upset_rates,
)

RETENTION_SECONDS = 24 * 3600
MAX_BATCH_SAMPLES = 4096


def flip_mask(addresses: np.ndarray) -> np.ndarray:
    return (np.bincount(addresses, minlength=MEMORY_BITS) % 2).astype(bool)


@dataclass(frozen=True)
class Sample:
    time: float
    latitude: float
    longitude: float
    rate: float
    addresses: np.ndarray


@dataclass(frozen=True)
class HistoryView:
    track: GroundTrack
    radiation: RadiationResult
    initial_memory: np.ndarray
    total_before: int

    def memory_at(self, index: int) -> np.ndarray:
        return self.initial_memory ^ self.radiation.memory_at(index)

    def total_at(self, index: int) -> int:
        return self.total_before + int(self.radiation.counts[: index + 1].sum())


class LiveSimulation:
    """Preserve RNG and memory across updates; retain at most 24 hours of samples."""

    def __init__(self, config: OrbitConfig, sensitivity: float = 1.0, seed: int = 42):
        self.config = config
        self.sensitivity = sensitivity
        # Independent streams ensure repaint/batch size cannot change events.
        counts_seed, memory_seed = np.random.SeedSequence(seed).spawn(2)
        self._count_rng = np.random.default_rng(counts_seed)
        self._memory_rng = np.random.default_rng(memory_seed)
        self.memory = np.zeros(MEMORY_BITS, dtype=bool)
        self.total_upsets = 0
        initial = orbit_at_times(config, np.array([0.0]))
        rate = upset_rates(initial, config.altitude_km, sensitivity)[0]
        self.samples = deque([
            Sample(
                0.0,
                initial.latitude_deg[0],
                initial.longitude_deg[0],
                rate,
                np.empty(0, dtype=np.int64),
            )
        ])
        self.sample_number = 0

    @property
    def time_s(self) -> float:
        return self.sample_number * self.config.step_seconds

    def advance_to(
        self, target_seconds: float, max_samples: int = MAX_BATCH_SAMPLES
    ) -> None:
        """Advance on a fixed sample grid, with bounded work on each refresh.

        Unprocessed time remains a clock backlog, never skipped or re-randomized.
        """
        if not np.isfinite(target_seconds) or target_seconds < 0:
            raise ValueError("Target time must be finite and nonnegative.")
        if max_samples < 1:
            raise ValueError("max_samples must be positive.")
        end = min(
            int(target_seconds // self.config.step_seconds),
            self.sample_number + max_samples,
        )
        if end <= self.sample_number:
            return
        times = (
            np.arange(self.sample_number + 1, end + 1, dtype=float)
            * self.config.step_seconds
        )
        track = orbit_at_times(self.config, times)
        rates = upset_rates(track, self.config.altitude_km, self.sensitivity)
        previous = np.r_[self.samples[-1].rate, rates[:-1]]
        counts = self._count_rng.poisson(
            (previous + rates) * 0.5 * self.config.step_seconds
        )
        addresses = self._memory_rng.integers(0, MEMORY_BITS, size=int(counts.sum()))
        self.memory ^= flip_mask(addresses)
        self.total_upsets += len(addresses)
        offsets = np.r_[0, np.cumsum(counts)]
        for i, time in enumerate(times):
            self.samples.append(
                Sample(
                    time,
                    track.latitude_deg[i],
                    track.longitude_deg[i],
                    rates[i],
                    addresses[offsets[i] : offsets[i + 1]].copy(),
                )
            )
        self.sample_number = end
        while self.samples[0].time < self.time_s - RETENTION_SECONDS:
            self.samples.popleft()

    def view(self, history_hours: float) -> HistoryView:
        if not np.isfinite(history_hours) or not 0.1 <= history_hours <= 24:
            raise ValueError("History must be between 0.1 and 24 hours.")
        selected = [
            sample
            for sample in self.samples
            if sample.time >= self.time_s - history_hours * 3600
        ]
        track = GroundTrack(
            *(
                np.array([getattr(s, name) for s in selected])
                for name in ("time", "latitude", "longitude")
            )
        )
        addresses = np.concatenate([s.addresses for s in selected])
        counts = np.array([len(s.addresses) for s in selected], dtype=np.int64)
        radiation = RadiationResult(
            radiation_intensity(track.latitude_deg, track.longitude_deg),
            np.array([s.rate for s in selected]),
            counts,
            addresses,
            self.sensitivity,
        )
        return HistoryView(
            track,
            radiation,
            self.memory ^ flip_mask(addresses),
            self.total_upsets - len(addresses),
        )


@dataclass
class SimulationClock:
    """Convert monotonic wall time to virtual time; pausing never adds exposure."""

    target_seconds: float
    last_wall_seconds: float
    pace: float = 300.0
    running: bool = True

    def update(self, now: float, *, running: bool, pace: float) -> float:
        if self.running:
            self.target_seconds += max(0.0, now - self.last_wall_seconds) * self.pace
        self.last_wall_seconds = now
        self.running, self.pace = running, pace
        return self.target_seconds
