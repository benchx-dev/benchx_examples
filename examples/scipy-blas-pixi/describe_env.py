"""The scipy version, blas version, and blas build of the environment."""

import json
import sys
from pathlib import Path

import scipy

[record] = Path(sys.prefix, "conda-meta").glob("libblas-*.json")
libblas = json.loads(record.read_text())

print(json.dumps({"summary": {
    "scipy": scipy.__version__,
    "libblas": libblas["version"],
    "blas": libblas["build"].rsplit("_", 1)[-1],
}}, sort_keys=True))
