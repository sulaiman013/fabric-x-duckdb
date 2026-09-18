# Notebook: build the gold layer in Fabric

This file was the design for the Fabric **Python** notebook that runs Phase 2
on capacity. The notebook itself is now generated, imported and run:

- Generator: `scripts/build_gold_notebook.py`
- Output: `notebooks/01_build_gold.Notebook/` (the ipynb Fabric imports)
- Workspace item: `02 Transformation / 01_build_gold`
- Evidence of each run: `Files/build_gold.json` in the `fincrime` lakehouse

The generator embeds `transform.py`, `rules.py` and `star.py` verbatim, so the
code that was validated against the full 50,000,000 rows on a laptop is
byte-for-byte the code that runs on capacity.

## What changed from the design

| Design said | What runs |
| --- | --- |
| `%%configure` | `%%configure -f` as the first cell, so an API-triggered run honours 8 vCores; a `%`-formatting slip once turned it into `%configure` and the job died in twelve seconds |
| `%pip install duckdb` | nothing installed; the Python runtime ships DuckDB (1.2.2 at the time of writing) and pinning a different version would only make the run differ from the runtime everyone else has |
| import the modules from `scripts/` | the modules are embedded in the notebook and written to a temp directory at run time; a notebook cannot import from the repo |
| "the same bytes the laptop build did" | not true of the laptop build, which parsed epoch timestamps in the laptop's timezone; the build is now deterministic, see BUILD_LOG section 40 |
| counts only | per-rule firings and a dedup reconciliation are recorded too, so two runs can be compared rule by rule |

Attach the **`fincrime`** Lakehouse as the default lakehouse (the generator
writes it into the notebook metadata, which is what makes a CLI-triggered run
work). The mirrored table is shortcut into it at `Tables/raw_txn`.

Run it with `fab job start "fabric duckdb.Workspace/01_build_gold.Notebook"`,
then `02_vorder_write` and `03_verify`.
