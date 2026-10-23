"""Score solutions to the reschedule_weekly prompt.

    python prompt_comparison/evaluate.py solutions/claude_opus.py solutions/claude_haiku.py

Add any other model's answer as a new file under solutions/ (a module that defines reschedule_weekly) and pass it too.
Each solution is run against the hand-computed cases in cases.py, some purity checks, and 2,000 seeded random inputs
compared with reference.py. Nothing here is imported by the app or the pytest suite.
"""

import copy
import importlib.util
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cases import CASES, M, d  # noqa: E402
from reference import reschedule_weekly as reference  # noqa: E402


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reschedule_weekly


def run(function, kwargs):
    """Return ("ok", value) or ("error", exception)."""
    try:
        return "ok", function(**copy.deepcopy(kwargs))
    except Exception as err:  # noqa: BLE001 - any failure is a result to report
        return "error", err


def check_case(function, kwargs, expected):
    kind, got = run(function, kwargs)
    if expected is ValueError:
        return kind == "error" and isinstance(got, ValueError), got
    return kind == "ok" and got == expected, got


def purity_checks(function):
    """Return (name, passed) pairs for behaviour that is not a single input/output pair."""
    results = []
    busy = [(d(7), "09:00", 30), (d(7), "08:00", 30)]
    before = copy.deepcopy(busy)
    kwargs = dict(due_date=M, time="08:00", duration=30, completed_on=M, busy=busy)
    first = function(**kwargs)
    results.append(("does not mutate the busy list", busy == before))
    results.append(("same answer when called twice", function(**kwargs) == first))
    results.append(
        ("returns a (date, str) tuple, not a datetime",
         isinstance(first, tuple) and len(first) == 2 and type(first[0]) is date and isinstance(first[1], str))
    )
    results.append(("accepts busy blocks as lists as well as tuples", function(M, "08:00", 30, M, [[d(7), "08:00", 30]]) == (d(7), "08:30")))
    results.append(("max_weeks is optional", function(M, "08:00", 30, M, []) == (d(7), "08:00")))
    return results


def random_inputs(count=2000, seed=12345):
    rng = random.Random(seed)
    for _ in range(count):
        due = date(2026, 1, 1) + timedelta(days=rng.randrange(0, 1500))  # crosses the 2028 leap year
        completed = due + timedelta(days=rng.randrange(-15, 80))
        duration = rng.choice([1, 5, 15, 30, 45, 60, 90, 180, 600, 1000, 1440])
        time = f"{rng.randrange(24):02d}:{rng.randrange(60):02d}"
        anchor = max(due, completed)
        weeks = rng.choice([1, 2, 3, 8, 8, 8])
        days = [anchor + timedelta(days=((due.weekday() - anchor.weekday()) % 7 or 7) + 7 * k) for k in range(weeks + 1)]
        busy = []
        for _ in range(rng.randrange(0, 9)):
            day = rng.choice(days + [anchor, anchor - timedelta(days=1)])
            minutes = rng.choice([1, 15, 30, 60, 120, 300, 800, 1440, 2000])
            busy.append((day, f"{rng.randrange(24):02d}:{rng.randrange(60):02d}", minutes))
        yield dict(due_date=due, time=time, duration=duration, completed_on=completed, busy=busy, max_weeks=weeks)


def evaluate(path: Path):
    function = load(path)
    report = {"file": path.name, "categories": {}, "failures": [], "purity": [], "random": {}}
    for category, name, kwargs, expected in CASES:
        passed, got = check_case(function, kwargs, expected)
        row = report["categories"].setdefault(category, [0, 0])
        row[0] += passed
        row[1] += 1
        if not passed:
            report["failures"].append((category, name, expected, got))
    report["purity"] = []
    try:
        report["purity"] = purity_checks(function)
    except Exception as err:  # noqa: BLE001
        report["purity"] = [(f"purity checks crashed: {err!r}", False)]
    matched = total = 0
    mismatches = []
    for kwargs in random_inputs():
        total += 1
        kind, got = run(function, kwargs)
        _, want = run(reference, kwargs)
        if kind == "ok" and got == want:
            matched += 1
        elif len(mismatches) < 3:
            mismatches.append((kwargs, want, got))
    report["random"] = {"matched": matched, "total": total, "examples": mismatches}
    return report


def show(report):
    print(f"\n=== {report['file']} ===")
    case_pass = sum(p for p, _ in report["categories"].values())
    case_total = sum(t for _, t in report["categories"].values())
    for category, (passed, total) in report["categories"].items():
        print(f"  {category:<11} {passed:>3}/{total:<3}")
    print(f"  {'cases':<11} {case_pass:>3}/{case_total:<3}")
    pure = sum(1 for _, ok in report["purity"] if ok)
    print(f"  {'purity':<11} {pure:>3}/{len(report['purity']):<3}")
    rnd = report["random"]
    print(f"  {'random':<11} {rnd['matched']:>4}/{rnd['total']:<4} match the reference")
    for category, name, expected, got in report["failures"][:12]:
        print(f"    FAIL [{category}] {name}: expected {expected!r}, got {got!r}")
    if len(report["failures"]) > 12:
        print(f"    ... and {len(report['failures']) - 12} more failing cases")
    for name, ok in report["purity"]:
        if not ok:
            print(f"    FAIL [purity] {name}")
    for kwargs, want, got in rnd["examples"]:
        print(f"    MISMATCH want {want!r}, got {got!r} for {kwargs}")


if __name__ == "__main__":
    paths = [Path(p) for p in sys.argv[1:]] or [HERE / "reference.py"]
    for path in paths:
        show(evaluate(path))
