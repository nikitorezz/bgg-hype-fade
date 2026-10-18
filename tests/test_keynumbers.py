import json
import math

import pytest

from bgg.analysis.keynumbers import REQUIRED, validate
from bgg.config import load_config

CFG = load_config()
PATH = CFG.root / CFG.section("analysis")["results_dir"] / "key_numbers.json"


def _e(v, lo=None, hi=None):
    return {"value": v, "ci_low": lo, "ci_high": hi, "n": 10, "source": "t", "definition": "d"}


def test_validate_flags_missing_nonfinite_and_bad_ci():
    nums = {k: _e(1.0) for k in REQUIRED}
    assert validate(nums) == []
    del nums["change_12"]
    nums["change_24"] = _e(float("nan"))
    nums["change_36"] = _e(1.0, 2.0, 3.0)
    problems = " ".join(validate(nums))
    assert "missing key: change_12" in problems
    assert "change_24: non-finite" in problems
    assert "change_36: value 1.0 outside CI" in problems


@pytest.mark.skipif(not PATH.exists(), reason="run `bgg analysis` first")
def test_real_key_numbers_file_is_complete_and_consistent():
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    nums = payload["numbers"]
    assert validate(nums) == []
    for k, e in nums.items():
        if not isinstance(e["value"], str):
            assert math.isfinite(e["value"]), k
            if e["ci_low"] is not None and e["ci_high"] is not None:
                assert e["ci_low"] - 1e-9 <= e["value"] <= e["ci_high"] + 1e-9, k
        assert e["source"] and e["definition"], k
