# Research log

## 2026-11-09 · Initial fixed baseline

**Question:** can a dynamic Nasdaq hedge isolate profitable BTC-specific mean reversion?

**Decisions made before inspecting performance:** QQQ proxy; synchronized Coinbase marks; EWMA-63 trading beta; 20-session residual shock; 1.5 entry / 0.25 exit / 3.5 stop; ten-session maximum holding; 10% target residual volatility; 1.5× gross cap; two-row execution lag; chronological 2021 / 2023 boundaries. See `configs/research.toml` for the exact versioned parameters.

**Observed sample:** 2,225 sessions, 2018-01-02 through 2026-11-06. All selected Nasdaq-close BTC marks and QQQ prices passed the alignment checks. No synthetic or forward-filled research observations were used.

**Findings:**

- BTC/QQQ aligned return correlation was approximately −0.001 before 2020 and 0.390 from 2020 onward. This supports a changed relationship, not a monotonic trend or causal explanation.
- In the 716-session holdout, EWMA-63 reduced passive residual variance by 16.3%. Realized residual beta was −0.020, with an approximate HAC 95% interval of [−0.237, 0.196]. Conditional risk remains.
- The training Engle–Granger p-value was 0.111. The fixed log-price relation did not meet a 5% cointegration threshold, despite an appealing fitted AR half-life. The OU fit is insufficient evidence.
- The fixed costed reversal rule returned −10.1% over the holdout, with zero-cash Sharpe −0.65 and maximum drawdown −12.3%. Its 10-session block-bootstrap Sharpe interval was approximately [−1.64, 0.39].
- The same BTC signal without QQQ returned −11.3%; this comparator has different gross and risk. A useful hedge did not rescue an unproven alpha signal.

**Decision:** keep the data/hedge toolkit; reject a profitability claim for this particular initial reversal rule. Do not tune on the now-inspected holdout and describe the result as a fresh test.

**Next research choice:** identify the intended holding horizon and economic reversal mechanism, then source appropriate point-in-time intraday/flow/funding data. A futures or perpetual implementation needs its own instrument, carry and execution model.

## Template for the next experiment

- Date / experiment ID:
- Economic hypothesis and falsifier:
- Change from baseline and why:
- Data and configuration hashes:
- Training / validation / untouched evaluation boundaries:
- Number of variants inspected:
- Metrics and costs specified before evaluation:
- Results, uncertainty and failure modes:
- Decision and next action:
