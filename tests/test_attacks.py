import pytest

from proofgate.attacks import CASES, exercise, material


@pytest.fixture(scope="module", params=["ed25519-v1", "mldsa65-v1", "ed25519-mldsa65-v1"])
def corpus_cluster(request, tmp_path_factory):
    root = tmp_path_factory.mktemp(request.param) / "cluster"
    return (root, *material(root, request.param))


@pytest.mark.parametrize("name,expected", CASES.items())
def test_attack_corpus(name, expected, corpus_cluster, tmp_path):
    root, trust, request, receipt = corpus_cluster
    assert exercise(name, root, trust, request, receipt, tmp_path / "replay.sqlite") == expected
