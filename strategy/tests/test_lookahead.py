"""Look-ahead test (G2): truncate the data at t, recompute, and assert every feature at t is unchanged."""

import unittest

import numpy as np
import pandas as pd

from strategy.core.config import load_spec
from strategy.core.data import synthetic_bars
from strategy.core.signals import daily_to_signal_tf, make_strategy


def _assert_row_equal(full: pd.DataFrame, trunc: pd.DataFrame, t):
    a = full.loc[t]
    b = trunc.loc[t]
    for col in full.columns:
        x, y = a[col], b[col]
        if np.isnan(x) and np.isnan(y):
            continue
        assert x == y, f"{col} at {t}: full={x} truncated={y}"


class LookAheadTests(unittest.TestCase):
    def setUp(self):
        self.daily = synthetic_bars(400, "1d", seed=11, start="2022-01-01")
        self.hourly = synthetic_bars(400 * 24, "1h", seed=12, start="2022-01-01")
        self.btc_daily = synthetic_bars(400, "1d", seed=13, start="2022-01-01", price0=30_000)
        self.btc_hourly = synthetic_bars(400 * 24, "1h", seed=14, start="2022-01-01", price0=30_000)

    def _check(self, strategy, bars, btc_daily, btc_signal, probe_rows):
        full = strategy.build_features(bars)
        full_btc = strategy.build_btc_features(btc_daily, btc_signal)
        for i in probe_rows:
            t = bars.index[i]
            trunc = strategy.build_features(bars.iloc[: i + 1])
            _assert_row_equal(full, trunc, t)
            tb = btc_signal.index[btc_signal.index.searchsorted(t, side="right") - 1]
            trunc_btc = strategy.build_btc_features(btc_daily[btc_daily.index <= t], btc_signal[btc_signal.index <= t])
            _assert_row_equal(full_btc, trunc_btc, tb)

    def test_c1_features_are_causal(self):
        s = make_strategy(load_spec("C1", verify=False).candidate)
        self._check(s, self.hourly, self.btc_daily, self.btc_hourly, [300, 2000, 5000, 9000])

    def test_c2_features_are_causal(self):
        for variant in ("V1", "V2", "V3"):
            s = make_strategy(load_spec("C2", verify=False).candidate, variant)
            self._check(s, self.daily, self.btc_daily, self.btc_daily, [60, 150, 250, 399])

    def test_c3_features_are_causal(self):
        s = make_strategy(load_spec("C3", verify=False).candidate)
        self._check(s, self.daily, self.btc_daily, self.btc_daily, [100, 250, 399])

    def test_daily_to_intraday_mapping_waits_for_the_daily_close(self):
        daily = pd.Series([0.0, 1.0], index=pd.date_range("2024-01-01", periods=2, freq="D", tz="UTC"))
        hourly_idx = pd.date_range("2024-01-01", periods=72, freq="h", tz="UTC")
        mapped = daily_to_signal_tf(daily, hourly_idx)
        # The 2024-01-02 daily bar (value 1.0) is only known from 2024-01-03 00:00.
        self.assertEqual(mapped.loc["2024-01-02 23:00"], 0.0)
        self.assertEqual(mapped.loc["2024-01-03 00:00"], 1.0)
        self.assertTrue(np.isnan(mapped.loc["2024-01-01 12:00"]))


if __name__ == "__main__":
    unittest.main()
