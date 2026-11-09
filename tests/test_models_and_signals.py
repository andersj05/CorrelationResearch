import numpy as np
import pandas as pd
import pytest

from btc_nasdaq.config import load_config
from btc_nasdaq.diagnostics import block_bootstrap, ou_diagnostic
from btc_nasdaq.models import estimate_betas, hedge_scorecard
from btc_nasdaq.risk import hedge_units
from btc_nasdaq.strategy import position_state, residual_signal, target_weights


@pytest.fixture
def sample():
    rng = np.random.default_rng(91)
    x = rng.normal(0, .01, 800)
    return pd.DataFrame({"qqq": x, "btc": .0003 + 1.7*x + rng.normal(0, .001, 800)},
                        index=pd.bdate_range("2018-01-01", periods=800))


def test_betas_recover_known_exposure(sample):
    betas, _ = estimate_betas(sample, load_config()["model"])
    assert np.allclose(betas.iloc[-1], 1.7, atol=.08)
    score = hedge_scorecard(sample, betas)
    assert score.loc["ewma_63", "variance_reduction"] > .98


def test_future_data_cannot_rewrite_estimates_or_signals(sample):
    cfg = load_config()
    original, original_k = estimate_betas(sample, cfg["model"])
    edited = sample.copy()
    edited.iloc[650:] *= -7
    revised, revised_k = estimate_betas(edited, cfg["model"])
    pd.testing.assert_frame_equal(original.iloc[:650], revised.iloc[:650])
    pd.testing.assert_frame_equal(original_k.iloc[:650], revised_k.iloc[:650])
    original_s = residual_signal(sample, original.ewma_63)
    revised_s = residual_signal(edited, revised.ewma_63)
    pd.testing.assert_frame_equal(original_s.iloc[:650], revised_s.iloc[:650])
    pd.testing.assert_frame_equal(
        target_weights(original_s, original.ewma_63, cfg["strategy"]).iloc[:650],
        target_weights(revised_s, revised.ewma_63, cfg["strategy"]).iloc[:650])


def test_gross_limit_and_negative_beta(sample):
    cfg = {**load_config()["strategy"], "max_gross": .3}
    signal = pd.DataFrame({"z": -2., "annual_residual_vol": .01}, index=sample.index)
    weights = target_weights(signal, pd.Series(-2., index=sample.index), cfg)
    assert weights.abs().sum(axis=1).max() <= .3 + 1e-12
    assert (weights.loc[weights.btc > 0, "qqq"] > 0).all()


def test_entry_exit_stop_and_holding_cap():
    z = pd.Series([-2., -1., .1, 2., 4., -2., -2., -2.])
    state = position_state(z, 1.5, .25, 3.5, 2)
    assert state.tolist() == [1., 1., 0., -1., 0., 1., 1., 0.]


def test_block_bootstrap_keeps_pairing():
    x = np.arange(100)
    values = np.column_stack([x, 3*x])
    draws = block_bootstrap(values, lambda a: np.max(abs(a[:, 1] - 3*a[:, 0])), samples=50)
    assert (draws == 0).all()


def test_explosive_ar_has_no_ou_half_life():
    series = pd.Series(1.01 ** np.arange(500))
    assert np.isnan(ou_diagnostic(series)["half_life_sessions"])


def test_dollar_beta_is_translated_to_units_and_signed():
    result = hedge_units(2, 50_000, 500, 1.2)
    assert result["hedge_units"] == -240
    assert result["rounding_residual_beta_dollars"] == 0
    assert hedge_units(-2, 50_000, 500, 1.2)["hedge_units"] == 240
    assert hedge_units(2, 50_000, 20_000, 1.2, multiplier=2)["hedge_units"] == -3
