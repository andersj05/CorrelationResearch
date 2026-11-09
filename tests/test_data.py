import numpy as np
import pandas as pd
import pytest

from btc_nasdaq.data import align_prices, returns_from_prices, session_schedule


def test_calendar_handles_dst_and_early_close():
    spring = session_schedule("2024-03-08", "2024-03-12")
    assert spring.market_close.dt.hour.tolist() == [21, 20]
    thanksgiving = session_schedule("2024-11-28", "2024-11-30")
    assert len(thanksgiving) == 1
    assert thanksgiving.market_close.iloc[0].hour == 18


def test_alignment_uses_completed_bar_not_future_bar():
    schedule = session_schedule("2024-11-29", "2024-11-30")
    btc = pd.DataFrame({"close": [100., 999.]},
                       index=pd.to_datetime(["2024-11-29 17:00Z", "2024-11-29 18:00Z"]))
    qqq = pd.DataFrame({"Close": [500.], "Adj Close": [490.]}, index=schedule.index)
    prices, audit = align_prices(qqq, btc, schedule)
    assert prices.btc.iloc[0] == 100
    assert prices.qqq.iloc[0] == 490
    assert audit.early_close.iloc[0]


def test_missing_prices_are_not_bridged_or_filled():
    frame = pd.DataFrame({"btc": [100., np.nan, 121., 133.1], "qqq": [100., 101., 102., 103.]})
    result = returns_from_prices(frame)
    assert result.btc.iloc[:3].isna().all()
    assert result.btc.iloc[3] == pytest.approx(.1)


def test_invalid_price_rejected():
    with pytest.raises(ValueError, match="positive"):
        returns_from_prices(pd.DataFrame({"btc": [1, 0], "qqq": [1, 1]}))
