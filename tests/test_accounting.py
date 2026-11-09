import numpy as np
import pandas as pd
import pytest

from btc_nasdaq.config import load_config
from btc_nasdaq.strategy import backtest


def setup_case(n=5):
    index = pd.bdate_range("2024-01-01", periods=n)
    returns = pd.DataFrame(0., index=index, columns=["btc", "qqq"])
    targets = returns.copy()
    days = pd.Series(1., index=index)
    cfg = {**load_config()["strategy"], "btc_cost_bps": 0., "qqq_cost_bps": 0.,
           "short_carry_annual": 0., "financing_annual": 0.}
    return returns, targets, days, cfg


def test_lag_prevents_same_close_and_next_session_profit():
    returns, targets, days, cfg = setup_case()
    targets.loc[:, "btc"] = 1.
    returns.iloc[0:3, 0] = [.1, .2, .3]
    result = backtest(returns, targets, days, cfg)
    assert result.net_return.tolist() == [0., 0., .3, 0., 0.]


def test_entry_and_terminal_liquidation_costs():
    returns, targets, days, cfg = setup_case(3)
    targets.loc[:, "btc"] = 1.
    cfg["btc_cost_bps"] = 10
    result = backtest(returns, targets, days, cfg)
    assert result.trade_cost.sum() == pytest.approx(.002)
    assert result.turnover.sum() == pytest.approx(2.)


def test_drift_rebalancing_is_charged():
    returns, targets, days, cfg = setup_case()
    targets.loc[:, "btc"] = .5
    returns.iloc[2, 0] = .1
    cfg["btc_cost_bps"] = 10
    result = backtest(returns, targets, days, cfg, liquidate=False)
    expected_drift = .5 * 1.1 / (1 + .05 - .0005)
    assert result.trade_cost.iloc[3] == pytest.approx(abs(.5 - expected_drift) * .001)


def test_carry_uses_calendar_days_and_each_short_leg():
    returns, targets, days, cfg = setup_case(3)
    targets.loc[:, "btc"] = -.5
    targets.loc[:, "qqq"] = -.5
    days.iloc[-1] = 3
    cfg["short_carry_annual"] = .1
    result = backtest(returns, targets, days, cfg)
    assert result.carry.sum() == pytest.approx(.1 * 3 / 365.25)


def test_leg_attribution_and_compounding():
    returns, targets, days, cfg = setup_case()
    targets.loc[:, "btc"], targets.loc[:, "qqq"] = .5, -.2
    returns.loc[:, "btc"], returns.loc[:, "qqq"] = .04, .02
    result = backtest(returns, targets, days, cfg)
    np.testing.assert_allclose(result.gross_return, result.btc_pnl + result.qqq_pnl)
    assert result.equity.iloc[-1] == pytest.approx((1 + .016)**3)


def test_drawdown_includes_initial_capital():
    returns, targets, days, cfg = setup_case(3)
    targets.loc[:, "btc"] = 1.
    returns.iloc[-1, 0] = -.1
    assert backtest(returns, targets, days, cfg).drawdown.iloc[-1] == pytest.approx(-.1)


@pytest.mark.parametrize("problem", ["missing_return", "misaligned", "invalid_days", "bad_lag"])
def test_invalid_inputs_rejected(problem):
    returns, targets, days, cfg = setup_case()
    if problem == "missing_return":
        returns.iloc[-1, 0] = np.nan
    elif problem == "misaligned":
        targets = targets.iloc[:-1]
    elif problem == "invalid_days":
        days.iloc[0] = 0
    elif problem == "bad_lag":
        cfg["execution_lag"] = 0
    with pytest.raises(ValueError):
        backtest(returns, targets, days, cfg)
