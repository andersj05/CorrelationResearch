"""Reproduce the fixed initial research pass from the aligned local snapshot."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from btc_nasdaq.config import load_config, project_root
from btc_nasdaq.data import load_prices, returns_from_prices, sha256
from btc_nasdaq.diagnostics import (
    block_bootstrap,
    fixed_log_spread,
    ou_diagnostic,
    regime_summary,
    stationarity,
)
from btc_nasdaq.models import estimate_betas, hedge_scorecard
from btc_nasdaq.strategy import backtest, performance, residual_signal, target_weights


def research_context(root: Path | None = None) -> dict:
    root = root or project_root()
    cfg = load_config(root)
    prices = load_prices(root)
    returns = returns_from_prices(prices).iloc[1:]
    if returns.isna().any().any():
        raise ValueError("Aligned sample has missing returns.")
    betas, kalman = estimate_betas(returns, cfg["model"])
    beta = betas[cfg["strategy"]["model"]].clip(-cfg["model"]["beta_limit"], cfg["model"]["beta_limit"])
    signal = residual_signal(returns, beta, cfg["strategy"]["lookback"])
    return dict(root=root, cfg=cfg, prices=prices, returns=returns, betas=betas,
                kalman=kalman, beta=beta, signal=signal)


def run_period(context: dict, start: str, end: str | None = None,
               strategy: dict | None = None, unhedged: bool = False) -> pd.DataFrame:
    cfg = strategy or context["cfg"]["strategy"]
    returns = context["returns"].loc[start:end]
    signal = residual_signal(context["returns"], context["beta"], cfg["lookback"])
    targets = target_weights(signal, context["beta"], cfg,
                             context["cfg"]["model"]["beta_limit"], start=start).loc[returns.index]
    if unhedged:
        targets["qqq"] = 0.0
    return backtest(returns, targets, context["prices"].elapsed_days.loc[returns.index], cfg)


def run_research(root: Path | None = None) -> dict:
    c = research_context(root)
    root, cfg = c["root"], c["cfg"]
    tables = root / "reports/tables"
    tables.mkdir(parents=True, exist_ok=True)
    regimes = regime_summary(c["returns"])
    regimes.to_csv(tables / "annual_regimes.csv")
    validation = cfg["validation"]
    score = hedge_scorecard(c["returns"], c["betas"], start=validation["holdout_start"])
    score.to_csv(tables / "holdout_hedges.csv")
    hedge_scorecard(c["returns"], c["betas"], start=validation["holdout_start"], lag=2).to_csv(
        tables / "holdout_hedges_delayed.csv")
    first_signal = str(c["signal"].z.first_valid_index().date())
    periods = {"train": (first_signal, validation["train_end"]),
               "validation": (str((pd.Timestamp(validation["train_end"]) + pd.Timedelta(days=1)).date()),
                              validation["validation_end"]),
               "holdout": (validation["holdout_start"], None)}
    performance_rows = {}
    for name, (start, end) in periods.items():
        result = run_period(c, start, end)
        performance_rows[name] = performance(result)
        if name == "holdout":
            holdout = result
    performance_rows["holdout_same_signal_unhedged"] = performance(
        run_period(c, validation["holdout_start"], unhedged=True))
    stats = pd.DataFrame(performance_rows).T
    stats.to_csv(tables / "strategy_performance.csv")
    cost_rows = []
    for btc_cost in [0., 5., 10., 25., 50.]:
        assumption = {**cfg["strategy"], "btc_cost_bps": btc_cost, "qqq_cost_bps": btc_cost / 5}
        stat = performance(run_period(c, validation["holdout_start"], strategy=assumption))
        cost_rows.append({"btc_bps": btc_cost, "qqq_bps": btc_cost / 5, **stat.to_dict()})
    pd.DataFrame(cost_rows).to_csv(tables / "cost_sensitivity.csv", index=False)
    sensitivity = []
    for lookback in [10, 20, 40]:
        for entry in [1., 1.5, 2.]:
            assumption = {**cfg["strategy"], "lookback": lookback, "entry_z": entry}
            stat = performance(run_period(c, *periods["validation"], strategy=assumption))
            sensitivity.append({"lookback": lookback, "entry_z": entry, **stat.to_dict()})
    pd.DataFrame(sensitivity).to_csv(tables / "validation_sensitivity.csv", index=False)
    spread, cointegration = fixed_log_spread(c["prices"], validation["train_end"])
    stationary = pd.DataFrame({name: stationarity(spread.loc[start:end])
                               for name, (start, end) in periods.items()}).T
    stationary.to_csv(tables / "fixed_spread_stationarity.csv")
    def sharpe(x):
        return np.mean(x) / np.std(x, ddof=1) * np.sqrt(252) if np.std(x) > 0 else np.nan
    draws = block_bootstrap(holdout.net_return.to_numpy(), sharpe,
                           samples=validation["bootstrap_samples"], block=validation["bootstrap_block"],
                           seed=validation["seed"])
    summary = {
        "sample_first": str(c["prices"].index.min().date()),
        "sample_last": str(c["prices"].index.max().date()), "sessions": len(c["prices"]),
        "pre_2020_correlation": c["returns"].loc[:"2019"].corr().loc["btc", "qqq"],
        "post_2020_correlation": c["returns"].loc["2020":].corr().loc["btc", "qqq"],
        "latest_beta": c["beta"].iloc[-1], "baseline_model": cfg["strategy"]["model"],
        "holdout_baseline_hedge": score.loc[cfg["strategy"]["model"]].to_dict(),
        "cointegration": cointegration,
        "train_ou": ou_diagnostic(spread.loc[:validation["train_end"]]),
        "holdout_strategy": stats.loc["holdout"].to_dict(),
        "holdout_sharpe_95pct_block_interval": np.nanquantile(draws, [.025, .975]).tolist(),
        "config_sha256": sha256(root / "configs/research.toml"),
        "data_sha256": sha256(root / "data/processed/aligned_prices.parquet"),
        "status": "Initial retrospective research; holdout examined once. New changes need a fresh test.",
    }
    (tables / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    return summary
