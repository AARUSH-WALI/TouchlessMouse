import random
import numpy as np
import pytest
from src.core.smoothing import OneEuroFilter, exponential_smooth


def test_one_euro_filter_initialization():
    f = OneEuroFilter(min_cutoff=1.0, beta=0.007)
    val = f(100.0, t=1.0)
    assert val == 100.0


def test_one_euro_filter_reduces_jitter():
    """High-frequency random noise should be smoothed out."""
    random.seed(42)
    f = OneEuroFilter(min_cutoff=1.0, beta=0.007)
    noisy_signal = [100.0 + random.gauss(0, 5) for _ in range(100)]
    smoothed = [f(v, t=i * 0.033) for i, v in enumerate(noisy_signal)]

    assert np.std(smoothed[10:]) < np.std(noisy_signal[10:])


def test_exponential_smooth():
    assert exponential_smooth(100.0, None) == 100.0
    # prev=0, new=10, factor=2 -> 0 + 10/2 = 5
    assert exponential_smooth(10.0, 0.0, factor=2.0) == 5.0
