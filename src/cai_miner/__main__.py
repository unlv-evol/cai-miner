"""Allow ``python -m cai_miner``, as the mining scripts invoke it."""

from cai_miner.cli import main

raise SystemExit(main())
