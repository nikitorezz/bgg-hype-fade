import json

import pytest

from bgg.config import load_config
from bgg.readme import readme_path, render, render_readme

CFG = load_config()


def test_render_fills_numbers_links_and_conditionals():
    nums = {"a": {"value": -0.365}, "b": {"value": 0.609}}
    tpl = "x {{a|abs:.2f}} y {{b|pct:.0f}}% {{#if repo}}[b]({{@repo}})\n{{/if}}end {{@missing}}"
    assert render(tpl, nums, {"repo": "http://r"}) == "x 0.37 y 61% [b](http://r)\nend "
    assert render(tpl, nums, {"repo": ""}) == "x 0.37 y 61% end "


def test_unknown_key_raises():
    with pytest.raises(KeyError):
        render("{{nope}}", {}, {})


def test_readme_is_not_stale():
    """README.md must equal the rendering of README.template.md from key_numbers.json."""
    assert readme_path(CFG).read_text(encoding="utf-8") == render_readme(CFG), (
        "README.md is stale: run `uv run python scripts/render_readme.py`")


def test_readme_numbers_match_key_numbers():
    nums = json.loads((CFG.root / "reports/results/key_numbers.json").read_text(encoding="utf-8"))[
        "numbers"]
    text = readme_path(CFG).read_text(encoding="utf-8")
    assert f"{abs(nums['change_36']['value']):.2f} points" in text
    assert "{{" not in text and "}}" not in text
