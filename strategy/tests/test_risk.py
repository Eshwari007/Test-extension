"""Risk tests (G2): exposure cap, position limits and every governor step at the exact threshold."""

import unittest

import pandas as pd

from strategy.core.config import load_spec
from strategy.core.portfolio import Fill, Portfolio
from strategy.core.risk import GovernorLevel, RiskManager

T = pd.Timestamp("2024-01-02", tz="UTC")


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.spec = load_spec("C2", verify=False)
        self.tier = self.spec.tiers["T2"]  # L=25%, 0.75% risk, 50% cap, 4 positions, 1 memecoin
        self.rm = RiskManager(self.tier, self.spec.governor, self.spec.max_order_notional_usd, self.spec.coin_tier)
        self.pf = Portfolio(10_000)

    def _open(self, sym, qty, price):
        self.pf.apply_fill(Fill(T, sym, "buy", qty, price, 0.0, 0.0, "t", sym), stop=price * 0.9)

    def test_volatility_sizing(self):
        r = self.rm.size_entry(10_000, 100, 95, self.pf, {}, GovernorLevel.NORMAL)
        self.assertAlmostEqual(r.qty, 10_000 * 0.0075 / 5)
        self.assertEqual(r.reason, "")

    def test_halve_governor_halves_size(self):
        r = self.rm.size_entry(10_000, 100, 95, self.pf, {}, GovernorLevel.HALVE)
        self.assertAlmostEqual(r.qty, 10_000 * 0.0075 / 5 / 2)
        self.assertEqual(r.reason, "governor:halve")

    def test_exposure_cap_clips(self):
        # tight stop -> huge qty; cap is 50% of 10k = 5000 notional
        r = self.rm.size_entry(10_000, 100, 99.9, self.pf, {}, GovernorLevel.NORMAL)
        self.assertAlmostEqual(r.qty * 100, 5000)
        self.assertEqual(r.reason, "exposure_cap_clipped")

    def test_exposure_cap_counts_open_and_reserved(self):
        self._open("SOL", 30, 100)  # 3000 exposure
        prices = {"SOL": 100.0}
        r = self.rm.size_entry(self.pf.equity(prices), 100, 99.9, self.pf, prices, GovernorLevel.NORMAL, reserved_notional=1500)
        self.assertAlmostEqual(r.qty * 100, 500, places=6)
        r = self.rm.size_entry(self.pf.equity(prices), 100, 99.9, self.pf, prices, GovernorLevel.NORMAL, reserved_notional=2000)
        self.assertEqual(r.qty, 0.0)
        self.assertEqual(r.reason, "exposure_cap")

    def test_stop_above_entry_rejected(self):
        r = self.rm.size_entry(10_000, 100, 101, self.pf, {}, GovernorLevel.NORMAL)
        self.assertEqual(r.qty, 0.0)

    def test_target_weight_sizing(self):
        r = self.rm.size_entry(10_000, 50, None, self.pf, {}, GovernorLevel.NORMAL, target_weight=0.1)
        self.assertAlmostEqual(r.qty * 50, 1000)

    def test_max_order_notional(self):
        big = Portfolio(1_000_000)
        r = self.rm.size_entry(1_000_000, 100, 99.99, big, {}, GovernorLevel.NORMAL)
        self.assertAlmostEqual(r.qty * 100, 200_000)

    def test_position_and_memecoin_limits(self):
        for s in ("SOL", "XRP", "ADA", "PEPE"):
            self._open(s, 1, 10)
        self.assertEqual(self.rm.can_open("LINK", self.pf, GovernorLevel.NORMAL), "max_positions")
        pf = Portfolio(10_000)
        pf.apply_fill(Fill(T, "PEPE", "buy", 1, 1, 0, 0, "t", "x"), stop=0.9)
        self.assertEqual(self.rm.can_open("SHIB", pf, GovernorLevel.NORMAL), "max_memecoins")
        self.assertEqual(self.rm.can_open("SOL", pf, GovernorLevel.NORMAL), "")
        self.assertEqual(self.rm.can_open("PEPE", pf, GovernorLevel.NORMAL), "already_open")
        self.assertEqual(self.rm.can_open("SOL", pf, GovernorLevel.BLOCK), "governor:block")

    def test_governor_thresholds_exact(self):
        L = 0.25
        eps = 1e-9
        self.assertEqual(self.rm.level_for_drawdown(0.33 * L - eps), GovernorLevel.NORMAL)
        self.assertEqual(self.rm.level_for_drawdown(0.33 * L), GovernorLevel.HALVE)
        self.assertEqual(self.rm.level_for_drawdown(0.53 * L - eps), GovernorLevel.HALVE)
        self.assertEqual(self.rm.level_for_drawdown(0.53 * L), GovernorLevel.BLOCK)
        self.assertEqual(self.rm.level_for_drawdown(0.80 * L - eps), GovernorLevel.BLOCK)
        self.assertEqual(self.rm.level_for_drawdown(0.80 * L), GovernorLevel.FLATTEN)
        self.assertEqual(self.rm.level_for_drawdown(L - eps), GovernorLevel.FLATTEN)
        self.assertEqual(self.rm.level_for_drawdown(L), GovernorLevel.KILL)

    def test_kill_is_sticky(self):
        self.assertEqual(self.rm.level_for_drawdown(0.25), GovernorLevel.KILL)
        self.assertEqual(self.rm.level_for_drawdown(0.0), GovernorLevel.KILL)

    def test_governor_resumes_after_flatten_cooldown_and_rebases(self):
        rm = RiskManager(self.tier, self.spec.governor, 200_000, self.spec.coin_tier, cooldown_bars=3)
        self.assertEqual(rm.governor_level(10_000), GovernorLevel.NORMAL)
        self.assertEqual(rm.governor_level(7_990), GovernorLevel.FLATTEN)      # -20.1% >= 80% of L
        self.assertEqual(rm.governor_level(7_990), GovernorLevel.FLATTEN)      # cooldown 1
        self.assertEqual(rm.governor_level(7_990), GovernorLevel.FLATTEN)      # cooldown 2
        self.assertEqual(rm.governor_level(7_990), GovernorLevel.FLATTEN)      # cooldown 3
        self.assertEqual(rm.governor_level(7_990), GovernorLevel.NORMAL)       # re-based at 7,990
        self.assertEqual(rm.governor_level(8_500), GovernorLevel.NORMAL)       # new governor peak 8,500
        self.assertEqual(rm.governor_level(7_790), GovernorLevel.HALVE)        # -8.4% of 8,500 > 33% of L; -22% all-time < L
        self.assertFalse(rm.killed)

    def test_kill_measures_from_all_time_peak_even_after_rebase(self):
        rm = RiskManager(self.tier, self.spec.governor, 200_000, self.spec.coin_tier, cooldown_bars=1)
        rm.governor_level(10_000)
        rm.governor_level(7_990)   # flatten
        rm.governor_level(7_990)   # cooldown
        self.assertEqual(rm.governor_level(7_990), GovernorLevel.NORMAL)
        self.assertEqual(rm.governor_level(7_490), GovernorLevel.KILL)         # -25.1% from 10,000 >= L
        self.assertTrue(rm.killed)

    def test_tier_table_matches_plan(self):
        rows = {
            "T1": (0.15, 0.005, 0.35, 3, 1),
            "T2": (0.25, 0.0075, 0.50, 4, 1),
            "T3": (0.40, 0.0125, 0.75, 5, 2),
            "T4": (0.60, 0.02, 1.00, 6, 3),
        }
        for name, (dd, risk, cap, npos, nmeme) in rows.items():
            t = self.spec.tiers[name]
            self.assertEqual((t.max_drawdown, t.risk_per_trade, t.gross_exposure_cap, t.max_positions, t.max_memecoins),
                             (dd, risk, cap, npos, nmeme))

    def test_governor_dollar_steps_match_plan_table(self):
        # Plan table: T3 (40%) halves at -13%, blocks at -21%, flattens at -32%, kills at -40%
        rm = RiskManager(self.spec.tiers["T3"], self.spec.governor, 200_000, self.spec.coin_tier)
        self.assertEqual(rm.level_for_drawdown(0.1321), GovernorLevel.HALVE)
        self.assertEqual(rm.level_for_drawdown(0.2121), GovernorLevel.BLOCK)
        self.assertEqual(rm.level_for_drawdown(0.3201), GovernorLevel.FLATTEN)
        self.assertEqual(rm.level_for_drawdown(0.40), GovernorLevel.KILL)


if __name__ == "__main__":
    unittest.main()
