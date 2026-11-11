# GHAgentCI notebooks

Four short notebooks that show how to load the GHAgentCI dataset
([doi:10.5281/zenodo.24088832](https://doi.org/10.5281/zenodo.24088832)) and run simple
analyses. Each is self-contained: it downloads the files it needs from Zenodo and uses only
pandas, NumPy, matplotlib and (in notebook 4) PyYAML. Column definitions are in
[docs/DATASET.md](https://github.com/unlv-evol/cai-miner/blob/main/docs/DATASET.md).

| notebook | | what it covers |
|---|---|---|
| [01-getting-started](01-getting-started.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/unlv-evol/cai-miner/blob/main/notebooks/01-getting-started.ipynb) | The tables, how they join, and the paper's headline numbers reproduced. |
| [02-adoption-over-time](02-adoption-over-time.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/unlv-evol/cai-miner/blob/main/notebooks/02-adoption-over-time.ipynb) | When repositories adopt agents, per agent and per language, and how many stop. |
| [03-triggers-and-safeguards](03-triggers-and-safeguards.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/unlv-evol/cai-miner/blob/main/notebooks/03-triggers-and-safeguards.ipynb) | Triggers, actor gating, permissions, action pinning and task labels at the latest snapshot. |
| [04-gh-aw-and-workflow-content](04-gh-aw-and-workflow-content.ipynb) | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/unlv-evol/cai-miner/blob/main/notebooks/04-gh-aw-and-workflow-content.ipynb) | GitHub Agentic Workflows manifests, and reading and parsing workflow YAML from `content.tar.gz`. |

## On Google Colab

Click a badge above and choose *Runtime → Run all*. Nothing needs installing. The tables are
about 40 MB in total; notebook 4 also downloads `content.tar.gz` (808 MB), which you can skip by
setting `DOWNLOAD_CONTENT = False`.

## Locally

From the repository root:

```sh
uv run --group notebooks jupyter lab
```

The notebooks cache downloads in a `ghagentci-data` folder next to them. To use files you already
have, point `GHAGENTCI_DATA` at their folder (an absolute path, since the kernel runs in
`notebooks/`):

```sh
GHAGENTCI_DATA=/path/to/ghagentci uv run --group notebooks jupyter lab
```
