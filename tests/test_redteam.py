import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def redteam_report(tmp_path_factory):
    spec = importlib.util.spec_from_file_location(
        "redteam", Path(__file__).parents[1] / "scripts/redteam.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run(tmp_path_factory.mktemp("redteam") / "results.json")


@pytest.mark.parametrize("index", range(18))
def test_redteam_reproduction(redteam_report, index):
    finding = redteam_report["findings"][index]
    assert finding["reproduced"], finding
