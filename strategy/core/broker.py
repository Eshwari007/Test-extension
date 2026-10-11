"""One broker interface with three adapters: SimBroker, AlpacaPaper, AlpacaLive.

SimBroker implements the backtest fill/cost model from specs/costs.yaml:
  * market orders fill at the next bar's open, pay the taker fee and slippage
    of max(half spread, floor) plus an extra for mid-caps and memecoins;
  * limit orders pay the maker fee and fill only if price trades through the
    limit by at least one tick;
  * stops fill at the worse of the stop price and the bar's open (gap-through).

The Alpaca adapters hit the REST API directly (urllib) so there is no hard
dependency on alpaca-py; drop it in later if preferred. Every order carries a
unique client_order_id so a restart can never double-submit.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .data import alpaca_headers
from .portfolio import Fill


@dataclass
class Order:
    symbol: str
    side: str                 # "buy" | "sell"
    qty: float
    type: str = "market"      # "market" | "limit" | "stop"
    limit_price: float | None = None
    stop_price: float | None = None
    reason: str = ""
    client_order_id: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.client_order_id:
            self.client_order_id = make_client_order_id(self)


def make_client_order_id(order: Order, salt: str = "") -> str:
    key = f"{order.symbol}|{order.side}|{order.qty:.8f}|{order.type}|{order.reason}|{salt}"
    return hashlib.sha1(key.encode()).hexdigest()[:20]


class Broker(ABC):
    @abstractmethod
    def submit(self, order: Order, **kwargs) -> Fill | None: ...

    @abstractmethod
    def positions(self) -> dict[str, float]: ...

    @abstractmethod
    def open_orders(self) -> list[dict[str, Any]]: ...


# ---------------------------------------------------------------------------
# SimBroker
# ---------------------------------------------------------------------------
class SimBroker(Broker):
    def __init__(
        self,
        costs: dict[str, Any],
        coin_tier_lookup,
        stress: bool = False,
        taker_everywhere: bool = False,
        tick_size: float = 1e-6,
    ):
        self.fees = costs["fees"]
        self.slip = costs["slippage"]
        self.coin_tier = coin_tier_lookup
        self.stress = stress
        self.taker_everywhere = taker_everywhere
        self.tick = tick_size
        self.measured_spread: dict[str, float] = {}
        self._positions: dict[str, float] = {}
        self._submitted: set[str] = set()

    # ---- cost model -----------------------------------------------------
    def slippage_rate(self, symbol: str) -> float:
        half_spread = self.measured_spread.get(symbol, 0.0) / 2
        rate = max(half_spread, self.slip["floor"])
        tier = self.coin_tier(symbol)
        if tier == "memecoin":
            rate += self.slip["extra_memecoin"]
        elif tier == "mid_cap":
            rate += self.slip["extra_midcap"]
        if self.stress:
            rate *= self.slip["stress_multiplier"]
        return rate

    def fee_rate(self, order_type: str) -> float:
        if order_type == "limit" and not self.taker_everywhere:
            return self.fees["maker"]
        return self.fees["taker"]

    # ---- fills ----------------------------------------------------------
    def submit(self, order: Order, bar: pd.Series | None = None, time: pd.Timestamp | None = None) -> Fill | None:
        """Fill `order` against `bar` (the bar AFTER the signal bar). Returns None if no fill."""
        if order.client_order_id in self._submitted:
            return None  # idempotent
        if bar is None or time is None:
            raise ValueError("SimBroker needs the bar to fill against")
        if order.qty <= 0:
            return None

        if order.type == "market":
            price = self._slipped(order, float(bar["open"]))
        elif order.type == "stop":
            assert order.stop_price is not None
            if order.side == "sell":
                if float(bar["open"]) <= order.stop_price:
                    raw = float(bar["open"])          # gapped through
                elif float(bar["low"]) <= order.stop_price:
                    raw = order.stop_price
                else:
                    return None
            else:
                if float(bar["open"]) >= order.stop_price:
                    raw = float(bar["open"])
                elif float(bar["high"]) >= order.stop_price:
                    raw = order.stop_price
                else:
                    return None
            price = self._slipped(order, raw)
        elif order.type == "limit":
            assert order.limit_price is not None
            if order.side == "buy":
                if float(bar["low"]) > order.limit_price - self.tick:
                    return None
                price = min(order.limit_price, float(bar["open"]))
            else:
                if float(bar["high"]) < order.limit_price + self.tick:
                    return None
                price = max(order.limit_price, float(bar["open"]))
        else:
            raise ValueError(f"unknown order type {order.type}")

        fee = order.qty * price * self.fee_rate(order.type)
        slip_cost = 0.0
        if order.type != "limit":
            raw = price / (1 + self.slippage_rate(order.symbol)) if order.side == "buy" else price / (1 - self.slippage_rate(order.symbol))
            slip_cost = abs(price - raw) * order.qty
        self._submitted.add(order.client_order_id)
        self._positions[order.symbol] = self._positions.get(order.symbol, 0.0) + (
            order.qty if order.side == "buy" else -order.qty
        )
        return Fill(
            time=time,
            symbol=order.symbol,
            side=order.side,
            qty=order.qty,
            price=price,
            fee=fee,
            slippage=slip_cost,
            reason=order.reason,
            order_id=order.client_order_id,
        )

    def _slipped(self, order: Order, raw: float) -> float:
        rate = self.slippage_rate(order.symbol)
        return raw * (1 + rate) if order.side == "buy" else raw * (1 - rate)

    def positions(self) -> dict[str, float]:
        return {k: v for k, v in self._positions.items() if abs(v) > 1e-12}

    def open_orders(self) -> list[dict[str, Any]]:
        return []


# ---------------------------------------------------------------------------
# Alpaca adapters
# ---------------------------------------------------------------------------
class AlpacaBroker(Broker):
    """Thin REST adapter. Paper and live differ only by base URL."""

    PAPER_URL = "https://paper-api.alpaca.markets"
    LIVE_URL = "https://api.alpaca.markets"

    def __init__(self, paper: bool = True, key: str | None = None, secret: str | None = None):
        self.base = self.PAPER_URL if paper else self.LIVE_URL
        # Empty when the keys are injected by an egress proxy (cloud network secret).
        self.headers = alpaca_headers(key, secret)

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        for k, v in self.headers.items():
            req.add_header(k, v)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode() or "null")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Alpaca {method} {path}: {exc.code} {exc.read().decode()}") from exc

    @staticmethod
    def pair(symbol: str) -> str:
        return symbol if "/" in symbol else f"{symbol}/USD"

    def submit(self, order: Order, **kwargs) -> Fill | None:
        body: dict[str, Any] = {
            "symbol": self.pair(order.symbol),
            "qty": f"{order.qty:.8f}",
            "side": order.side,
            "type": "market" if order.type == "stop" else order.type,  # stops are client-side
            "time_in_force": "gtc",
            "client_order_id": order.client_order_id,
        }
        if order.type == "limit":
            body["limit_price"] = f"{order.limit_price:.8f}"
        resp = self._request("POST", "/v2/orders", body)
        if resp.get("filled_qty") and float(resp["filled_qty"]) > 0:
            qty = float(resp["filled_qty"])
            price = float(resp["filled_avg_price"])
            return Fill(
                time=pd.Timestamp.now(tz="UTC"),
                symbol=order.symbol,
                side=order.side,
                qty=qty,
                price=price,
                fee=0.0,  # fees are reported on the account activity feed; reconcile separately
                slippage=0.0,
                reason=order.reason,
                order_id=resp["id"],
            )
        return None

    def get_order(self, order_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v2/orders/{order_id}")

    def positions(self) -> dict[str, float]:
        rows = self._request("GET", "/v2/positions") or []
        return {r["symbol"].replace("USD", "").replace("/", ""): float(r["qty"]) for r in rows}

    def open_orders(self) -> list[dict[str, Any]]:
        return self._request("GET", "/v2/orders?status=open") or []

    def cancel_all(self) -> None:
        self._request("DELETE", "/v2/orders")

    def account(self) -> dict[str, Any]:
        return self._request("GET", "/v2/account")
