#!/usr/bin/env python3
"""Target provider for numpy: builds a revision with `spin`, in a worktree of its own.

benchx runs this with a JSON request on stdin and reads one target description from
stdout (progress and errors go to stderr). `source_ref` is a revision of the numpy
checkout $NUMPY (a tag, a branch, a commit), or WORKSPACE for $NUMPY itself.

Every other revision gets a git worktree under $WORKTREES, named after the commit.
`spin build` writes `build/` and `build-install/` inside the checkout it runs in, so
two worktrees are two builds that exist at once, which a comparison needs.

    prepare    creates the worktree if there is none and runs `spin build` in it
               (incremental: nearly a no-op when nothing changed)
    describe   builds nothing; reports a build made before, and fails if there is none

The target is the directory that holds the built package,
`build-install/usr/lib/python3.X/site-packages`, and not the build directory: pyperf
puts the target's directory first on `sys.path` for the benchmark, so each side
imports its own build, in one shared environment, with no PYTHONPATH.

how_built is an object: how numpy was built (numpy_facts.py). The collector in
benchx.conf.json asks the same of the benchmark's process, and the run is refused if
the two differ. The provider also refuses to describe a numpy that is not the
checkout's HEAD: the version of a numpy built from git ends in the commit's hash, and
a release build is the checkout's tag.
"""

import fcntl
import json
import os
import re
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
numpy_dir = Path(os.environ.get("NUMPY", "~/repos/numpy")).expanduser()
worktrees = Path(os.environ.get("WORKTREES", f"{numpy_dir}-worktrees")).expanduser()


def fail(message):
    sys.exit(f"provider.py: {message}")


def run(*args, cwd):
    """A command whose output is progress: it goes to stderr, stdout is the answer."""
    try:
        subprocess.run(args, cwd=cwd, check=True, stdout=sys.stderr)
    except (OSError, subprocess.CalledProcessError) as e:
        fail(f"`{' '.join(args)}` failed in {cwd}: {e}")


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True).stdout.strip()


request = json.load(sys.stdin)
operation, ref = request["operation"], request["source_ref"]
if not (numpy_dir / ".git").exists():
    fail(f"{numpy_dir} is not a git checkout of numpy: set NUMPY")

if ref == "WORKSPACE":
    checkout = numpy_dir
else:
    commit = git(numpy_dir, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if not commit:
        fail(f"{ref!r} is not a revision of {numpy_dir}")
    checkout = worktrees / f"{re.sub(r'[^A-Za-z0-9._-]+', '-', ref)}-{commit[:10]}"

if operation == "prepare":
    # Two providers at once would race on the shared .git/config while initializing submodules.
    worktrees.mkdir(parents=True, exist_ok=True)
    with open(worktrees / ".provider.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not checkout.exists():
            run("git", "worktree", "add", "--detach", str(checkout), commit, cwd=numpy_dir)
            run("git", "submodule", "update", "--init", cwd=checkout)
        run("spin", "build", cwd=checkout)
elif not checkout.exists():
    fail(f"no worktree for {ref!r}: nothing was prepared")

packages = [p for p in sorted((checkout / "build-install").glob("**/site-packages")) if (p / "numpy").is_dir()]
if len(packages) != 1:
    fail(f"expected one site-packages with numpy under {checkout}/build-install, found {len(packages)}")
package = packages[0]

# Run in the package directory: numpy_facts.py imports the numpy it finds there.
done = subprocess.run([sys.executable, str(here / "numpy_facts.py")], cwd=package, capture_output=True, text=True)
if done.returncode:
    fail(f"the numpy in {package} did not report its facts:\n{done.stderr.strip()}")
facts = json.loads(done.stdout)
facts.pop("summary")  # readable extras for the results, not part of the declaration

# The version spin wrote when it built, read without importing: it is not among the facts.
version = re.search(r"""^version = ["']([^"']+)["']""", (package / "numpy" / "version.py").read_text(), re.M)[1]
head = git(checkout, "rev-parse", "HEAD")
built_from = re.search(r"git\d+\.([0-9a-f]+)", version)
if not (built_from and head.startswith(built_from[1])) and git(checkout, "describe", "--tags", "--exact-match") != f"v{version}":
    fail(f"numpy {version} in {package} is not the checkout's HEAD {head[:10]}: rebuild")

print(json.dumps({
    "schema_version": "benchx/target-description/0.1.0",
    "target": {"kind": "build", "path": str(package),
               "source": {"uri": "https://github.com/numpy/numpy.git", "type": "git"},
               "source_dir": str(checkout)},
    "how_built": facts,
    "provider": {"name": "provider.py", "version": "1"},
}, indent=1))
