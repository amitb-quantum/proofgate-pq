import time

import pytest

from proofgate.attacks import CASES, exercise, material


# Keep shared receipts and executor/replay checks on one synthetic clock. This
# fixture is local to the in-process corpus; subprocess integration uses real time.
@pytest.fixture(scope="module")
def corpus_clock():
    now = 1_800_000_000
    with pytest.MonkeyPatch.context() as clock:
        clock.setattr(time, "time", lambda: now)
        yield now


@pytest.fixture(scope="module", params=["ed25519-v1", "mldsa65-v1", "ed25519-mldsa65-v1"])
def corpus_cluster(request, tmp_path_factory, corpus_clock):
    root = tmp_path_factory.mktemp(request.param) / "cluster"
    return (root, *material(root, request.param))


@pytest.mark.parametrize("name,expected", CASES.items())
def test_attack_corpus(name, expected, corpus_cluster, tmp_path):
    root, trust, request, receipt = corpus_cluster
    assert exercise(name, root, trust, request, receipt, tmp_path / "replay.sqlite") == expected


@pytest.mark.parametrize(
    "name", ["human_verify_not_approval", "deny_not_approval", "signed_stale_freeze"]
)
def test_reissued_denial_across_second_boundary(
    name, corpus_cluster, corpus_clock, monkeypatch, tmp_path
):
    root, trust, request, receipt = corpus_cluster
    calls = 0

    def crossing_clock():
        nonlocal calls
        calls += 1
        return corpus_clock + (0.999 if calls == 1 else 1.001)

    # Force the old race: exercise captures T, then a replacement freeze/receipt
    # would read T+1. The denial must still reach the precise NOT_ALLOW check.
    monkeypatch.setattr(time, "time", crossing_clock)
    assert exercise(name, root, trust, request, receipt, tmp_path / "race.sqlite") == "NOT_ALLOW"
