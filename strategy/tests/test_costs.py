"""Cost-model tests (G2): fees, slippage, gap-through stops, limit fills, idempotency."""

import unittest

import pandas as pd

from strategy.core.broker import Order, SimBroker, make_client_order_id
from strategy.core.config import load_spec

T = pd.Timestamp("2024-01-02", tz="UTC")


def _bar(o, h, l, c):
    return pd.Series({"open": o, "high": h, "low": l, "close": c, "volume": 1.0})


class SimBrokerCostTests(unittest.TestCase):
    def setUp(self):
        self.spec = load_spec("C2", verify=False)
        self.broker = SimBroker(self.spec.costs, self.spec.coin_tier)

    def test_market_buy_pays_taker_and_floor_slippage(self):
        fill = self.broker.submit(Order("SOL", "buy", 10, "market"), bar=_bar(100, 105, 95, 102), time=T)
        self.assertAlmostEqual(fill.price, 100 * 1.0005)
        self.assertAlmostEqual(fill.fee, 10 * 100.05 * 0.0025)
        self.assertAlmostEqual(fill.slippage, 10 * 0.05, places=9)

    def test_market_sell_slips_down(self):
        fill = self.broker.submit(Order("SOL", "sell", 10, "market"), bar=_bar(100, 105, 95, 102), time=T)
        self.assertAlmostEqual(fill.price, 100 * 0.9995)

    def test_memecoin_and_midcap_extra_slippage(self):
        meme = self.broker.submit(Order("PEPE", "buy", 1, "market"), bar=_bar(1, 1, 1, 1), time=T)
        mid = self.broker.submit(Order("ARB", "buy", 1, "market"), bar=_bar(1, 1, 1, 1), time=T)
        large = self.broker.submit(Order("SOL", "buy", 1, "market"), bar=_bar(1, 1, 1, 1), time=T)
        self.assertAlmostEqual(meme.price, 1 * (1 + 0.0005 + 0.0010))
        self.assertAlmostEqual(mid.price, 1 * (1 + 0.0005 + 0.0010))
        self.assertAlmostEqual(large.price, 1 * 1.0005)

    def test_measured_spread_overrides_floor(self):
        self.broker.measured_spread["SOL"] = 0.004  # half spread 0.2% > 0.05% floor
        fill = self.broker.submit(Order("SOL", "buy", 1, "market"), bar=_bar(100, 100, 100, 100), time=T)
        self.assertAlmostEqual(fill.price, 100 * 1.002)

    def test_stress_doubles_slippage_not_fees(self):
        stressed = SimBroker(self.spec.costs, self.spec.coin_tier, stress=True)
        fill = stressed.submit(Order("SOL", "buy", 1, "market"), bar=_bar(100, 100, 100, 100), time=T)
        self.assertAlmostEqual(fill.price, 100 * 1.001)
        self.assertAlmostEqual(fill.fee, 100.1 * 0.0025)

    def test_stop_fills_at_stop_when_not_gapped(self):
        fill = self.broker.submit(Order("SOL", "sell", 1, "stop", stop_price=95), bar=_bar(100, 101, 90, 92), time=T)
        self.assertAlmostEqual(fill.price, 95 * 0.9995)

    def test_stop_gap_through_fills_at_open(self):
        fill = self.broker.submit(Order("SOL", "sell", 1, "stop", stop_price=95), bar=_bar(90, 91, 85, 88), time=T)
        self.assertAlmostEqual(fill.price, 90 * 0.9995)

    def test_stop_not_touched_no_fill(self):
        fill = self.broker.submit(Order("SOL", "sell", 1, "stop", stop_price=95), bar=_bar(100, 101, 96, 99), time=T)
        self.assertIsNone(fill)

    def test_limit_requires_trade_through_and_pays_maker(self):
        none = self.broker.submit(Order("SOL", "buy", 1, "limit", limit_price=95), bar=_bar(100, 101, 95.5, 99), time=T)
        self.assertIsNone(none)
        fill = self.broker.submit(Order("SOL", "buy", 1, "limit", limit_price=95), bar=_bar(100, 101, 94, 99), time=T)
        self.assertAlmostEqual(fill.price, 95)
        self.assertAlmostEqual(fill.fee, 95 * 0.0015)
        self.assertAlmostEqual(fill.slippage, 0.0)

    def test_taker_everywhere_flag(self):
        b = SimBroker(self.spec.costs, self.spec.coin_tier, taker_everywhere=True)
        fill = b.submit(Order("SOL", "buy", 1, "limit", limit_price=95), bar=_bar(100, 101, 94, 99), time=T)
        self.assertAlmostEqual(fill.fee, 95 * 0.0025)

    def test_duplicate_client_order_id_is_ignored(self):
        o = Order("SOL", "buy", 1, "market")
        first = self.broker.submit(o, bar=_bar(100, 100, 100, 100), time=T)
        second = self.broker.submit(o, bar=_bar(100, 100, 100, 100), time=T)
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(self.broker.positions()["SOL"], 1)

    def test_client_order_id_changes_with_salt(self):
        o = Order("SOL", "buy", 1, "market")
        self.assertNotEqual(make_client_order_id(o, "t1"), make_client_order_id(o, "t2"))


if __name__ == "__main__":
    unittest.main()
