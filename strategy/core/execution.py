"""Turn target positions into orders; client-side stop/target manager.

Alpaca crypto has no bracket/OCO orders, so stops live here, on the Position,
and are submitted as market orders the moment a bar trades through them. The
same class drives SimBroker in backtests and AlpacaBroker in paper/live.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .broker import Broker, Order, SimBroker, make_client_order_id
from .portfolio import Fill, Portfolio
from .risk import GovernorLevel, RiskManager
from .signals import BarContext, EntryIntent, ExitIntent


@dataclass
class PendingOrder:
    order: Order
    stop: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionLog:
    """Every decision is logged: bar, signal, size, order, fill, fees."""

    rows: list[dict[str, Any]] = field(default_factory=list)

    def add(self, **kw: Any) -> None:
        self.rows.append(kw)

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


class ExecutionEngine:
    def __init__(self, broker: Broker, risk: RiskManager, portfolio: Portfolio, log: DecisionLog | None = None):
        self.broker = broker
        self.risk = risk
        self.portfolio = portfolio
        self.log = log or DecisionLog()
        self.pending: list[PendingOrder] = []
        self.rejections: list[dict[str, Any]] = []

    # ---- reservations ------------------------------------------------------
    def pending_buy_symbols(self) -> set[str]:
        return {p.order.symbol for p in self.pending if p.order.side == "buy"}

    def pending_buy_notional(self) -> float:
        return sum(p.meta.get("notional", 0.0) for p in self.pending if p.order.side == "buy")

    # ---- queueing (called at the signal bar's close) -------------------------
    def queue_entry(self, intent: EntryIntent, ctx: BarContext, level: GovernorLevel) -> bool:
        reason = self.risk.can_open(intent.symbol, ctx.portfolio, level)
        if not reason and intent.symbol in self.pending_buy_symbols():
            reason = "already_pending"
        if not reason and len(ctx.portfolio.positions) + len(self.pending_buy_symbols()) >= self.risk.tier.max_positions:
            reason = "max_positions"
        if reason:
            self.rejections.append({"time": ctx.time, "symbol": intent.symbol, "reason": reason})
            return False
        price = ctx.prices[intent.symbol]
        equity = ctx.portfolio.equity(ctx.prices)
        sizing = self.risk.size_entry(
            equity, price, intent.stop, ctx.portfolio, ctx.prices, level,
            target_weight=intent.target_weight, reserved_notional=self.pending_buy_notional(),
        )
        if sizing.qty <= 0:
            self.rejections.append({"time": ctx.time, "symbol": intent.symbol, "reason": sizing.reason})
            return False
        order = Order(intent.symbol, "buy", sizing.qty, "market", reason=intent.reason)
        order.client_order_id = make_client_order_id(order, salt=str(ctx.time))
        self.pending.append(PendingOrder(order, stop=intent.stop, meta={"notional": sizing.qty * price, "signal_time": ctx.time}))
        self.log.add(time=ctx.time, symbol=intent.symbol, event="queue_buy", qty=sizing.qty, stop=intent.stop,
                     price_ref=price, size_note=sizing.reason, reason=intent.reason)
        return True

    def queue_exit(self, intent: ExitIntent, ctx: BarContext) -> bool:
        pos = ctx.portfolio.positions.get(intent.symbol)
        if pos is None or intent.fraction <= 0:
            return False
        already = sum(p.order.qty for p in self.pending if p.order.side == "sell" and p.order.symbol == intent.symbol)
        qty = min(pos.qty * intent.fraction, pos.qty - already)
        if qty <= 1e-12:
            return False
        order = Order(intent.symbol, "sell", qty, "market", reason=intent.reason)
        order.client_order_id = make_client_order_id(order, salt=str(ctx.time))
        self.pending.append(PendingOrder(order, meta={"signal_time": ctx.time}))
        self.log.add(time=ctx.time, symbol=intent.symbol, event="queue_sell", qty=qty, reason=intent.reason)
        return True

    def flatten(self, ctx: BarContext, reason: str) -> None:
        self.pending = [p for p in self.pending if p.order.side == "sell"]  # cancel queued buys
        for sym in list(ctx.portfolio.positions):
            self.queue_exit(ExitIntent(sym, 1.0, reason), ctx)

    # ---- fills (called at the NEXT bar) -------------------------------------
    def process_pending(self, time: pd.Timestamp, bars: dict[str, pd.Series]) -> list[Fill]:
        """Fill queued orders against this bar's open. Orders for symbols with no bar wait."""
        fills: list[Fill] = []
        keep: list[PendingOrder] = []
        for p in self.pending:
            bar = bars.get(p.order.symbol)
            if bar is None:
                keep.append(p)
                continue
            pos = self.portfolio.positions.get(p.order.symbol)
            if p.order.side == "sell" and (pos is None or pos.qty <= 1e-12):
                continue  # position already closed by a stop
            if p.order.side == "sell" and pos is not None:
                p.order.qty = min(p.order.qty, pos.qty)
            fill = self._submit(p.order, bar, time)
            if fill is None:
                keep.append(p)
                continue
            self.portfolio.apply_fill(fill, stop=p.stop)
            fills.append(fill)
            self.log.add(time=time, symbol=fill.symbol, event="fill", side=fill.side, qty=fill.qty,
                         price=fill.price, fee=fill.fee, slippage=fill.slippage, reason=fill.reason, order_id=fill.order_id)
        self.pending = keep
        return fills

    def check_stops(self, time: pd.Timestamp, bars: dict[str, pd.Series]) -> list[Fill]:
        """Submit a stop-market for any position whose stop traded in this bar."""
        fills: list[Fill] = []
        for sym, pos in list(self.portfolio.positions.items()):
            bar = bars.get(sym)
            if pos.stop is None or bar is None:
                continue
            if float(bar["low"]) > pos.stop:
                continue
            order = Order(sym, "sell", pos.qty, "stop", stop_price=pos.stop, reason="stop")
            order.client_order_id = make_client_order_id(order, salt=str(time))
            fill = self._submit(order, bar, time)
            if fill is None:
                continue
            self.portfolio.apply_fill(fill)
            fills.append(fill)
            self.pending = [p for p in self.pending if not (p.order.symbol == sym and p.order.side == "sell")]
            self.log.add(time=time, symbol=sym, event="fill", side="sell", qty=fill.qty, price=fill.price,
                         fee=fill.fee, slippage=fill.slippage, reason="stop", order_id=fill.order_id)
        return fills

    def _submit(self, order: Order, bar: pd.Series, time: pd.Timestamp) -> Fill | None:
        if isinstance(self.broker, SimBroker):
            return self.broker.submit(order, bar=bar, time=time)
        return self.broker.submit(order)
