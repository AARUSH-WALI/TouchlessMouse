"""Touchless Computer Control System - Cursor Smoothing Filters."""

import math
import time
from typing import Optional


class OneEuroFilter:
    """
    One Euro Filter for responsive, jitter-free cursor tracking.
    
    Dynamically balances jitter elimination (low speed) and latency reduction (high speed):
    - When hand is still or moving slowly: heavy smoothing removes camera jitter.
    - When hand moves rapidly: smoothing decreases adaptively so the cursor does not lag behind.

    Parameters:
        min_cutoff (float): Minimum cutoff frequency in Hz (lower = smoother at rest).
        beta (float): Speed coefficient (higher = less lag during rapid sweeps).
        d_cutoff (float): Cutoff frequency for derivative filtering (typically 1.0).
    """

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev: Optional[float] = None
        self.dx_prev: float = 0.0
        self.t_prev: Optional[float] = None

    def _smoothing_factor(self, t_e: float, cutoff: float) -> float:
        r = 2.0 * math.pi * cutoff * t_e
        return r / (r + 1.0)

    def __call__(self, x: float, t: Optional[float] = None) -> float:
        if t is None:
            t = time.monotonic()

        if self.t_prev is None or self.x_prev is None:
            self.x_prev = float(x)
            self.dx_prev = 0.0
            self.t_prev = float(t)
            return float(x)

        t_e = float(t) - self.t_prev  # Elapsed time in seconds
        if t_e <= 0.0:
            return self.x_prev

        # 1. Filter derivative dx
        a_d = self._smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self.x_prev) / t_e
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        # 2. Adaptive cutoff frequency
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)

        # 3. Filter position x
        a = self._smoothing_factor(t_e, cutoff)
        x_hat = a * x + (1.0 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t

        return x_hat

    def reset(self):
        """Resets filter memory when tracking is lost."""
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None


def exponential_smooth(new_val: float, prev_val: Optional[float], factor: float = 5.0) -> float:
    """
    Simple exponential moving average filter.
    Higher factor = more smoothing (more latency).
    """
    if prev_val is None:
        return new_val
    if factor <= 1.0:
        return new_val
    return prev_val + (new_val - prev_val) / factor
