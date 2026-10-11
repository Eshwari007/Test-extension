"""Positions, cash, equity curve and peak-equity tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class Position:
    symbol: str
    qty: float
    avg_entry: float
    entry_time: pd.Timestamp
    stop: float | None = None
    initial_stop: float | None = None
    initial_qty: float = 0.0
    highest_close: float = 0.0
    bars_held: int = 0
    rungs_hit: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def initial_risk(self) -> float:
        """Dollar risk per unit at entry (entry - initial stop)."""
        if self.initial_stop is None:
            return 0.0
        return max(self.avg_entry - self.initial_stop, 0.0)

    def r_multiple(self, price: float) -> float:
        risk = self.initial_risk
        if risk <= 0:
            return 0.0
        return (price - self.avg_entry) / risk


@dataclass
class Fill:
    time: pd.Timestamp
    symbol: str
    side: str  # "buy" | "sell"
    qty: float
    price: float
    fee: float
    slippage: float
    reason: str
    order_id: str


@dataclass
class Trade:
    """A closed round trip (possibly across several partial exits)."""

    symbol: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    qty: float
    avg_entry: float
    avg_exit: float
    fees: float
    initial_risk: float
    exit_reason: str

    @property
    def gross_pnl(self) -> float:
        return (self.avg_exit - self.avg_entry) * self.qty

    @property
    def net_pnl(self) -> float:
        return self.gross_pnl - self.fees

    @property
    def r_multiple(self) -> float:
        if self.initial_risk <= 0:
            return 0.0
        return self.net_pnl / (self.initial_risk * self.qty)

    @property
    def return_pct(self) -> float:
        return self.net_pnl / (self.avg_entry * self.qty)


class Portfolio:
    def __init__(self, cash: float):
        self.cash = float(cash)
        self.initial_cash = float(cash)
        self.positions: dict[str, Position] = {}
        self.peak_equity = float(cash)
        self.equity_curve: list[tuple[pd.Timestamp, float]] = []
        self.fills: list[Fill] = []
        self.trades: list[Trade] = []
        self._open_legs: dict[str, dict[str, Any]] = {}

    # ---- marks -----------------------------------------------------------
    def equity(self, prices: dict[str, float]) -> float:
        value = self.cash
        for sym, pos in self.positions.items():
            value += pos.qty * prices.get(sym, pos.avg_entry)
        return value

    def gross_exposure(self, prices: dict[str, float]) -> float:
        return sum(p.qty * prices.get(s, p.avg_entry) for s, p in self.positions.items())

    def mark(self, time: pd.Timestamp, prices: dict[str, float]) -> float:
        eq = self.equity(prices)
        self.peak_equity = max(self.peak_equity, eq)
        self.equity_curve.append((time, eq))
        return eq

    def drawdown(self, prices: dict[str, float]) -> float:
        eq = self.equity(prices)
        if self.peak_equity <= 0:
            return 0.0
        return max(0.0, 1 - eq / self.peak_equity)

    # ---- fills -----------------------------------------------------------
    def apply_fill(self, fill: Fill, stop: float | None = None, meta: dict | None = None) -> None:
        self.fills.append(fill)
        cost = fill.qty * fill.price
        if fill.side == "buy":
            self.cash -= cost + fill.fee
            pos = self.positions.get(fill.symbol)
            if pos is None:
                pos = Position(
                    symbol=fill.symbol,
                    qty=fill.qty,
                    avg_entry=fill.price,
                    entry_time=fill.time,
                    stop=stop,
                    initial_stop=stop,
                    initial_qty=fill.qty,
                    highest_close=fill.price,
                    meta=meta or {},
                )
                self.positions[fill.symbol] = pos
                self._open_legs[fill.symbol] = {
                    "entry_time": fill.time,
                    "qty": fill.qty,
                    "entry_cost": cost,
                    "exit_value": 0.0,
                    "exit_qty": 0.0,
                    "fees": fill.fee,
                    "initial_risk": (fill.price - stop) if stop is not None else 0.0,
                    "last_exit_time": fill.time,
                    "exit_reason": "",
                }
            else:
                total = pos.qty + fill.qty
                pos.avg_entry = (pos.avg_entry * pos.qty + cost) / total
                pos.qty = total
                pos.initial_qty += fill.qty
                leg = self._open_legs[fill.symbol]
                leg["qty"] += fill.qty
                leg["entry_cost"] += cost
                leg["fees"] += fill.fee
        else:
            pos = self.positions[fill.symbol]
            self.cash += cost - fill.fee
            pos.qty -= fill.qty
            leg = self._open_legs[fill.symbol]
            leg["exit_value"] += cost
            leg["exit_qty"] += fill.qty
            leg["fees"] += fill.fee
            leg["last_exit_time"] = fill.time
            leg["exit_reason"] = fill.reason
            if pos.qty <= 1e-12:
                self._close_leg(fill.symbol)

    def _close_leg(self, symbol: str) -> None:
        leg = self._open_legs.pop(symbol)
        del self.positions[symbol]
        qty = leg["qty"]
        self.trades.append(
            Trade(
                symbol=symbol,
                entry_time=leg["entry_time"],
                exit_time=leg["last_exit_time"],
                qty=qty,
                avg_entry=leg["entry_cost"] / qty,
                avg_exit=leg["exit_value"] / leg["exit_qty"],
                fees=leg["fees"],
                initial_risk=leg["initial_risk"],
                exit_reason=leg["exit_reason"],
            )
        )

    # ---- views -----------------------------------------------------------
    def equity_series(self) -> pd.Series:
        if not self.equity_curve:
            return pd.Series(dtype=float)
        idx, vals = zip(*self.equity_curve)
        return pd.Series(vals, index=pd.DatetimeIndex(idx), name="equity")

    def trades_frame(self) -> pd.DataFrame:
        rows = [
            {
                "symbol": t.symbol,
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "qty": t.qty,
                "avg_entry": t.avg_entry,
                "avg_exit": t.avg_exit,
                "fees": t.fees,
                "gross_pnl": t.gross_pnl,
                "net_pnl": t.net_pnl,
                "r_multiple": t.r_multiple,
                "return_pct": t.return_pct,
                "exit_reason": t.exit_reason,
            }
            for t in self.trades
        ]
        return pd.DataFrame(rows)
