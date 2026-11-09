# Research design

## The decision

Determine whether a Nasdaq hedge reduces unwanted Bitcoin market exposure and whether a separate BTC-specific reversal signal earns returns after costs. These are distinct tests. The initial output is research evidence, not an instruction to trade.

The intended alpha is reversal of a Bitcoin-specific shock. QQQ return beta is the unwanted exposure. A one-factor hedge retains crypto jumps, rates/dollar and nonlinear exposure, liquidity risk, financing, venue basis and model error. Smaller exposure or no trade remains a valid outcome.

## Observation clock and data

The first snapshot requests January 1, 2018 through November 7, 2026 (exclusive). It contains 2,225 Nasdaq sessions from January 2, 2018 through November 6, 2026. QQQ daily closes come from Yahoo Finance through yfinance. BTC-USD hourly candles come from Coinbase Exchange's public endpoint.

`pandas_market_calendars` supplies the Nasdaq schedule. For a session closing at UTC time T, BTC is the close of the hourly candle starting at T minus one hour. This is the last traded price in that hour, not the open or close of the future candle starting at T. QQQ and BTC returns run between consecutive scheduled closing marks. Weekend and holiday gaps belong to both legs' intervals. UTC time changes with DST; early closes are preserved.

The aligned panel retains every scheduled session. Missing prices, duplicate timestamps, nonpositive prices or non-finite observations cause a failure rather than a fill. The hourly archive can have gaps outside selected session marks. `alignment_audit.parquet` checks the selected marks, not completeness of every hour. Provider failures never switch to synthetic data.

QQQ adjusted close supplies total returns; raw close supplies share quantities. This is a present-day adjusted-history snapshot, not a point-in-time database of historical provider revisions. BTC uses one USD spot venue. QQQ tracks the Nasdaq-100; it is not the Nasdaq Composite or an NQ contract. Total-return versus price-return and ETF versus futures basis are explicit limitations.

Raw chunks are resumable and cached. `data/raw/manifest.json` records requested and realized coverage, source URLs and SHA-256 hashes. The pipeline timestamp records the run; cached files are not claimed to have been freshly retrieved. Delete the specific cache deliberately to refresh. `load_prices` rejects a changed data configuration or a processed-file hash mismatch. Notebook setup also rejects summary tables from a different data/configuration snapshot.

## Return-beta models

For simple returns y = BTC and x = QQQ, the minimum-variance linear hedge is beta = Cov(y,x) / Var(x) = corr(y,x) × vol(y)/vol(x). Beta is QQQ dollar exposure per BTC dollar, not QQQ shares per BTC unit. Centered moments allow an intercept. Alpha is not booked as an independently tradable P&L component.

Candidates are expanding OLS, 63/126/252-session rolling OLS, EWMA with 63-session half-life, and Kalman regression. The shared comparison uses dates when every candidate is available. Rolling estimates can be available before the 252-session EWMA/expanding/Kalman warm-up; comparisons use their intersection.

The Kalman state is [daily return intercept, return beta], with a random-walk transition. Q is diagonal with variances 1e-8 and 1e-4 per session. Initial state is zero and initial state covariance is diag(0.001, 4). Observation variance starts at 0.03² and updates from squared past innovations at a 0.02 rate. The filter uses the prior noise estimate for each measurement and then updates it for the next measurement. There is no backward smoother or whole-sample noise calibration. Bands are conditional on this model and should not be interpreted as full uncertainty about structural changes.

Estimates at t contain information through t. Passive hedge scorecards compare y_t − beta_(t−1) x_t and, separately, y_t − beta_(t−2) x_t. The former is a one-step forecast diagnostic, not the implemented backtest. Metrics include variance reduction, realized residual beta with HAC confidence intervals, residual correlation, downside tail mean and beta instability. These passive metrics exclude financing and costs. Portfolio simulation includes them.

## Mean reversion is a separate hypothesis

First fit a constant log-price relation on training data and freeze its coefficients. The training Engle–Granger test uses the appropriate residual-based critical values. ADF on an estimated training spread is descriptive only, with a nonstandard null distribution; later fixed-coefficient ADF and KPSS results remain sensitive to breaks and power. ADF's null is a unit root; KPSS's null is level stationarity. Boundary KPSS p-values are reported with a note.

An AR(1) approximation supplies phi and a conditional half-life only when 0 < phi < 1. A finite estimate alone does not justify an OU trade. HAC intervals for phi are not unit-root critical values. The fixed log-price slope and the minimum-variance return beta answer different questions and are not interchangeable.

