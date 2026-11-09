"""Offline notebook structure and Python syntax checks; no provider requests."""

import ast
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
paths = sorted((ROOT / "notebooks").glob("*.ipynb"))
assert len(paths) == 8, "Expected the eight initial research notebooks."
for number, path in enumerate(paths):
    assert path.name.startswith(f"{number:02d}_"), path.name
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source, filename=path.name)
            assert not any(out.output_type == "error" for out in cell.outputs), path.name
    print(f"OK {path.name}")
