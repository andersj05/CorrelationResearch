"""Statistical diagnostics; distinguish return predictability from level stationarity."""

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint, kpss


def regime_summary(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, sample in returns.dropna().groupby(returns.dropna().index.year):
        rows.append({"year": year, "n": len(sample),
                     "correlation": sample.btc.corr(sample.qqq),
                     "spearman": sample.btc.corr(sample.qqq, method="spearman"),
                     "beta": sample.btc.cov(sample.qqq) / sample.qqq.var(),
                     "btc_vol": sample.btc.std() * np.sqrt(252),
                     "qqq_vol": sample.qqq.std() * np.sqrt(252)})
    return pd.DataFrame(rows).set_index("year")


def block_bootstrap(values: np.ndarray, statistic, samples: int = 1000,
                    block: int = 10, seed: int = 42) -> np.ndarray:
    """Circular moving blocks; keeps columns paired and short-run dependence intact."""
    values = np.asarray(values)
    if len(values) < block or block < 1 or samples < 1:
        raise ValueError("Need at least one complete bootstrap block and positive samples.")
    rng = np.random.default_rng(seed)
    blocks_needed = int(np.ceil(len(values) / block))
    draws = []
    for _ in range(samples):
        starts = rng.integers(0, len(values), blocks_needed)
        indices = ((starts[:, None] + np.arange(block)) % len(values)).ravel()[:len(values)]
        draws.append(statistic(values[indices]))
    return np.asarray(draws)


def stationarity(series: pd.Series) -> dict:
    values = series.dropna()
    if len(values) < 30 or values.std() < 1e-12:
        return {"n": len(values), "adf_p": np.nan, "kpss_p": np.nan,
                "kpss_boundary": "insufficient/constant data"}
    adf = adfuller(values, regression="c", autolag="AIC")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        kp = kpss(values, regression="c", nlags="auto")
    return {"n": len(values), "adf_p": adf[1], "kpss_p": kp[1],
            "kpss_boundary": "; ".join(str(w.message).split("\n")[0] for w in caught)}


def fixed_log_spread(prices: pd.DataFrame, train_end: str) -> tuple[pd.Series, dict]:
    log = np.log(prices[["btc", "qqq"]]).dropna()
    train = log.loc[:train_end]
    fit = sm.OLS(train.btc, sm.add_constant(train.qqq)).fit()
    spread = log.btc - fit.params["const"] - fit.params["qqq"] * log.qqq
    test = coint(train.btc, train.qqq, trend="c", autolag="aic")
    return spread.rename("fixed_log_spread"), {
        "train_n": len(train), "intercept": fit.params["const"],
        "log_price_coefficient": fit.params["qqq"], "engle_granger_p": test[1],
        "note": "Log-price slope is NOT the minimum-variance return hedge beta.",
    }


def ou_diagnostic(series: pd.Series) -> dict:
    """AR(1) approximation; half-life is meaningful only for stationary positive phi."""
    frame = pd.concat([series.rename("y"), series.shift(1).rename("lag")], axis=1).dropna()
    if len(frame) < 30:
        raise ValueError("At least 30 adjacent observations required.")
    fit = sm.OLS(frame.y, sm.add_constant(frame.lag)).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    phi = fit.params["lag"]
    interval = fit.conf_int().loc["lag"]
    return {"phi": phi, "phi_low": interval.iloc[0], "phi_high": interval.iloc[1],
            "half_life_sessions": -np.log(2) / np.log(phi) if 0 < phi < 1 else np.nan,
            "phi_ci_below_one": bool(interval.iloc[1] < 1),
            "note": "Conditional AR(1) diagnostic; not a trading recommendation."}


def predictive_regression(signal: pd.Series, future_returns: pd.Series) -> pd.Series:
    frame = pd.concat([signal.rename("signal"), future_returns.rename("future")], axis=1).dropna()
    fit = sm.OLS(frame.future, sm.add_constant(frame.signal)).fit(
        cov_type="HAC", cov_kwds={"maxlags": 10})
    return pd.Series({"n": len(frame), "coefficient": fit.params["signal"],
                      "hac_t": fit.tvalues["signal"], "hac_p": fit.pvalues["signal"],
                      "r_squared": fit.rsquared})
