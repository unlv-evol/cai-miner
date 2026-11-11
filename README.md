# cai-miner

[![CI](https://github.com/unlv-evol/cai-miner/actions/workflows/ci.yml/badge.svg)](https://github.com/unlv-evol/cai-miner/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/cai-miner.svg)](https://pypi.org/project/cai-miner/)
[![Python](https://img.shields.io/pypi/pyversions/cai-miner.svg)](https://pypi.org/project/cai-miner/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/unlv-evol/cai-miner/blob/main/LICENSE)

**cai-miner** (Coding-Agent Invocations miner) mines the git history of GitHub
Actions workflow files and finds the **coding-agent invocations** inside them:
the steps that run Claude Code, Codex, Copilot, Gemini, Cursor, Aider and
similar agents as part of a repository's continuous integration.

For every workflow file that invokes an agent at some point, it emits the
file's whole history (before the agent arrived, while it was there, and after
it was removed), one row per agent invocation, and repository-level
denominators. It is the tool behind the **GHAgentCI** dataset.

## Why content-based detection

Agent context files such as `CLAUDE.md` or `AGENTS.md` can be classified by
path, since the filename names the agent. An agentic CI workflow cannot: it is
an ordinary `.github/workflows/whatever.yml`, indistinguishable by name from a
build or lint workflow. cai-miner therefore parses every revision of every
workflow file, walks its jobs and steps, and matches each step against a
catalogue of agents.

Not every mention of an agent is an invocation; a workflow that sets
`ANTHROPIC_API_KEY` may just be feeding a test suite. Evidence is therefore
tiered:

| evidence | meaning | strength |
| -------- | ------- | -------- |
| `uses` | a step invokes a dedicated agent GitHub Action | strong |
| `run` | a step shell-invokes an agent CLI | strong |
| `path` | the workflow file has a reserved, agent-specific name | strong |
| `ghaw` | the file was compiled by GitHub Agentic Workflows | strong |
| `job` | a job carries a reserved, agent-specific id | weak |
| `url` | a step talks to an LLM inference endpoint | weak |
| `env` | an agent or LLM credential is bound at that scope | weak |

A revision counts as agentic only with strong evidence, unless you pass
`--include-weak`.

## Installation

cai-miner needs Python 3.11 or newer and `git` 2.30 or newer on the `PATH`. Its
only Python dependency is PyYAML.

```bash
uv tool install cai-miner     # recommended: an isolated, global command
pipx install cai-miner        # equivalent with pipx
pip install cai-miner         # into the current environment
```

Or run it once without installing: `uvx cai-miner --help`.

## Quickstart

cai-miner works on local clones. A size-capped partial clone without a working
tree is the fastest way to get one (see [cloning](https://github.com/unlv-evol/cai-miner/blob/main/docs/cloning.md)):

```bash
git clone --filter=blob:limit=64k --no-checkout --single-branch \
    https://github.com/vitejs/vite.git clones/vite

# Agent invocations across the whole history, as CSV on stdout
cai-miner clones/vite

# Full outputs for many clones, plus every distinct workflow revision
cai-miner --from-file clones.txt -o out/ --content-dir out/content
```

With `-o out/` you get:

| file | one row per |
| ---- | ----------- |
| `repositories.csv` | repository, agentic or not, including failures |
| `revisions.csv` | change to a workflow file whose history is agentic at some point |
| `steps.csv` | agent invocation |
| `ghaw_manifests.csv` | revision of a GitHub Agentic Workflows source or compiled file |

Every column is documented in the
[output reference](https://github.com/unlv-evol/cai-miner/blob/main/docs/output.md).

## Command-line reference

```
cai-miner [options] [REPOSITORY ...]
```

| option | effect |
| ------ | ------ |
| `-c`, `--config FILE` | detector catalogue (TOML); defaults to the bundled frozen catalogue |
| `--from-file FILE` | read clone paths from a file, one per line |
| `-o`, `--out-dir DIR` | write the four CSV files to `DIR` |
| `--content-dir DIR` | store each distinct workflow revision as `DIR/<sha256>.yml` |
| `--rev REV` | commit to start the history walk from (default `HEAD`) |
| `--since DATE` | ignore commits older than `DATE`, e.g. `2024-01-01` |
| `--include-weak` | let `job`, `url` and `env` evidence make a revision agentic |
| `--keep-all` | emit every workflow revision, not only agentic histories |
| `--no-prefetch` | disable the bulk blob prefetch on partial clones |
| `--repository OWNER/NAME` | name of the single repository given, instead of reading it from the clone's remote |
| `--fail-fast` | stop at the first repository that fails |
| `-q`, `--quiet` | suppress progress output |
| `--version` | print the version and exit |

`python -m cai_miner` is equivalent to `cai-miner`.

## Detector catalogue

Agents and their patterns live in a TOML catalogue; adding an agent needs no
code changes:

```toml
[agents.myagent]
display_name = "My Agent"
uses = ["myorg/my-agent-action"]
run  = ["myagent --run"]
env  = ["MYAGENT_API_KEY"]
```

The bundled default is the catalogue GHAgentCI was mined with: a hand-written
catalogue drawn from vendor documentation, merged with one generated from the
GitHub Marketplace `ai-assisted` category. See the
[catalogue reference](https://github.com/unlv-evol/cai-miner/blob/main/docs/catalogue.md)
for the format, includes, aliases and overrides.

Files generated by [GitHub Agentic Workflows](https://github.com/github/gh-aw)
are detected from the compiler's own header, with no catalogue involved, and
their manifests are parsed in full; see
[gh-aw](https://github.com/unlv-evol/cai-miner/blob/main/docs/ghaw.md).

## Using it from Python

```python
from cai_miner.config import load_config
from cai_miner.detect import analyse
from cai_miner.extract import extract_repository

catalogue = load_config()  # the bundled catalogue; or load_config("my.toml")

# Classify one workflow revision
facts = analyse(catalogue, open("ci.yml").read(), ".github/workflows/ci.yml")
print(facts.strong_agents)

# Mine one local clone
result = extract_repository("clones/vite", catalogue)
print(result.summary.n_agentic_files, len(result.steps))
```

The command line is the stable interface; the Python modules may change
between minor versions before 1.0.

## Reproducing GHAgentCI

The GHAgentCI dataset and its replication package are archived on Zenodo at
[doi:10.5281/zenodo.24088832](https://doi.org/10.5281/zenodo.24088832). Browse it
in the [GHAgentCI explorer](https://unlv-evol.github.io/cai-miner/), or start
from the [notebooks](https://github.com/unlv-evol/cai-miner/tree/main/notebooks),
which load the data and run simple analyses (they also run on Google Colab).
This repository also holds the scripts and validation material behind the
dataset; they are not part of the installed package:

- [`docs/FULL_RUN.md`](https://github.com/unlv-evol/cai-miner/blob/main/docs/FULL_RUN.md): how the full mining run was set up, monitored and resumed;
- [`docs/DATASET.md`](https://github.com/unlv-evol/cai-miner/blob/main/docs/DATASET.md): the released tables, field by field;
- [`BENCHMARKS.md`](https://github.com/unlv-evol/cai-miner/blob/main/BENCHMARKS.md): throughput and clone-strategy measurements.

## Citing

If you use cai-miner or GHAgentCI in research, please cite it; GitHub's
"Cite this repository" button reads
[`CITATION.cff`](https://github.com/unlv-evol/cai-miner/blob/main/CITATION.cff).

## Contributing

Bug reports and pull requests are welcome. See
[CONTRIBUTING.md](https://github.com/unlv-evol/cai-miner/blob/main/CONTRIBUTING.md)
for the development setup.

## License

[MIT](https://github.com/unlv-evol/cai-miner/blob/main/LICENSE)
