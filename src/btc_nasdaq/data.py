"""Auditable public data ingestion with an explicit shared observation clock."""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import requests
import yfinance as yf
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from btc_nasdaq.config import load_config, project_root

COINBASE_URL = "https://api.exchange.coinbase.com/products/{product}/candles"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def session_schedule(start: str, end: str, calendar: str = "NASDAQ") -> pd.DataFrame:
    """End is exclusive; timestamps are UTC, index labels are naive session dates."""
    last = pd.Timestamp(end) - pd.Timedelta(days=1)
    return mcal.get_calendar(calendar).schedule(start_date=start, end_date=last)


def download_equity(ticker: str, start: str, end: str, cache: Path) -> pd.DataFrame:
    if cache.exists():
        return pd.read_parquet(cache)
    yf.set_tz_cache_location(str(cache.parent / "yfinance"))
    frame = yf.download(ticker, start=start, end=end, auto_adjust=False, actions=True,
                        progress=False, threads=False, multi_level_index=False)
    if frame.empty or "Adj Close" not in frame:
        raise RuntimeError(f"No adjusted daily history for {ticker}; no synthetic fallback used.")
    frame.index = pd.DatetimeIndex(frame.index).tz_localize(None).normalize()
    if not frame.index.is_unique:
        raise ValueError("Duplicate equity session labels.")
    frame.to_parquet(cache)
    return frame


def _http_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=0.6, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = "CorrelationResearch/0.1 (historical research)"
    return session


def download_btc(product: str, start: str, end: str, directory: Path) -> pd.DataFrame:
    """Resume immutable 296-hour chunks; Coinbase limits each response to 300 bars."""
    directory.mkdir(parents=True, exist_ok=True)
    cursor, stop = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    chunks = []
    with _http_session() as session:
        count = 0
        while cursor < stop:
            right = min(cursor + pd.Timedelta(hours=296), stop)
            path = directory / f"{cursor:%Y%m%dT%H}_{right:%Y%m%dT%H}.parquet"
            if path.exists():
                chunk = pd.read_parquet(path)
            else:
                response = session.get(COINBASE_URL.format(product=product), params={
                    "start": cursor.isoformat(), "end": right.isoformat(), "granularity": 3600,
                }, timeout=30)
                response.raise_for_status()
                rows = response.json()
                if not isinstance(rows, list) or not rows:
                    raise RuntimeError(f"Missing Coinbase response for {cursor}: {rows}")
                chunk = pd.DataFrame(rows, columns=["time", "low", "high", "open", "close", "volume"])
                chunk.index = pd.to_datetime(chunk.pop("time"), unit="s", utc=True)
                chunk = chunk.loc[(chunk.index >= cursor) & (chunk.index < right)].sort_index()
                chunk.to_parquet(path)
                time.sleep(0.12)
            chunks.append(chunk)
            count += 1
            if count % 25 == 0:
                print(f"Coinbase: {count} chunks through {right.date()}", flush=True)
            cursor = right
    result = pd.concat(chunks).sort_index()
    if not result.index.is_unique:
        raise ValueError("Duplicate Coinbase hourly timestamps.")
    return result


