# CLAUDE.md

Guidance for AI agents (Claude Code) working in AAAGas.

## What this repo is

Scheduled GitHub Actions scrape gas prices from [AAA](https://gasprices.aaa.com/) and commit
the results to `main`:

| Workflow | Script | Writes |
| --- | --- | --- |
| County Scraper (`countyscraper.yml`) | `RealCounty/county_scraper_main.py` | `RealCounty/Data/CountyGas<YYYY-MM-DD>.csv` |
| Daily State Gas Price Scraper (`state-scraper.yml`) | `gas.py` | `Prices/MasterGas.csv` |
| City Level Gas Price Scraper (`city-gas-scrape.yml`) | `City Scrape/cityscrape.py` | `City Scrape/Data/City_<date>.csv` |

The county scraper is the one under test. The others are not yet; bring a script under the
rules below before changing its behavior.

Workflows that push to `main` run `git pull --rebase --autostash` first. A scheduled run checks
out the commit `main` pointed at when it was queued, so another scraper's push during the wait
makes a plain `git push` fail.

## Common commands

```bash
pip install requests pandas pytest pytest-cov hypothesis tomli
pytest -q                                                    # the suite
pytest -q --cov=RealCounty --cov-branch --cov-report=term-missing --cov-fail-under=100
python tools/mutation/run_mutants.py                         # the mutant catalogue
python tools/mutation/run_mutants.py --list                  # what it plants, and why
```

`AAAGAS_HYPOTHESIS_PROFILE=ci` makes property tests deterministic; CI and mutation runs set it.

## Testing doctrine

Adapted from mlsynth's `agents/agents_tests.md` for a much smaller project.

Write the test first and watch it fail for the right reason, then make it pass. Each unit of
behavior gets four levels:

- Smoke: one minimal valid run, end to end.
- Unit: the invariants the code promises, such as one row per county, a pause after every
  request, or a wait that never exceeds its cap.
- Edge: boundaries and degenerate input: no states, an empty map, a county with no price,
  accented names, a single attempt, `Retry-After: 0`.
- Failure: a refused request, a page without a map, or malformed map data is logged with the
  state's name and listed in the run's summary. A wrong input raises. Nothing is swallowed, and
  nothing writes a file that looks complete when it is not.

Two instruments sit beside the levels:

- Property: every invariant is asserted over generated input with `hypothesis`, not only at one
  fixture. Keep the generated domain generous; narrowing it needs a comment saying why.
- Mutant: each defect a change could plausibly reintroduce goes in `tools/mutation/targets.toml`
  with a `models` line naming the real mistake, and must be killed. A survivor is a question:
  either an assertion is too weak or the mutant is equivalent. Record the answer either way.

Coverage of `RealCounty/` stays at 100% of lines and branches, and CI fails below it. An
unreachable branch gets `# pragma: no cover` (or `no branch`) with a one-line reason.

Each instrument is blind where the next one looks. Coverage says a line ran, an example says one
input gives one answer, a property says the invariant holds across inputs, and only a mutant says
the assertions would notice the code being wrong.

Practice:

- Tests never touch the network. `tests/helpers.py` has fake sessions that answer like AAA.
- Name a test for the behavior it pins (`test_a_huge_retry_after_is_capped`), one behavior per
  test, and no prints: a value a test would print belongs in an assertion.
- Prefer `parametrize` over near-identical tests.
- The mutation run is a weekly diagnostic (`mutation.yml`), not a merge gate.
- Never `git add -A` while `run_mutants.py` is running. It edits source files in place, and a
  planted defect committed by accident reads like a feature.
