"""Unit tests for every indicator against hand-computed / reference values (G2)."""

import unittest

import numpy as np
import pandas as pd

from strategy.core import features as F


def _series(values):
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="D", tz="UTC"), dtype=float)


class SmaEmaTests(unittest.TestCase):
    def test_sma_matches_hand_values(self):
        s = _series([1, 2, 3, 4, 5])
        out = F.sma(s, 3)
        self.assertTrue(np.isnan(out.iloc[0]) and np.isnan(out.iloc[1]))
        self.assertAlmostEqual(out.iloc[2], 2.0)
        self.assertAlmostEqual(out.iloc[4], 4.0)

    def test_ema_recursion(self):
        s = _series([10, 11, 12, 13, 14, 15])
        out = F.ema(s, 3)
        k = 2 / 4
        # pandas ewm(adjust=False) seeds with the first value; check the recursion holds.
        prev = out.iloc[2]
        for i in range(3, len(s)):
            expected = s.iloc[i] * k + prev * (1 - k)
            self.assertAlmostEqual(out.iloc[i], expected, places=10)
            prev = expected


class AtrTests(unittest.TestCase):
    def test_atr_wilder_seed_and_recursion(self):
        n = 20
        idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
        high = pd.Series(101.0, index=idx)
        low = pd.Series(99.0, index=idx)
        close = pd.Series(100.0, index=idx)
        # Flat bars: TR = 2 everywhere (high-low = 2 dominates), so ATR = 2 after the seed.
        out = F.atr(high, low, close, 14)
        self.assertTrue(np.isnan(out.iloc[12]))
        self.assertAlmostEqual(out.iloc[13], 2.0)
        self.assertAlmostEqual(out.iloc[19], 2.0)
        # One wide bar then Wilder smoothing: (2*13 + 11.5)/14
        high.iloc[19] = 111.0
        low.iloc[19] = 99.5
        close.iloc[19] = 110.0
        out = F.atr(high, low, close, 14)
        self.assertAlmostEqual(out.iloc[19], (2 * 13 + 11.5) / 14, places=10)

    def test_true_range_uses_previous_close(self):
        high = _series([10, 12])
        low = _series([9, 11])
        close = _series([9.5, 11.5])
        tr = F.true_range(high, low, close)
        # bar 2: max(12-11, |12-9.5|, |11-9.5|) = 2.5
        self.assertAlmostEqual(tr.iloc[1], 2.5)


class DonchianTests(unittest.TestCase):
    def test_donchian_includes_current_bar_and_shift_gives_prior(self):
        high = _series([1, 5, 3, 4, 2])
        dh = F.donchian_high(high, 3)
        self.assertAlmostEqual(dh.iloc[2], 5)
        self.assertAlmostEqual(dh.iloc[4], 4)
        prior = dh.shift(1)
        self.assertAlmostEqual(prior.iloc[3], 5)


class MomentumTests(unittest.TestCase):
    def test_momentum_score_sign(self):
        up = _series(np.exp(np.linspace(0, 1, 60)) + np.r_[np.zeros(59), 0.0])
        rng = np.random.default_rng(0)
        noisy = up * (1 + rng.normal(0, 0.001, 60))
        score = F.momentum_score(noisy, 30)
        self.assertGreater(score.iloc[-1], 0)

    def test_realized_vol_matches_numpy(self):
        rng = np.random.default_rng(1)
        s = _series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 50))))
        vol = F.realized_vol(s, 10)
        lr = np.log(s.values[1:] / s.values[:-1])
        self.assertAlmostEqual(vol.iloc[-1], np.std(lr[-10:], ddof=1), places=12)


class OscillatorTests(unittest.TestCase):
    def test_rsi_bounds_and_extremes(self):
        s = _series(np.arange(1, 40, dtype=float))
        r = F.rsi(s, 14)
        self.assertAlmostEqual(r.iloc[-1], 100.0)
        s = _series(np.arange(40, 1, -1, dtype=float))
        r = F.rsi(s, 14)
        self.assertAlmostEqual(r.iloc[-1], 0.0)

    def test_adx_in_range(self):
        rng = np.random.default_rng(2)
        close = _series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 120))))
        high = close * 1.01
        low = close * 0.99
        a = F.adx(high, low, close, 14).dropna()
        self.assertTrue(((a >= 0) & (a <= 100)).all())

    def test_macd_columns(self):
        rng = np.random.default_rng(3)
        close = _series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 120))))
        m = F.macd(close)
        self.assertEqual(list(m.columns), ["macd", "signal", "hist"])
        self.assertAlmostEqual(m["hist"].iloc[-1], m["macd"].iloc[-1] - m["signal"].iloc[-1])


if __name__ == "__main__":
    unittest.main()