The separately tested trading signal uses observable residual returns e_t = y_t − beta_(t−1) x_t. Its numerator is the last 20-session sum minus 20 times a past EWMA residual mean. The denominator is sqrt(20) times a past EWMA residual standard deviation. The normalization estimates are shifted by the full 20-session window, so they end before the shock being normalized. This scale is approximate under serial dependence and non-Gaussian tails.

A rolling shock mechanically forgets old observations. Its apparent reversion is not proof that prices reverse. Predictive diagnostics examine future returns after the execution delay, using beta known at the decision. Labels are shifted inside each chronological segment to avoid crossing train/validation boundaries. These diagnostics are separate from the costed strategy simulation.

## Strategy and execution

The baseline was fixed before the first result inspection: EWMA-63 beta; 20-session shock; entry |z| ≥ 1.5 but < 3.5; fade the sign; exit when z reverts toward/past zero (exit band 0.25), |z| reaches 3.5, or 10 decision sessions elapse. Signals are evaluated after each close. Exits and entries have the same delay. A stop on a signal is not a guaranteed loss cap.

At t, target BTC weight is side × 10% / estimated annual residual volatility. QQQ weight is −beta_t × BTC weight. Beta is bounded to ±4 for trading and gross exposure is capped at 1.5×. Weights remain constant only within each modeled close-to-close holding interval, and targets are recomputed daily. Volatility targeting is approximate, not a guaranteed realized risk level.

| Time | Information and action |
| --- | --- |
| After close t | Observe completed returns; update beta, z, and target weights |
| Close t+1 | Execute the queued target using the modeled closing marks |
| t+1 to t+2 | Earn the first holding interval return |
| Row t+2 | Record P&L and opening/rebalance costs for that interval |

The two-row shift includes the ordinary one-row return alignment plus a complete extra session for execution. A one-row setting is available for research comparisons but assumes a fill at the same close whose data was just observed and is optimistic. The shipped baseline uses two.

Daily gross P&L is w_B r_B + w_Q r_Q, as a fraction of pre-trade NAV. Pre-rebalance holdings are drifted from the prior period using each leg's return and the portfolio's previous net return. Trading costs apply to absolute changes from those drifted holdings. Opening, closing, sign reversals, beta/volatility rebalancing and terminal liquidation are charged. NAV compounds net returns; drawdown includes the initial NAV of one.

Baseline one-way costs are 10 bp on BTC and 2 bp on QQQ. Both short legs incur 5% annualized carry using actual elapsed calendar days / 365.25. Net debit cash above one NAV incurs 5% financing; idle cash and short proceeds earn zero. QQQ distributions are included in total returns, avoiding a second dividend debit. Short-collateral restrictions, venue-specific perpetual funding, futures margin/roll, rebates, taxes and liquidity capacity are not modeled. Gross/cash/margin constraints must be replaced with actual broker and venue rules before an implementation claim.

## Validation and interpretation

- Training ends December 31, 2021; validation covers 2022–2023; holdout starts January 1, 2024.
- Models update sequentially; there is no future-data parameter fit. Strategy performance begins only after its signal warm-up. Every segment starts flat and liquidates at its end.
- The validation grid covers lookback {10,20,40} and entry threshold {1,1.5,2}; it is a sensitivity diagnostic, not a holdout-optimized winner selection.
- The baseline holdout is inspected once in this pass. It is retrospective evidence, not a pristine prospective test. Changing the rule after inspection requires new evaluation data.
- Uncertainty uses paired circular blocks of 10 sessions with deterministic random seeds. Bootstrap intervals are conditional on the observed sample and do not cover every regime or selection effect.
- Volatility, Sharpe, CAGR and turnover annualize at 252 sessions. Carry uses calendar days. Sharpe is relative to zero cash yield, not an observed risk-free rate.
- The same-signal unhedged comparator retains the BTC leg and removes QQQ, so gross/risk differs. It isolates the hedge's contribution, not equal-risk portfolio superiority.

## Regression checks

Tests verify market-close timing including DST and early closes, missing-data propagation, recovery of known synthetic betas, invariance of historical estimates/signals to altered future data, position caps, holding/exit rules, dollar-to-unit conversion, execution delay, drift turnover, two-leg attribution, liquidation, weekend carry, compounding and invalid-input failures. Synthetic data appears only in tests, never in the research results.
