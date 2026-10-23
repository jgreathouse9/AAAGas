"""Run the mutant catalogue in ``targets.toml``.

    python tools/mutation/run_mutants.py                  # every target
    python tools/mutation/run_mutants.py --target countyutils
    python tools/mutation/run_mutants.py --list

A slimmed port of mlsynth's tools/mutation/run_mutants.py. For each catalogued
mutant: plant the defect in the module, confirm it landed, run that target's
tests, and restore the module. Failing tests mean the mutant was killed: the
suite noticed the defect. Passing tests mean it survived, which is a question
and not a verdict: either an assertion is too weak, or the mutant is equivalent
to the original.

The harness keeps mlsynth's four guarantees, because each one is a way for a
mutation run to report confidence it never measured:

* A mutant whose ``find`` text matches no site, or more than one, is an error,
  never a survivor.
* The unmutated suite must pass first; otherwise every mutant "fails" a suite
  that was already red and the run scores perfectly while measuring nothing.
* Cached bytecode is purged before every run and the child writes none, since
  a mutant the same length as the code it replaces can match the ``.pyc`` the
  previous run wrote and never be compiled.
* The module is restored byte for byte on every path, and the harness refuses
  to start while a target module has uncommitted changes.

Never ``git add -A`` while this is running: it edits source files in place.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 and below
    import tomli as tomllib

KILLED = "killed"
SURVIVED = "survived"
NOT_APPLIED = "not-applied"

# A misspelled key would otherwise be an instruction that silently does not run
TARGET_KEYS = frozenset({"name", "module-path", "test-command", "timeout", "mutant"})
MUTANT_KEYS = frozenset({"id", "find", "replace", "models", "expected", "accepted-because"})


@dataclass(frozen=True)
class Mutant:
    id: str
    find: str
    replace: str
    models: str
    expected: str = KILLED
    accepted_because: str = ""


@dataclass(frozen=True)
class Target:
    name: str
    module_path: Path
    test_command: str
    timeout: float
    mutants: List[Mutant] = field(default_factory=list)


@dataclass(frozen=True)
class MutantResult:
    target: str
    mutant_id: str
    outcome: str
    detail: str
    expected: str = KILLED


def load_targets(path: Path) -> List[Target]:
    """Parse ``targets.toml`` into ``Target`` objects, refusing keys nothing reads."""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    targets = []
    for entry in data.get("target", []):
        _reject_unknown(f"target {entry.get('name', '<unnamed>')!r}", entry, TARGET_KEYS)
        targets.append(Target(
            name=entry["name"],
            module_path=Path(entry["module-path"]),
            test_command=entry["test-command"],
            timeout=float(entry.get("timeout", 300.0)),
            mutants=[_mutant(entry["name"], m) for m in entry.get("mutant", [])],
        ))
    return targets


def _reject_unknown(where: str, entry: dict, allowed: frozenset) -> None:
    unknown = sorted(set(entry) - allowed)
    if unknown:
        raise ValueError(
            f"{where}: unknown key(s) {', '.join(repr(k) for k in unknown)}; "
            f"this harness reads only {', '.join(sorted(allowed))}")


def _mutant(target: str, entry: dict) -> Mutant:
    """Build one ``Mutant``. An accepted survivor must say why, and only an accepted survivor may."""
    where = f"{target}/{entry.get('id', '<unnamed>')}"
    _reject_unknown(where, entry, MUTANT_KEYS)
    expected = entry.get("expected", KILLED)
    because = entry.get("accepted-because", "")
    if expected not in (KILLED, SURVIVED):
        raise ValueError(f"{where}: expected must be {KILLED!r} or {SURVIVED!r}; got {expected!r}")
    if expected == SURVIVED and not because.strip():
        raise ValueError(f"{where}: a mutant expected to survive must say why in accepted-because")
    if expected == KILLED and because.strip():
        raise ValueError(f"{where}: accepted-because without expected = {SURVIVED!r} records an "
                         f"acceptance the run does not act on")
    return Mutant(id=entry["id"], find=entry["find"], replace=entry["replace"],
                  models=entry.get("models", ""), expected=expected, accepted_because=because)


def apply_mutant(source: str, mutant: Mutant) -> str:
    """Return ``source`` with ``mutant`` applied; raise ValueError unless ``find`` matches exactly once."""
    count = source.count(mutant.find)
    if count == 0:
        raise ValueError(f"pattern not found; the code was probably refactored. Update or retire "
                         f"the mutant: {mutant.find!r}")
    if count > 1:
        raise ValueError(f"pattern occurs {count} times; it must identify exactly one site: {mutant.find!r}")
    return source.replace(mutant.find, mutant.replace, 1)


def read_source(module: Path):
    """Return ``(raw_bytes, text_with_LF, newline)`` so the restore can be byte-exact."""
    raw = module.read_bytes()
    text = raw.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    return raw, text.replace("\r\n", "\n"), newline


def write_source(module: Path, text: str, newline: str) -> None:
    module.write_bytes(text.replace("\n", newline).encode("utf-8"))


def purge_bytecode(module: Path) -> None:
    """Delete cached bytecode for ``module`` so a same-length mutant cannot hide behind it."""
    cache = module.parent / "__pycache__"
    if cache.is_dir():
        for stale in cache.glob(f"{module.stem}.*.pyc"):
            stale.unlink()


def run_target(target: Target, root: Path) -> List[MutantResult]:
    """Run every mutant of ``target`` after checking the unmutated suite passes."""
    module = Path(root) / target.module_path
    raw, original, newline = read_source(module)

    baseline = _score(target, Mutant("<baseline>", "", "", ""), root)
    if baseline.outcome != SURVIVED:
        return [MutantResult(target.name, "<baseline>", NOT_APPLIED,
                             f"the tests do not pass on the unmutated module, so no mutant can be "
                             f"scored against them ({baseline.detail})")]

    results: List[MutantResult] = []
    for mutant in target.mutants:
        try:
            mutated = apply_mutant(original, mutant)
        except ValueError as exc:
            results.append(MutantResult(target.name, mutant.id, NOT_APPLIED, str(exc), mutant.expected))
            continue
        try:
            write_source(module, mutated, newline)
            results.append(_score(target, mutant, root))
        finally:
            module.write_bytes(raw)
    return results


def _score(target: Target, mutant: Mutant, root: Path) -> MutantResult:
    """Run the target's test command and classify the outcome."""
    purge_bytecode(Path(root) / target.module_path)
    # Deterministic hypothesis: a mutant killed by an unlucky draw would corrupt the score
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "AAAGAS_HYPOTHESIS_PROFILE": "ci"}
    try:
        completed = subprocess.run(shlex.split(target.test_command), cwd=str(root), env=env,
                                   capture_output=True, text=True, timeout=target.timeout)
    except subprocess.TimeoutExpired:
        return MutantResult(target.name, mutant.id, KILLED,
                            f"the tests timed out after {target.timeout}s", mutant.expected)
    except (OSError, ValueError) as exc:
        return MutantResult(target.name, mutant.id, NOT_APPLIED,
                            f"the test command could not be run: {exc}", mutant.expected)
    if completed.returncode == 0:
        detail = (f"the tests passed with this defect in place; {mutant.models}"
                  if mutant.expected == KILLED else f"as the catalogue expects; {mutant.accepted_because}")
        return MutantResult(target.name, mutant.id, SURVIVED, detail, mutant.expected)
    return MutantResult(target.name, mutant.id, KILLED, f"exit {completed.returncode}", mutant.expected)


