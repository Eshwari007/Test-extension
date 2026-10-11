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

## Reference exchange (Coinbase)

Daily bars from 2017-01-01 for BTC and all 30 coins (`data/ref`). Rebrands stitched and documented:
MATIC→POL (1:1), RNDR→RENDER (1:1), **MKR→SKY (1:24000 — the first stitch assumed 1:1 and was caught by
the seam check; prices now divided and volumes multiplied by the ratio)**. Quality: **G1 PASS on all 31**,
no gaps, no zero-volume bars. Extreme moves (XRP, ADA, LTC, BCH, UNI, GRT, FIL, POL, SKY, SHIB) are
real 2017–2021 events, consistent across both sources.

## Liquidity threshold — Phase 1 decision

Sensitivity of the eligible universe to the 30-day median dollar-volume threshold (Coinbase volume,
90-day history rule, Alpaca listing required):

| Threshold | Median coins/month | Min | Months with <3 | Coins in training | Coins in hold-out | Memecoins ever |
|---|---|---|---|---|---|---|
| $2M | 11 | 4 | 0 | 14 | 23 | 4 |
| **$5M** | **8** | **3** | **0** | **14** | **20** | **3** |
| $10M | 5 | 0 | 3 | 13 | 18 | 3 |
| $20M (proposed) | 4 | 0 | 20 | 9 | 15 | 3 |

**Decision (2026-10-11): $5M.** At $20M the universe was smaller than the tiers' position slots in 20 of
69 months and empty in H2 2023. Recorded in `universe.yaml` and re-frozen with the reason.

Final eligibility (`data/eligibility_{position,swing,intraday}.csv`), 2021-01 → 2026-10:

- **Position (365d):** median 7 coins/month (3–15). Training: AAVE AVAX BCH DOGE DOT GRT LINK LTC SHIB SOL SUSHI UNI YFI.
  Hold-out adds ADA CRV ONDO PEPE XRP XTZ.
- **Swing / Intraday (90d):** median 8 (3–15). Training adds BAT; hold-out adds HYPE TRUMP.
- **Never eligible at $5M:** BONK FIL LDO POL RENDER SKY WIF (+ BAT HYPE TRUMP for the position rule).

## Hourly bars (C1)

Alpaca 1h bars from 2021-01-01 (up to 50,616 per coin). **G1: 29 of 31 PASS.** Excluded for the 1h
timeframe, reason logged in `listings.yaml`: **YFI** (1.89% missing) and **BAT** (1.14%). Alpaca emits no
bar in an hour with no trades, so the misses are thin-book hours; both coins are marginal at $5M anyway.

Caveat for C1: zero-volume hours are common even on passing coins (DOGE 18%, SUSHI 53%, XTZ 76% of
hours). C1's entry needs *1h volume > 2× its 7-day average*; on Alpaca-venue volume that signal is
noisy. Phase 3 should run C1 with reference-exchange hourly volume as a pre-registered data variant
(Coinbase 1h fetch is ~5,000 calls; not pulled yet).

## Gate G1: PASS

Every coin passes or is excluded with the reason logged. Open items carried into Phase 3:
Alpaca minimum order sizes (from the assets snapshot) and the live fee tier are recorded but not yet
checked against the $10k starting capital.
