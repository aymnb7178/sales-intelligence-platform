"""One-command demo: synthetic data -> SQL analytics -> charts -> dashboard -> CSV export."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sales_intel.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["all"]))
