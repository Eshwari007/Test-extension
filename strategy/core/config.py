"""Load the frozen YAML specs and verify them against the registered hash.

Gate G0: the spec document is committed; any later change requires a new commit
stating the reason. `check_registry` refuses to run if a spec's hash differs
from the one recorded in `specs/REGISTRY.json`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SPEC_DIR = Path(__file__).resolve().parent.parent / "specs"
REGISTRY_FILE = SPEC_DIR / "REGISTRY.json"

CANDIDATE_FILES = {
    "C1": "c1_intraday.yaml",
    "C2": "c2_swing.yaml",
    "C3": "c3_position.yaml",
}
SHARED_FILES = ["risk_tiers.yaml", "costs.yaml", "universe.yaml", "periods.yaml"]


class SpecHashMismatch(RuntimeError):
    """A spec file no longer matches the hash frozen at Gate G0."""


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class RiskTier:
    name: str
    max_drawdown: float
    risk_per_trade: float
    gross_exposure_cap: float
    max_positions: int
    max_memecoins: int


@dataclass
class Spec:
    """Everything a single backtest run needs, loaded from the frozen YAML files."""

    candidate: dict[str, Any]
    tiers: dict[str, RiskTier]
    governor: dict[str, float]
    max_order_notional_usd: float
    costs: dict[str, Any]
    universe: dict[str, Any]
    periods: dict[str, Any]
    hashes: dict[str, str] = field(default_factory=dict)

    @property
    def candidate_id(self) -> str:
        return self.candidate["id"]

    def coin_tier(self, symbol: str) -> str:
        for tier_name, coins in self.universe["tiers"].items():
            if symbol in coins:
                return tier_name
        return "unknown"

    def config_hash(self) -> str:
        """Single hash over every spec file, written into every run log."""
        joined = "|".join(f"{k}={v}" for k, v in sorted(self.hashes.items()))
        return hashlib.sha256(joined.encode()).hexdigest()[:16]


def load_spec(candidate_id: str, spec_dir: Path = SPEC_DIR, verify: bool = True) -> Spec:
    candidate_file = spec_dir / CANDIDATE_FILES[candidate_id]
    files = [candidate_file] + [spec_dir / f for f in SHARED_FILES]
    hashes = {p.name: file_hash(p) for p in files}
    if verify:
        check_registry(hashes, spec_dir)

    tiers_raw = load_yaml(spec_dir / "risk_tiers.yaml")
    tiers = {k: RiskTier(**v) for k, v in tiers_raw["tiers"].items()}
    return Spec(
        candidate=load_yaml(candidate_file),
        tiers=tiers,
        governor=tiers_raw["governor"],
        max_order_notional_usd=float(tiers_raw["max_order_notional_usd"]),
        costs=load_yaml(spec_dir / "costs.yaml"),
        universe=load_yaml(spec_dir / "universe.yaml"),
        periods=load_yaml(spec_dir / "periods.yaml"),
        hashes=hashes,
    )


def check_registry(hashes: dict[str, str], spec_dir: Path = SPEC_DIR) -> None:
    registry_path = spec_dir / "REGISTRY.json"
    if not registry_path.exists():
        return  # Not yet frozen; `freeze_registry` writes it at Gate G0.
    registry = json.loads(registry_path.read_text())
    for name, digest in hashes.items():
        frozen = registry.get("files", {}).get(name)
        if frozen is None:
            raise SpecHashMismatch(f"{name} is not in the registry; freeze it first")
        if frozen != digest:
            raise SpecHashMismatch(
                f"{name} changed since it was frozen ({frozen[:12]} -> {digest[:12]}). "
                "Commit the change with a stated reason and re-run freeze_registry."
            )


def freeze_registry(spec_dir: Path = SPEC_DIR, reason: str = "") -> dict[str, Any]:
    """Record every spec file's hash. Call once at Gate G0 and after any approved change."""
    files = sorted(p for p in spec_dir.glob("*.yaml"))
    registry = {
        "reason": reason,
        "files": {p.name: file_hash(p) for p in files},
    }
    (spec_dir / "REGISTRY.json").write_text(json.dumps(registry, indent=2) + "\n")
    return registry
