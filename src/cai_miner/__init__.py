"""cai-miner: mine coding-agent invocations from CI workflow histories.

The command-line tool is the main interface (``cai-miner --help``). The pieces
it is built from can also be used directly:

* :func:`cai_miner.config.load_config` reads a detector catalogue (by default
  the bundled one, :data:`cai_miner.config.DEFAULT_CATALOGUE`);
* :func:`cai_miner.detect.analyse` classifies one workflow revision;
* :func:`cai_miner.extract.extract_repository` mines one local clone.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cai-miner")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
