"""Transparent residual-reversal hypothesis with causal weights and delayed fills."""

import numpy as np
import pandas as pd


def residual_signal(returns: pd.DataFrame, beta: pd.Series, lookback: int = 20
                    ) -> pd.DataFrame:
    if lookback < 2:
        raise ValueError("lookback must be at least 2.")
    # Realized one-step hedge forecast error, not an ex-post fitted residual.
    residual = returns.btc - beta.shift(1) * returns.qqq
    # Normalize by information predating the entire shock window.
    center = residual.ewm(halflife=63, min_periods=63, adjust=False).mean().shift(lookback)
    sigma = residual.ewm(halflife=63, min_periods=63, adjust=False).std().shift(lookback)
    shock = residual.rolling(lookback).sum() - lookback * center
    z = shock / (sigma * np.sqrt(lookback)).where(sigma > 1e-10)
    return pd.DataFrame({"residual": residual, "shock": shock, "z": z,
                         "annual_residual_vol": residual.ewm(
                             halflife=63, min_periods=63, adjust=False).std() * np.sqrt(252)})


def position_state(z: pd.Series, entry: float, exit_z: float, stop: float,
                   max_holding: int) -> pd.Series:
    if not 0 <= exit_z < entry < stop or max_holding < 1:
        raise ValueError("Require 0 <= exit < entry < stop and positive maximum holding.")
    side, age = 0, 0
    result = []
    for value in z:
        if not np.isfinite(value):
            side, age = 0, 0
        elif side:
            age += 1
            if side * value >= -exit_z or abs(value) >= stop or age >= max_holding:
                side, age = 0, 0
        elif entry <= abs(value) < stop:
            side, age = -int(np.sign(value)), 0
        result.append(side)
    return pd.Series(result, index=z.index, name="side", dtype=float)


def target_weights(signal: pd.DataFrame, beta: pd.Series, config: dict,
                   beta_limit: float = 4.0, start: str | None = None) -> pd.DataFrame:
    z = signal.z.copy()
    if start is not None:
        z.loc[z.index < pd.Timestamp(start)] = np.nan
    side = position_state(z, config["entry_z"], config["exit_z"], config["stop_z"],
                          config["max_holding"])
    bounded_beta = beta.clip(-beta_limit, beta_limit)
    scale = (config["target_vol"] / signal.annual_residual_vol).clip(upper=config["max_gross"])
    btc = side * scale
    qqq = -bounded_beta * btc
    weights = pd.DataFrame({"btc": btc, "qqq": qqq}).replace([np.inf, -np.inf], np.nan).fillna(0)
    gross = weights.abs().sum(axis=1)
    weights = weights.mul((config["max_gross"] / gross.replace(0, np.nan)).clip(upper=1).fillna(1), axis=0)
    return weights


def backtest(returns: pd.DataFrame, targets: pd.DataFrame, elapsed_days: pd.Series,
             config: dict, liquidate: bool = True) -> pd.DataFrame:
    """Daily portfolio accounting as a fraction of pre-trade NAV.

    target[t] is observed after t's close. With lag=2 it is held over t+1 -> t+2.
    Transaction costs include opening, closing, drift and hedge rebalancing.
    Cash earns zero; short carry applies to both legs and debit financing to net borrowing.
    """
    lag = config["execution_lag"]
    if not isinstance(lag, int) or lag < 1:
        raise ValueError("execution_lag must be a positive integer.")
    if not returns.index.equals(targets.index) or not returns.index.equals(elapsed_days.index):
        raise ValueError("Returns, targets and elapsed days must have identical indices.")
    if not np.isfinite(returns.to_numpy()).all() or not np.isfinite(targets.to_numpy()).all():
        raise ValueError("Missing/non-finite returns or weights; repair the data rather than filling.")
    if (returns <= -1).any().any() or (elapsed_days <= 0).any() or elapsed_days.isna().any():
        raise ValueError("Invalid simple returns or elapsed days.")
    rates = np.array([config["btc_cost_bps"], config["qqq_cost_bps"]]) / 10000
    if (rates < 0).any() or min(config["short_carry_annual"], config["financing_annual"]) < 0:
        raise ValueError("Costs cannot be negative.")
    holdings = targets[["btc", "qqq"]].shift(lag).fillna(0)
    drifted = np.zeros(2)
    rows = []
    for i, (date, r) in enumerate(returns[["btc", "qqq"]].iterrows()):
        w = holdings.loc[date].to_numpy()
        turnover_by_leg = np.abs(w - drifted)
        trade_cost = float(turnover_by_leg @ rates)
        day_fraction = elapsed_days.loc[date] / 365.25
        borrow = np.maximum(-w, 0).sum() * config["short_carry_annual"] * day_fraction
        financing = max(w.sum() - 1, 0) * config["financing_annual"] * day_fraction
        leg_pnl = w * r.to_numpy()
        gross_return = float(leg_pnl.sum())
        closing_turnover = 0.0
        if liquidate and i == len(returns) - 1:
            end_notionals = np.abs(w * (1 + r.to_numpy()))
            trade_cost += float(end_notionals @ rates)
            closing_turnover = float(end_notionals.sum())
        net_return = gross_return - trade_cost - borrow - financing
        if net_return <= -1:
            raise ValueError(f"Portfolio insolvent on {date}; leverage assumptions invalid.")
        drifted = w * (1 + r.to_numpy()) / (1 + net_return)
        rows.append({"btc_weight": w[0], "qqq_weight": w[1], "gross_exposure": abs(w).sum(),
                     "btc_pnl": leg_pnl[0], "qqq_pnl": leg_pnl[1], "gross_return": gross_return,
                     "trade_cost": trade_cost, "carry": borrow + financing,
                     "turnover": turnover_by_leg.sum() + closing_turnover, "net_return": net_return})
    result = pd.DataFrame(rows, index=returns.index)
    result["equity"] = (1 + result.net_return).cumprod()
    result["drawdown"] = result.equity / result.equity.cummax().clip(lower=1) - 1
    return result


def performance(result: pd.DataFrame) -> pd.Series:
    net = result.net_return
    years = len(net) / 252
    vol = net.std() * np.sqrt(252)
    return pd.Series({"sessions": len(net), "total_return": (1 + net).prod() - 1,
                      "cagr": (1 + net).prod() ** (1 / years) - 1,
                      "annual_vol": vol, "sharpe_zero_cash": net.mean() * 252 / vol if vol else np.nan,
                      "max_drawdown": result.drawdown.min(),
                      "active_fraction": (result.gross_exposure > 0).mean(),
                      "annual_turnover": result.turnover.sum() / years,
                      "cost_drag_sum": (result.trade_cost + result.carry).sum()})
