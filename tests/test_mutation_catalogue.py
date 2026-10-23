"""The mutation catalogue and its harness: a mutation run that measures nothing must say so."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "mutation"))

import run_mutants  # noqa: E402

CATALOGUE = run_mutants.load_targets(ROOT / "tools" / "mutation" / "targets.toml")
MUTANTS = [(t, m) for t in CATALOGUE for m in t.mutants]


def write_toml(tmp_path, text):
    path = tmp_path / "targets.toml"
    path.write_text(text)
    return path


# The catalogue stays honest


@pytest.mark.parametrize("target,mutant", MUTANTS, ids=[f"{t.name}/{m.id}" for t, m in MUTANTS])
def test_every_mutant_matches_exactly_one_site(target, mutant):
    _, source, _ = run_mutants.read_source(ROOT / target.module_path)

    run_mutants.apply_mutant(source, mutant)


@pytest.mark.parametrize("target", CATALOGUE, ids=[t.name for t in CATALOGUE])
def test_every_test_file_a_target_runs_exists(target):
    files = [arg for arg in target.test_command.split() if arg.startswith("tests/")]

    assert files
    assert all((ROOT / f).is_file() for f in files), files


@pytest.mark.parametrize("target,mutant", MUTANTS, ids=[f"{t.name}/{m.id}" for t, m in MUTANTS])
def test_every_mutant_names_the_mistake_it_models(target, mutant):
    assert len(mutant.models.split()) >= 5


# apply_mutant


def test_a_pattern_that_no_longer_matches_is_an_error():
    mutant = run_mutants.Mutant("gone", find="old code", replace="x", models="")

    with pytest.raises(ValueError, match="not found"):
        run_mutants.apply_mutant("new code", mutant)


def test_a_pattern_matching_two_sites_is_an_error():
    mutant = run_mutants.Mutant("ambiguous", find="x = 1", replace="x = 2", models="")

    with pytest.raises(ValueError, match="2 times"):
        run_mutants.apply_mutant("x = 1\nx = 1\n", mutant)


# load_targets


def test_a_misspelled_key_is_refused(tmp_path):
    path = write_toml(tmp_path, '''
[[target]]
name = "t"
module-path = "m.py"
test-command = "true"
  [[target.mutant]]
  id = "m"
  find = "a"
  replace = "b"
  model = "singular, so nothing would read it"
''')

    with pytest.raises(ValueError, match="unknown key"):
        run_mutants.load_targets(path)


@pytest.mark.parametrize("extra,message", [
    ('expected = "survived"', "must say why"),
    ('accepted-because = "equivalent"', "does not act on"),
    ('expected = "maybe"', "expected must be"),
])
def test_acceptances_must_be_complete_and_consistent(tmp_path, extra, message):
    path = write_toml(tmp_path, f'''
[[target]]
name = "t"
module-path = "m.py"
test-command = "true"
  [[target.mutant]]
  id = "m"
  find = "a"
  replace = "b"
  {extra}
''')

    with pytest.raises(ValueError, match=message):
        run_mutants.load_targets(path)


# run_target, against a throwaway project


def make_project(tmp_path, test_body):
    (tmp_path / "pkg").mkdir()
    module = tmp_path / "pkg" / "calc.py"
    module.write_bytes(b"def double(x):\r\n    return x * 2\r\n")  # CRLF on purpose: the restore must be byte-exact
    (tmp_path / "test_calc.py").write_text(f"import sys\nsys.path.insert(0, 'pkg')\nimport calc\n\n{test_body}\n")
    command = f"{sys.executable} -m pytest test_calc.py -q -p no:cacheprovider"
    return module, command


def target(module, command, *mutants):
    return run_mutants.Target("calc", Path("pkg") / module.name, command, 60.0, list(mutants))


def test_a_mutant_the_tests_notice_is_killed_and_the_module_restored(tmp_path):
    module, command = make_project(tmp_path, "def test_double():\n    assert calc.double(3) == 6")
    original = module.read_bytes()
    mutant = run_mutants.Mutant("triples", find="x * 2", replace="x * 3", models="")

    results = run_mutants.run_target(target(module, command, mutant), tmp_path)

    assert [(r.mutant_id, r.outcome) for r in results] == [("triples", run_mutants.KILLED)]
    assert module.read_bytes() == original


def test_a_mutant_the_tests_miss_survives(tmp_path):
    module, command = make_project(tmp_path, "def test_double():\n    assert calc.double(0) == 0")
    mutant = run_mutants.Mutant("triples", find="x * 2", replace="x * 3", models="")

    results = run_mutants.run_target(target(module, command, mutant), tmp_path)

    assert [r.outcome for r in results] == [run_mutants.SURVIVED]


def test_a_suite_that_already_fails_scores_nothing(tmp_path):
    module, command = make_project(tmp_path, "def test_double():\n    assert calc.double(3) == 7")
    mutant = run_mutants.Mutant("triples", find="x * 2", replace="x * 3", models="")

    results = run_mutants.run_target(target(module, command, mutant), tmp_path)

    assert [(r.mutant_id, r.outcome) for r in results] == [("<baseline>", run_mutants.NOT_APPLIED)]


def test_a_mutant_that_cannot_be_applied_is_reported_as_such(tmp_path):
    module, command = make_project(tmp_path, "def test_double():\n    assert calc.double(3) == 6")
    mutant = run_mutants.Mutant("stale", find="x + x", replace="x", models="")

    results = run_mutants.run_target(target(module, command, mutant), tmp_path)

    assert [r.outcome for r in results] == [run_mutants.NOT_APPLIED]


def test_cached_bytecode_for_the_module_is_purged(tmp_path):
    # Python trusts a .pyc whose recorded size and mtime (in whole seconds) match the source, so a
    # same-length mutant written within a second of the last run would never be compiled
    module, _ = make_project(tmp_path, "")
    cache = tmp_path / "pkg" / "__pycache__"
    cache.mkdir()
    (cache / "calc.cpython-39.pyc").write_bytes(b"stale")
    (cache / "other.cpython-39.pyc").write_bytes(b"unrelated")

    run_mutants.purge_bytecode(module)

    assert sorted(p.name for p in cache.iterdir()) == ["other.cpython-39.pyc"]


def test_tests_run_without_writing_bytecode_and_with_deterministic_hypothesis(tmp_path):
    module, _ = make_project(tmp_path, "")
    check = (f"{sys.executable} -c \"import os, sys; e = os.environ; "
             f"sys.exit(e.get('PYTHONDONTWRITEBYTECODE') != '1' or e.get('AAAGAS_HYPOTHESIS_PROFILE') != 'ci')\"")

    result = run_mutants._score(target(module, check), run_mutants.Mutant("<baseline>", "", "", ""), tmp_path)

    assert result.outcome == run_mutants.SURVIVED  # the child exited 0, so both settings reached it


@pytest.mark.parametrize("outcome,expected,code", [
    (run_mutants.KILLED, run_mutants.KILLED, 0),
    (run_mutants.SURVIVED, run_mutants.KILLED, 1),
    (run_mutants.SURVIVED, run_mutants.SURVIVED, 0),
    (run_mutants.KILLED, run_mutants.SURVIVED, 1),
    (run_mutants.NOT_APPLIED, run_mutants.KILLED, 1),
])
def test_the_exit_code_fails_on_anything_the_catalogue_did_not_expect(outcome, expected, code, capsys):
    result = run_mutants.MutantResult("t", "m", outcome, "", expected)

    assert run_mutants.report([result]) == code
