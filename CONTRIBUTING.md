# Contributing to cai-miner

Thanks for helping. Bug reports with a repository that reproduces the problem
are especially useful: the owner/name, the commit you started from, and the
row you expected or did not expect.

## Development setup

The project is managed with [uv](https://docs.astral.sh/uv/). It installs the
pinned Python version from `.python-version` and every tool from `uv.lock`:

```bash
git clone https://github.com/unlv-evol/cai-miner.git
cd cai-miner
uv sync                      # package in editable mode + dev tools
uv run cai-miner --help
```

`uv sync --all-groups` also installs the `research` group (matplotlib,
openpyxl) that the dataset and paper scripts in `scripts/` need.

## Checks

Run these before opening a pull request; CI runs the same:

```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy                  # type-check src/cai_miner
uv run pytest                # tests (tests/research needs --all-groups)
uv run pytest --cov          # with coverage
```

Optionally install the git hooks so lint and format run on every commit:

```bash
uvx pre-commit install
```

## Repository layout

| path | contents | shipped on PyPI |
| ---- | -------- | --------------- |
| `src/cai_miner/` | the package | yes |
| `src/cai_miner/catalogues/` | bundled detector catalogues | yes |
| `tests/` | package tests | sdist only |
| `tests/research/` | tests of the research scripts | no |
| `docs/` | user and dataset documentation | sdist only |
| `scripts/` | dataset build, validation and paper scripts | no |
| `validation/`, `explorer/` | validation material, dataset explorer | no |
| `zenodo/` | metadata and scripts for the dataset's Zenodo record | no |

## Conventions

- Code style is whatever `ruff format` produces; lint rules are in
  `pyproject.toml`.
- Public functions have type hints and docstrings that explain *why*, not just
  what.
- Every behaviour change comes with a test. Git-history tests build small
  repositories in `tmp_path`; see `tests/test_cai_miner.py`.
- **Do not edit the bundled catalogues.** They are frozen at the versions that
  produced GHAgentCI and a test checks their checksums. Put new patterns in a
  new catalogue file and load it with `-c`.
- Add a line under `[Unreleased]` in `CHANGELOG.md`.

## Releasing

Maintainers only.

1. Update `version` in `pyproject.toml` (or `uv version --bump minor`), the
   `version` in `CITATION.cff`, and move the `[Unreleased]` notes in
   `CHANGELOG.md` under the new version.
2. Check the build locally: `uv build`, then
   `uvx --from dist/cai_miner-*.whl cai-miner --version`.
3. Commit, tag `vX.Y.Z`, and push the tag. The `release` workflow builds the
   distributions and publishes them to PyPI through trusted publishing; no API
   token is stored in the repository.

The first release needs a one-time setup on PyPI: add a *pending trusted
publisher* for the project `cai-miner`, with owner `unlv-evol`, repository
`cai-miner`, workflow `release.yml` and environment `pypi`.