def report(results: Sequence[MutantResult]) -> int:
    """Print a table and return the exit code: 0 only if every outcome matches the catalogue."""
    width = max((len(f"{r.target}/{r.mutant_id}") for r in results), default=20)
    for r in results:
        label = r.outcome
        if r.expected == SURVIVED:
            label = f"{r.outcome} (accepted)" if r.outcome == SURVIVED else f"{r.outcome} (acceptance stale)"
        print(f"  {r.target + '/' + r.mutant_id:<{width}}  {label:<26}  {r.detail[:100]}")

    killed = sum(r.outcome == KILLED for r in results)
    survived = [r for r in results if r.outcome == SURVIVED and r.expected == KILLED]
    stale = [r for r in results if r.outcome == KILLED and r.expected == SURVIVED]
    broken = [r for r in results if r.outcome == NOT_APPLIED]
    print(f"\n{killed}/{len(results)} killed, {len(survived)} survived, {len(broken)} could not be applied")
    if survived:
        print("Survivors are a question: is the assertion too weak, or is the mutant equivalent to the "
              "original? Record the answer either way.")
    if stale:
        print("An accepted survivor was killed; its acceptance is out of date and should be removed.")
    if broken:
        print("A mutant that could not be applied measures nothing. Fix the pattern or retire the mutant.")
    return 1 if (survived or stale or broken) else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", help="run only this target")
    parser.add_argument("--list", action="store_true", help="list the catalogue without running it")
    parser.add_argument("--targets-file", default=str(Path(__file__).parent / "targets.toml"))
    args = parser.parse_args(argv)

    targets = load_targets(Path(args.targets_file))
    if args.target:
        targets = [t for t in targets if t.name == args.target]
        if not targets:
            parser.error(f"no target named {args.target!r}")

    if args.list:
        for target in targets:
            print(f"{target.name}  ({target.module_path})")
            for mutant in target.mutants:
                print(f"    {mutant.id}: {mutant.models}")
        return 0

    dirty = subprocess.run(["git", "status", "--porcelain", "--"] + [str(t.module_path) for t in targets],
                           cwd=str(root), capture_output=True, text=True)
    if dirty.stdout.strip():
        print("Refusing to run: a target module has uncommitted changes, so a crashed run could not be "
              "told from an edit.\n" + dirty.stdout, file=sys.stderr)
        return 2

    results: List[MutantResult] = []
    for target in targets:
        print(f"\n{target.name}: {len(target.mutants)} mutants against {target.module_path}")
        results.extend(run_target(target, root))
    return report(results)


if __name__ == "__main__":
    raise SystemExit(main())
