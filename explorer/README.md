# GHAgentCI Explorer

A static web app for exploring the GHAgentCI dataset: which repositories run
coding agents from GitHub Actions, how the agents are wired in, which events
start them, which safeguards constrain them, and how long projects keep them.
It has no server and no framework: one HTML file plus precomputed JSON.

## Build and run

```bash
python3 scripts/build_explorer.py out/full      # ~2 minutes; writes explorer/data/ and explorer/index.html
python3 -m http.server -d explorer 8000         # then open http://localhost:8000
```

Opening `index.html` straight from disk does not work: the browser refuses to
`fetch()` the data files over `file://`. The build needs `out/full/` (the
merged mining output), `data/seart/frame-2026-10-03.csv` (language, stars and
creation date) and the validation results in `manuscripts/shared/`
(`numbers-validation.tex`, `table-validation.tex`, written by
`scripts/score_validation.py`).

## Files

| file | what it is |
|---|---|
| `app.html` | the app: markup, styles and script in one file, with no document skeleton. Edit this one. |
| `index.html` | `app.html` wrapped in a document for local serving (generated, not in git) |
| `data/summary.json` | every aggregate the Overview, Triggers & safeguards and Actions views draw, for both evidence views (plus the validation results, kept for a later Method view) |
| `data/repos.json` | one row per agentic repository, for the Repositories view |
| `data/shards/NN.json` | per-repository detail, in 64 shards keyed by a hash of the name, so opening a repository loads about 1 MB |

The `data/` folder (about 20 MB) is generated and not in git.

## Evidence views

The header switch recomputes every view:

- **All strong evidence** follows the paper: named agents, strong evidence,
  nothing before ChatGPT's release.
- **Explicit calls only** keeps `run` evidence only for prompt-style CLI
  calls (`claude -p`, `claude --print`, `codex exec`, `copilot -p`,
  `gemini -p`). Validation found that most other `run` matches name or
  install an agent without running it (paper, Table II). In the repository
  list such repositories carry a *name/install only* tag.

## What is left out

Author and committer names and emails are never written to the app's data;
whether the dataset release publishes them is still open.
`tests/test_build_explorer.py` checks this.

## The website

The explorer is published on GitHub Pages under the dataset's landing page
(`site/index.html`), at <https://unlv-evol.github.io/cai-miner/>. The `Website`
workflow downloads the released tables from Zenodo and runs
`scripts/build_site.py`, which builds the explorer from them; built from the
release, its data is identical to a build from `out/full`. To preview it:

```bash
uv run python scripts/build_site.py out/zenodo -o _site   # or any folder with the released tables
python3 -m http.server -d _site 8000
```

## Publishing

`app.html` is written for the claude.ai artifact viewer, which wraps the page
in its own document; publish it with the `data/` files beside it. Any static
host works too: serve `index.html` and `data/`.
