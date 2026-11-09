"""Find the project from notebooks or scripts and load versioned assumptions."""

import tomllib
from pathlib import Path


def project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for path in (current, *current.parents):
        if (path / "configs" / "research.toml").exists():
            return path
    raise FileNotFoundError("Run inside the CorrelationResearch project.")


def load_config(root: Path | None = None) -> dict:
    with ((root or project_root()) / "configs" / "research.toml").open("rb") as handle:
        return tomllib.load(handle)