def align_prices(equity: pd.DataFrame, btc: pd.DataFrame, schedule: pd.DataFrame
                 ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Use the close of [T-1h,T), never the candle beginning at equity close T."""
    if not btc.index.is_unique or not equity.index.is_unique:
        raise ValueError("Input timestamps must be unique.")
    if btc.index.tz is None:
        raise ValueError("BTC timestamps must be timezone-aware candle-start times.")
    if not btc.index.is_monotonic_increasing or not equity.index.is_monotonic_increasing:
        raise ValueError("Input timestamps must be sorted.")
    panel = pd.DataFrame(index=schedule.index)
    panel.index.name = "session"
    panel["close_utc"] = schedule.market_close
    candle_start = pd.DatetimeIndex(schedule.market_close) - pd.Timedelta(hours=1)
    panel["btc"] = btc.close.reindex(candle_start).to_numpy()
    panel["qqq"] = equity["Adj Close"].reindex(panel.index)
    panel["qqq_raw"] = equity["Close"].reindex(panel.index)
    # Calendar-date UTC close is intentionally kept only to quantify clock mismatch.
    midnight_bar = pd.DatetimeIndex(panel.index).tz_localize("UTC") + pd.Timedelta(hours=23)
    panel["btc_utc_close"] = btc.close.reindex(midnight_bar).to_numpy()
    panel["elapsed_days"] = panel.close_utc.diff().dt.total_seconds() / 86400
    audit = pd.DataFrame(index=panel.index)
    audit["btc_missing"] = panel.btc.isna()
    audit["qqq_missing"] = panel.qqq.isna()
    audit["nonpositive"] = (panel[["btc", "qqq", "qqq_raw"]] <= 0).any(axis=1)
    audit["early_close"] = panel.close_utc.dt.tz_convert("America/New_York").dt.hour < 16
    audit["multi_day_interval"] = panel.elapsed_days > 1.5
    return panel, audit


def returns_from_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Keep calendar rows: a missing price invalidates both adjacent returns."""
    if not prices.index.is_unique or not prices.index.is_monotonic_increasing:
        raise ValueError("Prices must have a sorted unique index.")
    frame = prices[["btc", "qqq"]]
    if (frame <= 0).any().any():
        raise ValueError("Prices must be positive.")
    return frame.pct_change(fill_method=None)


def fetch_all(root: Path | None = None) -> dict:
    root = root or project_root()
    cfg = load_config(root)["data"]
    raw, processed = root / "data/raw", root / "data/processed"
    raw.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    key = f"{cfg['equity_ticker']}_{cfg['start']}_{cfg['end']}"
    equity_path = raw / f"{key}.parquet"
    equity = download_equity(cfg["equity_ticker"], cfg["start"], cfg["end"], equity_path)
    actual_end = min(pd.Timestamp(cfg["end"]), equity.index.max() + pd.Timedelta(days=1))
    actual_end = actual_end.strftime("%Y-%m-%d")
    btc_path = raw / f"{cfg['crypto_product']}_{cfg['start']}_{actual_end}_1h.parquet"
    if btc_path.exists():
        btc = pd.read_parquet(btc_path)
    else:
        btc = download_btc(cfg["crypto_product"], cfg["start"], actual_end,
                           raw / f"{cfg['crypto_product']}_1h_chunks")
        btc.to_parquet(btc_path)
    schedule = session_schedule(cfg["start"], actual_end, cfg["calendar"])
    panel, audit = align_prices(equity, btc, schedule)
    audit.to_parquet(processed / "alignment_audit.parquet")
    bad = audit[["btc_missing", "qqq_missing", "nonpositive"]].any(axis=1)
    if bad.any():
        raise ValueError(f"{bad.sum()} invalid synchronized sessions; inspect alignment_audit.parquet. "
                         "No observations were forward-filled or silently removed.")
    if not np.isfinite(panel[["btc", "qqq", "qqq_raw"]].to_numpy()).all():
        raise ValueError("Non-finite aligned prices.")
    panel_path = processed / "aligned_prices.parquet"
    panel.to_parquet(panel_path)
    manifest = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested": cfg, "actual_first_session": str(panel.index.min().date()),
        "actual_last_session": str(panel.index.max().date()), "sessions": len(panel),
        "btc_hourly_rows": len(btc), "calendar": cfg["calendar"],
        "alignment": "Coinbase close of [Nasdaq close - 1h, Nasdaq close); exact lookup",
        "equity_price": "QQQ adjusted close for returns; raw close for units",
        "sources": {"btc": COINBASE_URL.format(product=cfg["crypto_product"]),
                    "qqq": f"https://finance.yahoo.com/quote/{cfg['equity_ticker']}/history/"},
        "files": {p.relative_to(root).as_posix(): sha256(p) for p in [equity_path, btc_path, panel_path]},
        "note": "Raw snapshots are cached; retrieval timestamp is pipeline run time. "
                "Delete a cache deliberately to refresh. Public-data research only.",
    }
    (raw / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_prices(root: Path | None = None) -> pd.DataFrame:
    root = root or project_root()
    path = root / "data/processed/aligned_prices.parquet"
    if not path.exists():
        raise FileNotFoundError("Fetch real data first: uv run python scripts/fetch_data.py")
    manifest = json.loads((root / "data/raw/manifest.json").read_text(encoding="utf-8"))
    if manifest["requested"] != load_config(root)["data"]:
        raise ValueError("Data configuration changed. Re-run scripts/fetch_data.py.")
    if sha256(path) != manifest["files"]["data/processed/aligned_prices.parquet"]:
        raise ValueError("Aligned data hash does not match the recorded manifest.")
    return pd.read_parquet(path)
