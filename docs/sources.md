# Source and design ledger

Consulted November 9, 2026. Links below are primary project, provider, exchange or statistical-library sources. Numerical findings come from this repository's recorded data snapshot and code, not from copying published performance claims.

| Source | Use in this project | Limitation |
| --- | --- | --- |
| [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/) | Separate raw/processed data, notebooks, reusable package, reports and tests; ordered notebook names | A structure reference, not a financial-methodology authority |
| [Machine Learning for Trading repository](https://github.com/stefan-jansen/machine-learning-for-trading) | Notebook-led progression from data and research to strategy evaluation | No code or backtest results copied |
| [Coinbase Exchange candle API](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles) | BTC-USD historical hourly OHLCV; bucket timestamps; at most 300 candles per request | Incomplete candles are possible; validates exact required close marks |
| [yfinance download reference](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) | Daily QQQ with explicit unadjusted/adjusted fields and exclusive end date | Community client, not an exchange-grade feed |
| [yfinance project](https://github.com/ranaroussi/yfinance) | Data-use context and client implementation | Respect provider terms; raw history is not redistributed in Git |
| [Yahoo QQQ historical data](https://finance.yahoo.com/quote/QQQ/history/) | Underlying equity data source | Revisions, availability and adjustment methodology can change |
| [pandas-market-calendars](https://pandas-market-calendars.readthedocs.io/en/latest/usage.html) | Actual market schedule, UTC timestamps, holidays and early closes | Library calendar is versioned; extraordinary closures merit review |
| [CME: Why is Bitcoin Moving in Tandem with Equities?](https://www.cmegroup.com/insights/economic-research/2025/why-is-bitcoin-moving-in-tandem-with-equities.html) | Prior evidence motivating a post-2020 regime comparison | Different feed and sample; not evidence for this trading rule |
| [statsmodels Engle–Granger test](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.coint.html) | Residual-based cointegration test; null of no cointegration | Model specification and I(1) assumptions matter |
| [statsmodels ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html) | Unit-root diagnostic and lag selection | Generated training residuals require appropriate critical values |
| [statsmodels KPSS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html) | Complementary stationarity-null diagnostic | Tabulated p-values have boundaries |
| [CME MNQ specifications](https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.contractSpecs.html) | $2 per index point in illustrative futures sizing | Check current specs and actual contract prices; no futures data fit here |
| [Freqtrade lookahead analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/) | Motivation for future-data perturbation checks and explicit timing | No Freqtrade dependency or engine used |
| [uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/) | Locked environment installation in CI | CI checks code offline; market-data retrieval remains explicit |

The repository retains small aggregate tables and rendered research figures, not the raw provider history. Raw and processed Parquet snapshots plus detailed file hashes remain in local ignored directories. The committed summary includes the processed-data and configuration hashes so readers can identify the run. Re-downloading later may not reproduce identical vendor values.
