import pytest

from proofgate.attacks import material


@pytest.fixture
def cluster(tmp_path):
    root = tmp_path / "cluster"
    trust, request, receipt = material(root)
    return root, trust, request, receipt
