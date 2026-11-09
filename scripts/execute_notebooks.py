"""Execute real-data notebooks in fresh kernels and export readable local HTML."""

import argparse
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for key, leaf in [("JUPYTER_RUNTIME_DIR", "jupyter"), ("IPYTHONDIR", "ipython"),
                  ("MPLCONFIGDIR", "matplotlib")]:
    path = ROOT / ".cache" / leaf
    path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(key, str(path))

import nbformat  # noqa: E402
from nbclient import NotebookClient  # noqa: E402
from nbconvert import HTMLExporter  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", default="*.ipynb", help="Notebook glob, e.g. 03*.ipynb")
    parser.add_argument("--no-html", action="store_true")
    args = parser.parse_args()
    paths = sorted((ROOT / "notebooks").glob(args.pattern))
    if not paths:
        raise SystemExit("No notebooks matched.")
    html_dir = ROOT / "reports/html"
    html_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        started = time.monotonic()
        print(f"Executing {path.name}", flush=True)
        notebook = nbformat.read(path, as_version=4)
        client = NotebookClient(notebook, timeout=300, kernel_name="python3",
                                resources={"metadata": {"path": str(ROOT)}})
        client.execute()
        # No partial notebook is saved if a cell fails.
        nbformat.write(notebook, path)
        if not args.no_html:
            body, _ = HTMLExporter(template_name="lab", embed_images=True).from_notebook_node(notebook)
            (html_dir / f"{path.stem}.html").write_text(body, encoding="utf-8")
        print(f"  OK ({time.monotonic()-started:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
