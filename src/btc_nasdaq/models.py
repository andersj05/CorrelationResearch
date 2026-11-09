"""Causal return-beta estimates. Values at t use observations only through t."""

import numpy as np
import pandas as pd
import statsmodels.api as sm


def kalman_regression(returns: pd.DataFrame, warmup: int = 252,
                      alpha_variance: float = 1e-8, beta_variance: float = 1e-4
                      ) -> pd.DataFrame:
    """Random-walk [alpha, beta], adaptive innovation variance, filtered (never smoothed).

    Q is in squared daily-return-intercept / squared beta per session. R is learned
    from past innovations only. Posterior bands are conditional model uncertainty.
    """
    state = np.array([0.0, 0.0])
    covariance = np.diag([0.001, 4.0])
    process = np.diag([alpha_variance, beta_variance])
    noise = 0.03**2
    rows = []
    seen = 0
    for y, x in returns[["btc", "qqq"]].itertuples(index=False, name=None):
        prior = covariance + process
        if np.isfinite([y, x]).all():
            design = np.array([1.0, x])
            innovation = y - design @ state
            innovation_var = design @ prior @ design + noise
            gain = prior @ design / innovation_var
            state = state + gain * innovation
            # Joseph form preserves positive semidefiniteness under rounding.
            residual_map = np.eye(2) - np.outer(gain, design)
            covariance = residual_map @ prior @ residual_map.T + np.outer(gain, gain) * noise
            noise = max(0.98 * noise + 0.02 * innovation**2, 1e-8)
            seen += 1
        else:
            covariance = prior
        rows.append([*state, np.sqrt(max(covariance[1, 1], 0))]
                    if seen >= warmup else [np.nan] * 3)
    return pd.DataFrame(rows, index=returns.index, columns=["alpha", "beta", "beta_se"])


def estimate_betas(returns: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    y, x = returns.btc, returns.qqq
    warmup = config["warmup"]
    betas = pd.DataFrame(index=returns.index)
    betas["expanding"] = y.expanding(warmup).cov(x) / x.expanding(warmup).var()
    for window in config["rolling_windows"]:
        betas[f"rolling_{window}"] = y.rolling(window).cov(x) / x.rolling(window).var()
    half = config["ewma_halflife"]
    ew = y.ewm(halflife=half, min_periods=warmup, adjust=False)
    betas[f"ewma_{half}"] = ew.cov(x) / x.ewm(
        halflife=half, min_periods=warmup, adjust=False).var()
    kalman = kalman_regression(returns, warmup, config["kalman_alpha_variance"],
                               config["kalman_beta_variance"])
    betas["kalman"] = kalman.beta
    return betas.replace([np.inf, -np.inf], np.nan), kalman


def hedge_scorecard(returns: pd.DataFrame, betas: pd.DataFrame,
                    start: str | None = None, end: str | None = None,
                    lag: int = 1) -> pd.DataFrame:
    """Compare identical dates. lag=1 is a forecast diagnostic, not executed P&L."""
    forecast = betas.shift(lag)
    valid = forecast.notna().all(axis=1) & returns.notna().all(axis=1)
    sample = returns.loc[valid].loc[start:end]
    forecast = forecast.loc[sample.index]
    if len(sample) < 20:
        raise ValueError("Too few common observations for hedge comparison.")
    rows = []
    for name in ["unhedged", *betas.columns]:
        beta = pd.Series(0.0, index=sample.index) if name == "unhedged" else forecast[name]
        residual = sample.btc - beta * sample.qqq
        fit = sm.OLS(residual, sm.add_constant(sample.qqq)).fit(
            cov_type="HAC", cov_kwds={"maxlags": 5})
        ci = fit.conf_int().loc["qqq"]
        rows.append({"model": name, "n": len(sample),
                     "annual_vol": residual.std() * np.sqrt(252),
                     "variance_reduction": 1 - residual.var() / sample.btc.var(),
                     "residual_beta": fit.params["qqq"],
                     "beta_ci_low": ci.iloc[0], "beta_ci_high": ci.iloc[1],
                     "residual_corr": residual.corr(sample.qqq),
                     "mean_beta_change": beta.diff().abs().mean(),
                     "tail_5pct_mean": residual[residual <= residual.quantile(.05)].mean()})
    return pd.DataFrame(rows).set_index("model")
