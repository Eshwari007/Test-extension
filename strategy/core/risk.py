"""Volatility sizing, exposure cap, position/memecoin limits, drawdown governor.

The overlay is identical across candidates so they are compared on signal
quality alone. All thresholds come from specs/risk_tiers.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .config import RiskTier
from .portfolio import Portfolio


class GovernorLevel(IntEnum):
    NORMAL = 0
    HALVE = 1          # at 33% of L: halve position sizes
    BLOCK = 2          # at 53% of L: block new entries, manage exits only
    FLATTEN = 3        # at 80% of L: flatten everything to cash
    KILL = 4           # at 100% of L: retire the strategy


@dataclass
class SizingResult:
    qty: float
    reason: str  # "" when sized normally, otherwise why it was cut or rejected


class RiskManager:
    def __init__(
        self,
        tier: RiskTier,
        governor: dict[str, float],
        max_order_notional: float,
        coin_tier_lookup,
    ):
        self.tier = tier
        self.governor = governor
        self.max_order_notional = max_order_notional
        self.coin_tier = coin_tier_lookup
        self.killed = False

    # ---- governor ----------------------------------------------------------
    def governor_level(self, drawdown: float) -> GovernorLevel:
        if self.killed:
            return GovernorLevel.KILL
        share = drawdown / self.tier.max_drawdown if self.tier.max_drawdown > 0 else 0.0
        if share >= self.governor["kill"]:
            self.killed = True
            return GovernorLevel.KILL
        if share >= self.governor["flatten"]:
            return GovernorLevel.FLATTEN
        if share >= self.governor["block_entries"]:
            return GovernorLevel.BLOCK
        if share >= self.governor["halve_size"]:
            return GovernorLevel.HALVE
        return GovernorLevel.NORMAL

    # ---- limits -------------------------------------------------------------
    def can_open(self, symbol: str, portfolio: Portfolio, level: GovernorLevel) -> str:
        """Return "" if a new position in `symbol` is allowed, else the reason."""
        if level >= GovernorLevel.BLOCK:
            return f"governor:{level.name.lower()}"
        if symbol in portfolio.positions:
            return "already_open"
        if len(portfolio.positions) >= self.tier.max_positions:
            return "max_positions"
        if self.coin_tier(symbol) == "memecoin":
            open_memes = sum(1 for s in portfolio.positions if self.coin_tier(s) == "memecoin")
            if open_memes >= self.tier.max_memecoins:
                return "max_memecoins"
        return ""

    # ---- sizing -------------------------------------------------------------
    def size_entry(
        self,
        equity: float,
        entry_price: float,
        stop_price: float | None,
        portfolio: Portfolio,
        prices: dict[str, float],
        level: GovernorLevel,
        target_weight: float | None = None,
        reserved_notional: float = 0.0,
    ) -> SizingResult:
        """Quantity to buy so the position risks `risk_per_trade` of equity at its stop.

        For candidates without a stop (C3) pass `target_weight` and the size is
        `target_weight * equity`, still capped by exposure and order limits.
        """
        if entry_price <= 0:
            return SizingResult(0.0, "bad_price")
        reason = ""
        if stop_price is not None:
            risk_per_unit = entry_price - stop_price
            if risk_per_unit <= 0:
                return SizingResult(0.0, "stop_above_entry")
            dollar_risk = equity * self.tier.risk_per_trade
            if level == GovernorLevel.HALVE:
                dollar_risk *= 0.5
                reason = "governor:halve"
            qty = dollar_risk / risk_per_unit
        elif target_weight is not None:
            weight = target_weight * (0.5 if level == GovernorLevel.HALVE else 1.0)
            if level == GovernorLevel.HALVE:
                reason = "governor:halve"
            qty = weight * equity / entry_price
        else:
            return SizingResult(0.0, "no_stop_or_weight")

        notional = qty * entry_price
        # Gross exposure cap (no margin: cash is also a hard ceiling).
        # `reserved_notional` covers buys already queued for the next open.
        cap_room = self.tier.gross_exposure_cap * equity - portfolio.gross_exposure(prices) - reserved_notional
        room = min(cap_room, portfolio.cash - reserved_notional, self.max_order_notional)
        if room <= 0:
            return SizingResult(0.0, "exposure_cap")
        if notional > room:
            qty = room / entry_price
            reason = reason or "exposure_cap_clipped"
        return SizingResult(qty, reason)
