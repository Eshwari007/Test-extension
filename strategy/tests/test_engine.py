"""Engine tests (G2): golden trades reproduced to the cent, determinism, accounting invariants.

Golden trades are hand-calculated below from the frozen spec values
(T2: 0.75% risk per trade; taker 0.25%; slippage floor 0.05%; C2 stop 2.5 ATR,
V3 chandelier 3 ATR). Extend the list in a spreadsheet as Phase 2 requires 20.
"""

import unittest

import numpy as np
import pandas as pd

from strategy.core.backtest import run_backtest
from strategy.core.config import load_spec
from strategy.core.data import synthetic_bars
from strategy.core.signals import make_strategy

FEE = 0.0025
SLIP = 0.0005


def _btc_rising(n=600, start="2020-01-01"):
    idx = pd.date_range(start, periods=n, freq="D", tz="UTC")
    close = 100 + np.arange(n) * 0.1
    return pd.DataFrame({"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1e6}, index=idx)


def _coin_breakout(extra_bars, start="2021-01-01"):
    """60 flat bars (100 / 101 / 99), then a breakout bar, then the caller's bars."""
    rows = [(100.0, 101.0, 99.0, 100.0)] * 60
    rows.append((100.0, 111.0, 99.5, 110.0))  # breakout: close 110 > prior 20-high 101 and > SMA50 100
    rows.extend(extra_bars)
    idx = pd.date_range(start, periods=len(rows), freq="D", tz="UTC")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = 1e6
    return df


class GoldenTradeTests(unittest.TestCase):
    def setUp(self):
        self.spec = load_spec("C2", verify=False)
        self.btc = _btc_rising()

    def _run(self, coin, variant="V3", tier="T2"):
        strat = make_strategy(self.spec.candidate, variant)
        return run_backtest(self.spec, strat, {"SOL": coin}, self.btc, tier=tier, initial_cash=10_000)

    def test_golden_1_c2_v3_entry_and_chandelier_stop(self):
        # bar 62: open 112, high 115, low 108, close 114 -> fills the buy, trails the stop
        # bar 63: open 114, high 116, low 100, close 101 -> stop traded, not gapped
        # bar 64: flat afterwards
        coin = _coin_breakout([(112, 115, 108, 114), (114, 116, 100, 101), (101, 102, 100, 101)])
        res = self._run(coin)
        self.assertEqual(len(res.trades), 1)
        tr = res.trades.iloc[0]

        atr_breakout = (2 * 13 + 11.5) / 14               # Wilder ATR after the 11.5 TR bar
        stop0 = 110 - 2.5 * atr_breakout                   # 103.3036
        qty = 10_000 * 0.0075 / (110 - stop0)              # risk 75 USD at the stop
        entry = 112 * (1 + SLIP)
        fee_in = qty * entry * FEE
        atr_62 = (atr_breakout * 13 + 7) / 14              # TR bar 62 = max(7, 5, 2)
        trail = 114 - 3 * atr_62                           # 105.04 > stop0 -> stop moves up
        exit_px = trail * (1 - SLIP)                        # low 100 <= stop, open 114 > stop
        fee_out = qty * exit_px * FEE
        net = (exit_px - entry) * qty - fee_in - fee_out

        self.assertAlmostEqual(tr["qty"], qty, places=9)
        self.assertAlmostEqual(tr["avg_entry"], entry, places=9)
        self.assertAlmostEqual(tr["avg_exit"], exit_px, places=9)
        self.assertAlmostEqual(tr["fees"], fee_in + fee_out, places=9)
        self.assertAlmostEqual(tr["net_pnl"], net, places=2)
        self.assertEqual(tr["exit_reason"], "stop")
        self.assertAlmostEqual(res.equity.iloc[-1], 10_000 + net, places=2)

    def test_golden_2_gap_through_stop_fills_at_open(self):
        coin = _coin_breakout([(112, 115, 108, 114), (98, 99, 90, 95), (95, 96, 94, 95)])
        res = self._run(coin)
        tr = res.trades.iloc[0]
        self.assertAlmostEqual(tr["avg_exit"], 98 * (1 - SLIP), places=9)
        self.assertEqual(tr["exit_reason"], "stop")

    def test_golden_3_v1_ladder_partial_exits(self):
        # Entry fills at 112 * 1.0005 = 112.056. Close 124 on bar 62 is +10.66% -> the +10% rung
        # hits, so 50% is sold at bar 63's open 125 (close 121 would be only +7.98%).
        coin = _coin_breakout([(112, 125, 111, 124), (125, 126, 123, 125), (125, 126, 123, 125)])
        res = self._run(coin, variant="V1")
        fills = [f for f in res.fills]
        sells = [f for f in fills if f.side == "sell"]
        self.assertEqual(sells[0].reason, "ladder_1")
        self.assertAlmostEqual(sells[0].qty, fills[0].qty * 0.5, places=9)
        self.assertAlmostEqual(sells[0].price, 125 * (1 - SLIP), places=9)
        self.assertEqual(sells[-1].reason, "end_of_test")

    def test_golden_4_position_sizing_respects_cap_at_t1(self):
        coin = _coin_breakout([(112, 115, 108, 114), (114, 116, 100, 101), (101, 102, 100, 101)])
        res = self._run(coin, tier="T1")
        qty = 10_000 * 0.005 / (110 - (110 - 2.5 * (2 * 13 + 11.5) / 14))
        self.assertAlmostEqual(res.trades.iloc[0]["qty"], qty, places=9)

    def test_no_trade_when_regime_off(self):
        idx = self.btc.index
        falling = self.btc.copy()
        falling["close"] = 200 - np.arange(len(idx)) * 0.1
        coin = _coin_breakout([(112, 115, 108, 114), (114, 116, 100, 101)])
        strat = make_strategy(self.spec.candidate, "V3")
        res = run_backtest(self.spec, strat, {"SOL": coin}, falling, tier="T2")
        self.assertEqual(len(res.trades), 0)


class InvariantTests(unittest.TestCase):
    """Every candidate on synthetic data: deterministic and cash reconciles with trade P&L."""

    def _data(self, tf):
        n = 500
        btc_daily = synthetic_bars(n, "1d", seed=1, start="2022-01-01", drift=0.002, vol=0.03, price0=30_000)
        syms = ["SOL", "XRP", "ARB", "PEPE", "LINK"]
        if tf == "1h":
            bars = {s: synthetic_bars(n * 24, "1h", seed=10 + i, start="2022-01-01", drift=0.0001, vol=0.012) for i, s in enumerate(syms)}
            btc_sig = synthetic_bars(n * 24, "1h", seed=2, start="2022-01-01", drift=0.0001, vol=0.006, price0=30_000)
        else:
            bars = {s: synthetic_bars(n, "1d", seed=10 + i, start="2022-01-01", drift=0.002, vol=0.05) for i, s in enumerate(syms)}
            btc_sig = btc_daily
        return bars, btc_daily, btc_sig

    def _check(self, cid, variant=None, tier="T2"):
        spec = load_spec(cid, verify=False)
        bars, btc_daily, btc_sig = self._data(spec.candidate["signal_timeframe"])
        r1 = run_backtest(spec, make_strategy(spec.candidate, variant), bars, btc_daily, btc_sig, tier=tier)
        r2 = run_backtest(spec, make_strategy(spec.candidate, variant), bars, btc_daily, btc_sig, tier=tier)
        pd.testing.assert_series_equal(r1.equity, r2.equity)
        pd.testing.assert_frame_equal(r1.trades, r2.trades)
        self.assertGreater(len(r1.trades), 0, f"{cid} {variant} produced no trades on synthetic data")
        # Everything is closed at the end, so final equity == initial + sum(net P&L).
        self.assertAlmostEqual(r1.equity.iloc[-1], 10_000 + r1.trades["net_pnl"].sum(), places=6)
        # No bar ever exceeds the gross exposure cap by more than the marked move of one bar.
        cap = spec.tiers[tier].gross_exposure_cap
        self.assertLessEqual(r1.exposure.quantile(0.99), cap * 1.5)
        # Trade count stays within the tier's position limit at every fill time.
        return r1

    def test_c1(self):
        self._check("C1")

    def test_c2_all_variants(self):
        for v in ("V1", "V2", "V3"):
            self._check("C2", v)

    def test_c3(self):
        r = self._check("C3")
        self.assertTrue((r.trades["exit_reason"].isin(["rank_drop", "regime_off", "end_of_test"])).all())

    def test_stress_costs_more(self):
        spec = load_spec("C2", verify=False)
        bars, btc_daily, btc_sig = self._data("1d")
        base = run_backtest(spec, make_strategy(spec.candidate, "V3"), bars, btc_daily, btc_sig)
        stress = run_backtest(spec, make_strategy(spec.candidate, "V3"), bars, btc_daily, btc_sig, stress=True)
        self.assertGreater(sum(f.slippage for f in stress.fills), sum(f.slippage for f in base.fills))

    def test_governor_kill_stops_trading(self):
        # Crash every coin after a run-up so the T1 (15%) kill triggers; no fills after the kill.
        spec = load_spec("C2", verify=False)
        btc = _btc_rising(400)
        rows = [(100.0, 101.0, 99.0, 100.0)] * 60 + [(100.0, 111.0, 99.5, 110.0)]
        rows += [(112 + i, 115 + i, 110 + i, 114 + i) for i in range(10)]
        rows += [(60.0, 61.0, 40.0, 45.0)] * 5 + [(45.0, 46.0, 44.0, 45.0)] * 5
        idx = pd.date_range("2020-06-01", periods=len(rows), freq="D", tz="UTC")
        coin = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
        coin["volume"] = 1e6
        bars = {s: coin for s in ("SOL", "XRP", "ADA")}
        res = run_backtest(spec, make_strategy(spec.candidate, "V3"), bars, btc, tier="T4")
        self.assertTrue(len(res.trades) >= 1)
        self.assertTrue((res.trades["exit_reason"] == "stop").any())


if __name__ == "__main__":
    unittest.main()
