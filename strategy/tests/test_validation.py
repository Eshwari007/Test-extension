"""Validation-protocol tests: Monte Carlo, deflated Sharpe, Kelly, gates, ranking, walk-forward."""

import unittest

import numpy as np
import pandas as pd

from strategy.core import validation as V
from strategy.core.config import RiskTier


class MonteCarloTests(unittest.TestCase):
    def test_deterministic_for_seed(self):
        r = np.array([0.02, -0.01, 0.03, -0.02, 0.01] * 10)
        a = V.monte_carlo(r, n_runs=200, seed=5)
        b = V.monte_carlo(r, n_runs=200, seed=5)
        self.assertEqual(a.dd_p95, b.dd_p95)
        self.assertEqual(a.terminal_p50, b.terminal_p50)

    def test_all_losses_give_full_drawdown(self):
        r = np.array([-0.5] * 10)
        mc = V.monte_carlo(r, n_runs=50, seed=0)
        self.assertAlmostEqual(mc.dd_p95, 1 - 0.5**10)
        self.assertLess(mc.terminal_p50, 0.01)

    def test_all_wins_have_no_drawdown(self):
        mc = V.monte_carlo(np.array([0.01] * 20), n_runs=50, seed=0)
        self.assertEqual(mc.dd_p95, 0.0)
        self.assertAlmostEqual(mc.terminal_p50, 1.01**20)


class StatisticsTests(unittest.TestCase):
    def test_deflated_sharpe_falls_with_more_trials(self):
        one = V.deflated_sharpe(1.5, 1, 500, 0.0, 3.0)
        many = V.deflated_sharpe(1.5, 200, 500, 0.0, 3.0)
        self.assertGreater(one, many)
        self.assertTrue(0 <= many <= 1)

    def test_kelly_fraction(self):
        r = np.array([0.1, -0.05, 0.1, -0.05])
        self.assertAlmostEqual(V.kelly_fraction(r), r.mean() / r.var(ddof=1))
        self.assertEqual(V.kelly_fraction(np.array([0.1])), 0.0)

    def test_norm_helpers(self):
        self.assertAlmostEqual(V.norm_cdf(0.0), 0.5)
        self.assertAlmostEqual(V.norm_ppf(0.975), 1.959964, places=5)


class GateTests(unittest.TestCase):
    def _inputs(self, **over):
        tier = RiskTier("Moderate", 0.25, 0.0075, 0.5, 4, 1)
        m = {"net_return": 0.2, "max_drawdown": 0.10, "trade_count": 150, "max_coin_profit_share": 0.2}
        wf = V.WalkForwardResult([V.WalkForwardWindow(None, None, None, None, "V3", 1.0, 100.0, 10)] * 4)
        mc = V.MonteCarloResult(10, 0, dd_p95=0.2, dd_p50=0.1, terminal_p05=1.0, terminal_p50=1.2, terminal_p95=1.5)
        rnd = V.RandomEntryResult(0.2, np.linspace(-0.1, 0.1, 100), "net_return", 0)
        g = V.GateInputs("C2", tier, {**m, **over.get("oos", {})}, {"net_return": over.get("stress", 0.05)}, mc, rnd, wf, 100)
        return g

    def test_all_pass(self):
        self.assertTrue(all(V.hard_gates(self._inputs()).values()))

    def test_drawdown_gate_uses_two_thirds_of_tier(self):
        gates = V.hard_gates(self._inputs(oos={"max_drawdown": 0.17}))
        self.assertFalse(gates["max_dd_within_2_3_tier"])
        gates = V.hard_gates(self._inputs(oos={"max_drawdown": 0.16}))
        self.assertTrue(gates["max_dd_within_2_3_tier"])

    def test_min_trades_and_stress(self):
        self.assertFalse(V.hard_gates(self._inputs(oos={"trade_count": 99}))["min_oos_trades"])
        self.assertFalse(V.hard_gates(self._inputs(stress=-0.01))["survives_double_cost"])

    def test_profit_concentration(self):
        self.assertFalse(V.hard_gates(self._inputs(oos={"max_coin_profit_share": 0.31}))["profit_concentration"])


class RankingTests(unittest.TestCase):
    def test_weighted_rank_prefers_better_metrics(self):
        scores = pd.DataFrame({
            "calmar": [2.0, 1.0], "walk_forward_consistency": [0.8, 0.6], "sortino": [2.0, 1.0],
            "parameter_robustness": [0.9, 0.5], "fees_pct_gross_profit": [0.1, 0.3], "simplicity": [4, 6],
        }, index=["A", "B"])
        ranked = V.rank_survivors(scores)
        self.assertEqual(list(ranked.index), ["A", "B"])
        self.assertAlmostEqual(ranked["A"], 1.0)


class WalkForwardTests(unittest.TestCase):
    def test_windows_roll_and_pick_variant_on_train(self):
        calls = []

        class R:
            def __init__(self, pnl, calmar):
                self.trades = pd.DataFrame({"net_pnl": [pnl]})
                self._c = calmar

            def metrics(self):
                return {"calmar": self._c}

        def run(variant, s, e):
            calls.append((variant, s, e))
            return R(10.0 if variant == "V2" else -5.0, 2.0 if variant == "V2" else 0.5)

        wf = V.walk_forward(run, ["V1", "V2"], pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC"), 12, 3)
        self.assertEqual(len(wf.windows), 4)
        self.assertTrue(all(w.chosen_variant == "V2" for w in wf.windows))
        self.assertEqual(wf.positive_fraction, 1.0)
        self.assertTrue(wf.passed())


if __name__ == "__main__":
    unittest.main()
