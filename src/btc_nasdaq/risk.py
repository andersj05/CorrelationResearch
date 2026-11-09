"""Dollar-delta translation and explicitly hypothetical hedge-failure scenarios."""

import numpy as np
import pandas as pd


def hedge_units(btc_units: float, btc_price: float, hedge_price: float, beta: float,
                multiplier: float = 1.0) -> dict:
    if not np.isfinite([btc_units, btc_price, hedge_price, beta, multiplier]).all():
        raise ValueError("Sizing inputs must be finite.")
    if min(btc_price, hedge_price, multiplier) <= 0:
        raise ValueError("Prices and multiplier must be positive.")
    btc_notional = btc_units * btc_price
    hedge_notional = -beta * btc_notional
    units = hedge_notional / (hedge_price * multiplier)
    rounded = float(np.rint(units))
    return {"btc_notional": btc_notional, "hedge_notional": hedge_notional,
            "hedge_units": units, "nearest_whole_units": rounded,
            "rounding_residual_beta_dollars": beta * btc_notional + rounded * hedge_price * multiplier,
            "gross_notional": abs(btc_notional) + abs(hedge_notional),
            "net_notional": btc_notional + hedge_notional}


def stress_scenarios(beta: float) -> pd.DataFrame:
    """P&L per $1 BTC long, plus hedge. Scenarios are assumptions, not forecasts."""
    frame = pd.DataFrame([
        ("BTC-specific recovery", .10, .00),
        ("Broad risk selloff", -.15, -.08),
        ("Crypto-only crash", -.25, .00),
        ("QQQ squeeze / BTC flat", .00, .10),
        ("Correlation flips", -.15, .05),
        ("Weekend BTC gap / QQQ stale", -.12, .00),
    ], columns=["scenario", "btc_return", "qqq_return"]).set_index("scenario")
    frame["unhedged"] = frame.btc_return
    frame["half_size_unhedged"] = .5 * frame.btc_return
    frame["hedged"] = frame.btc_return - beta * frame.qqq_return
    return frame
