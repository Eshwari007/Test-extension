# Speculative Crypto Strategy — research engine

Python implementation of the *Speculative Crypto Strategy: Project Plan* (Oct 2026).
Three pre-registered candidates (C1 intraday, C2 swing, C3 position) are tested on
Alpaca's speculative coins under an identical risk overlay, and at most one is
promoted to live trading, only if it passes every gate. The default outcome is
"don't trade".

This folder is self-contained and independent of the browser extension in the rest
of the repository.

## What is built (Phases 0 and 2)

| Module | File | Responsibility |
|---|---|---|
| config | `core/config.py` | Loads the frozen YAML specs; refuses to run if a spec hash differs from `specs/REGISTRY.json` |
| data | `core/data.py` | Alpaca / Coinbase fetchers (urllib), Parquet/CSV store, Gate G1 quality checks, rebrand stitching, point-in-time eligibility table, synthetic bars |
| features | `core/features.py` | SMA, EMA, ATR (Wilder), ADX, MACD, Donchian, RSI, realized vol, momentum score — pure, causal functions |
| signals | `core/signals.py` | `C1Intraday`, `C2Swing` (exit variants V1/V2/V3), `C3Position`, and the `RandomEntry` benchmark wrapper. Output intents, never orders |
| risk | `core/risk.py` | Volatility sizing, exposure cap, position and memecoin limits, drawdown governor (halve / block / flatten / kill) |
| portfolio | `core/portfolio.py` | Positions, cash, equity curve, peak equity, round-trip trade records |
| execution | `core/execution.py` | Intents → orders; client-side stop manager (Alpaca crypto has no OCO); idempotent `client_order_id`; decision log |
| broker | `core/broker.py` | One interface, three adapters: `SimBroker` (fill/cost model), `AlpacaBroker(paper=True)`, `AlpacaBroker(paper=False)` |
| backtest | `core/backtest.py` | Event-driven loop: fills at next open → stops vs. low → mark → governor → manage → entries |
| validation | `core/validation.py` | Walk-forward, ±25 % sensitivity, Monte Carlo, random-entry benchmark, deflated Sharpe, Kelly, hard gates, weighted ranking |
| reporting | `core/reporting.py` | Every metric in the plan; append-only run log that counts trials for the deflated Sharpe |
| cli | `cli.py` | `freeze`, `fetch`, `quality`, `backtest`, `validate` |

Not built yet: `ops` (scheduler, websocket feed, heartbeat, reconciliation, alerts) — that is Phase 5 work and
should be written only after a candidate passes Gate G4.

## Frozen specs (Gate G0)

`specs/*.yaml` hold every parameter from the plan, untuned:

- `c1_intraday.yaml`, `c2_swing.yaml`, `c3_position.yaml` — hypothesis, regime filter, entry, stop, exits
- `risk_tiers.yaml` — T1–T4 and the governor steps (33 % / 53 % / 80 % / 100 % of L)
- `costs.yaml` — 0.15 % maker / 0.25 % taker, slippage floor, memecoin/mid-cap extras, stress ×2
- `universe.yaml` — 30 coins by tier, rebrands, eligibility rules
- `periods.yaml` — training through 2023-12-31, hold-out 2024-01-01…2026-06-30, statistical floors

Freeze them once, in a dated commit:

```bash
python -m strategy.cli freeze --reason "Gate G0: pre-registration"
```

After that, every backtest verifies the hashes and refuses to run on an edited spec until
`freeze` is re-run (which must itself be a commit stating the reason).

## Running

```bash
pip install -r strategy/requirements.txt

# Engine checks on synthetic bars (no network needed)
python -m strategy.cli backtest --candidate C2 --variant V3 --tier T2 --synthetic --no-verify
python -m strategy.cli validate --candidate C2 --variant V3 --tier T2 --synthetic --no-verify --mc-runs 500 --random-runs 50

# Phase 1: real data
python -m strategy.cli fetch --timeframe 1d --start 2021-01-01                       # Alpaca, the execution venue (default)
python -m strategy.cli fetch --timeframe 1h --start 2022-01-01                       # keys: APCA_* env vars, or a cloud network secret
python -m strategy.cli fetch --source coinbase --timeframe 1d --start 2019-01-01     # optional: reference exchange for pre-Alpaca history
python -m strategy.cli quality --timeframe 1d

# Phase 3: in-sample only
python -m strategy.cli backtest --candidate C2 --variant V1 --tier T2 --end 2023-12-31

# Phase 4: the hold-out is touched ONCE per candidate
python -m strategy.cli validate --candidate C2 --variant V3 --tier T2
```

Synthetic bars are for engine checks only. Nothing run on them counts as evidence.

## Tests (Gate G2)

```bash
python -m unittest discover -s strategy/tests -t . -v     # or: pytest strategy/tests
```

- `test_features.py` — each indicator against hand values (Wilder ATR seed/recursion, EMA recursion, Donchian shift, RSI extremes)
- `test_lookahead.py` — truncate at t, recompute, assert every feature at t is unchanged, for all three candidates; daily→hourly regime mapping waits for the daily close
- `test_costs.py` — taker/maker fees, slippage floor and extras, measured spread, stress multiplier, gap-through stops, limit trade-through, idempotent order ids
- `test_risk.py` — sizing, exposure cap with reserved notional, position and memecoin limits, every governor step at the exact threshold, tier table matches the plan
- `test_engine.py` — golden trades hand-calculated to the cent (entry, chandelier stop, gap-through, V1 ladder, T1 sizing), determinism, cash reconciles with trade P&L for C1/C2/C3, governor kill
- `test_validation.py` — Monte Carlo, deflated Sharpe, Kelly, hard gates (⅔-of-tier drawdown, min trades, stress, concentration), ranking, walk-forward

The plan asks for 20 golden trades; five are included. Add the rest from a spreadsheet as Phase 2 proceeds.

## Modelling decisions worth knowing

- **Fills.** Signals use closed bars; orders fill at the next bar's open. Stops fill at the worse of the stop and the open.
- **C1 execution.** The engine runs C1 on its 1h signal bars and fills at the next 1h open. Filling on 15m bars needs a second bar series in the loop and is left for Phase 2 if the 1h result justifies it.
- **C3 sizing.** C3 carries no stop, so positions are sized to `exposure_cap / hold_top` of equity instead of ATR risk. C3 exits all positions on regime-off; C1/C2 rely on their stops.
- **Regime on intraday bars.** The BTC daily close > SMA(200) flag is applied to hourly bars only from the next day's 00:00 UTC (`daily_to_signal_tf`), so an hourly bar never sees the day it belongs to.
- **Monte Carlo** resamples per-trade returns on equity (net P&L ÷ equity at entry).
- **Random-entry benchmark** reuses the candidate's exits, sizing and regime filter and calibrates its entry probability to the real trade count.
- **Trial counting.** Every `backtest`/`validate` call appends to `strategy/runs/run_log.jsonl`; `validate` uses that count for the deflated Sharpe.

## Open decisions (from the plan, still yours)

- Starting capital for the live pilot (`--cash`, default 10 000).
- Reference exchange for pre-Alpaca history: Coinbase is wired (`fetch --source coinbase`); Kraken/Binance are a small addition in `core/data.py`. Alpaca is the default and the execution venue.
- Liquidity threshold (`universe.yaml: min_median_dollar_volume_30d`, proposed 20 M).
- Hosting and alerting for the live bot (Phase 5).

This is research and engineering tooling, not financial advice.
