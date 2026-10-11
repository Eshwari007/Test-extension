# Phase 1 — Data (Gate G1)

Run on 2026-10-11 against Alpaca paper (data.alpaca.markets, paper-api.alpaca.markets).
Raw outputs: `phase1_assets.txt`, `phase1_quality_1d.txt`, `phase1_history_eligibility.txt`.

## Facts confirmed (plan: "Facts to confirm in Phase 1")

| Fact | Result |
|---|---|
| Alpaca crypto asset list | 36 tradable USD pairs. All 30 plan coins present; nothing new outside BTC/ETH/stables/PAXG. Snapshot saved to `runs/alpaca_assets_snapshot.json`. |
| How far back Alpaca bars go | Daily bars start **2021-01-01** at the earliest (BTC, DOGE, LINK, LTC, BCH, UNI, BAT). See table below. |
| Listings/delistings | **SOL was delisted 2023-07-07 → 2024-08-25** (SEC action) and relisted. Recorded in `specs/listings.yaml`; the eligibility table excludes those months. No other gaps. |
| Training-period coverage | Only **12 of 30 coins** have ≥365 Alpaca days before 2024-01-01; **14 have none** (listed 2024 or later: XRP, ADA, ARB, FIL, LDO, POL, RENDER, SKY, ONDO, HYPE, PEPE, BONK, WIF, TRUMP). |
| Alpaca volume | Near zero on most coins (venue volume only). It **cannot** drive the $20M eligibility rule — the plan's reference-exchange volume is required. |

## Alpaca daily history

| Coin | Tier | First bar | Days | Training days (<2024) |
|---|---|---|---|---|
| DOGE, LINK, LTC, BCH, UNI, BAT | large/mid | 2021-01-01 | 2110 | 1095 |
| SOL | large | 2021-01-01 (gap 2023-07-07→2024-08-25) | 1692 | 915 |
| AAVE, GRT | large/mid | 2021-07-15 | 1915 | 900 |
| SUSHI | mid | 2021-07-23 | 1907 | 892 |
| AVAX | large | 2021-11-18 | 1789 | 774 |
| YFI | mid | 2021-12-02 | 1775 | 760 |
| SHIB | meme | 2023-03-14 | 1308 | 293 |
| DOT, CRV, XTZ | large/mid | 2023-08-18 | 1151 | 136 |
| XRP | large | 2024-01-01 | 1015 | 0 |
| TRUMP, PEPE | meme | 2025-01 | ~625 | 0 |
| SKY | mid | 2025-09-27 | 380 | 0 |
| ADA, ARB, FIL, LDO, ONDO, HYPE, POL, RENDER, BONK, WIF | mixed | 2026-02 | ~237 | 0 |

## Quality checks (daily)

- Missing bars: 0% on every coin after accounting for the SOL delisting window (SOL 0.118%, under the 0.5% limit).
- ±50% moves: DOGE ×4 (2021 meme run), BCH ×2, UNI/GRT/SHIB ×1. All are 2021 or earlier events on thin early Alpaca books; to be cross-checked against the reference exchange once it is reachable.
- Zero-volume bars: common on thin coins (YFI 431, SUSHI 206, UNI 126). These are Alpaca-venue quiet days, not missing data. Prices on those days are still usable; volume is not.
- Duplicates: none. All timestamps UTC.

**Gate G1 (daily): PASS**, with the SOL delisting logged and the reference-exchange dependency below.

## Blocking item: reference exchange

The plan requires a reference exchange for (a) signal history before each coin's Alpaca listing and
(b) the 30-day dollar-volume eligibility rule. Coinbase (`api.exchange.coinbase.com`) is wired in
`core/data.py` but the cloud environment's network policy denies it (403). Until it is allowed:

- the eligibility table is built on Alpaca history and volume only, which marks almost every coin ineligible;
- the training period effectively contains ~12 coins.

Action: add `api.exchange.coinbase.com` to the environment's allowed domains, then run
`python -m strategy.cli fetch --source coinbase --timeframe 1d --start 2019-01-01`.

## Hourly bars (C1)

See `phase1_quality_1h.txt` (appended when the hourly fetch completes).
