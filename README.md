# Bitcoin / Nasdaq Research Lab

A notebook-first lab for testing whether Bitcoin-specific mean reversion survives a changing Nasdaq hedge, trading delays, and realistic costs. Start with `notebooks/00_research_map.ipynb` and follow the numbered notebooks.

## Quick start

Python 3.12 and [uv](https://docs.astral.sh/uv/) are recommended. From this folder:

```powershell
uv sync --locked
uv run python scripts/fetch_data.py
uv run python scripts/run_research.py
uv run jupyter lab
```

In Jupyter, choose the project's `.venv` interpreter. For VS Code, select `.venv/Scripts/python.exe`. The environment includes a portable `python3` kernel; no global kernel registration is required.

## Research sequence

| Notebook | Question |
| --- | --- |
| `00_research_map` | What are we testing, and what would falsify it? |
| `01_data_quality` | Do BTC and QQQ returns cover the same intervals? |
| `02_correlation_regimes` | How does dependence change over time and in stress? |
| `03_dynamic_hedging` | Which causal beta forecast removes the most risk? |
| `04_mean_reversion` | Is there evidence of a predictable residual process? |
| `05_walk_forward` | Does the fixed rule survive delays, costs, and holdouts? |
| `06_hedge_sizing_and_stress` | How does a return beta translate into units and risks? |
| `07_research_review` | What did the first pass establish, and what comes next? |

## Layout

```text
configs/           Versioned assumptions and sample boundaries
data/raw/          Local provider downloads and retrieval manifests (ignored)
data/processed/    Aligned prices and audit tables (ignored)
docs/              Methodology, sources, and research decisions
notebooks/         Ordered, self-contained research narratives and figures
reports/figures/   Selected portable figures
reports/tables/    Reproducible research summaries
scripts/           Fetch data, execute notebooks, and produce research outputs
src/btc_nasdaq/    Reusable data, estimation, signals, simulation, and plotting code
tests/             Timing, estimator, accounting, and data-quality checks
```

The organization follows [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/), with two-digit notebook names and a small importable package. Notebook files are the editable research source; calculations that need testing live in `src/`.

## Research contract

- BTC-USD spot from Coinbase and QQQ from Yahoo Finance via yfinance. QQQ is an investable Nasdaq-100 proxy, not the Nasdaq Composite or a futures series.
- Match BTC's last completed hourly candle to each actual Nasdaq session close, including DST and early closes. Never forward-fill missing market observations.
- Use simple returns for return-beta hedges and P&L. Keep return regression separate from log-price cointegration.
- Estimate causally. A signal observed after close `t` executes at close `t+1` and first earns the return ending at `t+2`.
- Test hedge quality separately from alpha. Lower residual volatility is not evidence that a residual price level mean reverts.
- Keep raw vendor data out of Git. Commit code, assumptions, selected figures, and executed research notebooks; a source manifest records provenance and hashes locally.

This is a research implementation, not a live trading system. Hedge beta is conditional and uncertain; crypto-specific jumps, other factors, weekend gaps, financing, and instrument basis remain.

More detail and initial findings are recorded in `docs/` and the executed notebooks.
