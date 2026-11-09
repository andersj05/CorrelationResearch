# Research conventions

- Start with README.md, configs/research.toml, and docs/methodology.md.
- Number primary notebooks with two digits. Keep prose and exploration in notebooks; place reusable calculations in src/btc_nasdaq.
- Notebook files are the editable source. Preserve user edits and narrative when making changes.
- Keep raw/provider data and local environments out of Git. Never substitute simulated data for unavailable real research data.
- Match timestamps before computing returns. Preserve missingness and fail rather than forward-fill an unavailable market observation.
- Estimates and signals must be causal. The default execution lag is two rows: an extra session after the information close.
- Separate return-beta hedging, log-price cointegration, and residual-reversal alpha. Do not treat one as proof of another.
- The initial 2024-onward holdout has been inspected. Log new variants and require fresh evaluation before making a new out-of-sample claim.
- Run relevant pytest tests, ruff, and scripts/validate_notebooks.py. If notebook behavior changes, execute the affected notebooks in clean kernels and inspect their plots.
- After changing data/configuration/analysis code, refresh affected summary tables and notebook outputs. Keep docs/research_log.md consistent with the experiment.

## GitHub CLI authentication

- The Windows GitHub CLI account andersj05 is stored in Windows Credential Manager.
- The workspace sandbox may block GitHub traffic and cause a false invalid-token result.
- Never recommend gh auth logout or gh auth login based only on a sandboxed check.
- Verify a failing GitHub command outside the sandbox with the narrowest appropriate approval. Only recommend re-authentication if that check confirms an authentication failure.
