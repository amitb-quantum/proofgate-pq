import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from proofgate.canonical import canonical, write
from proofgate.errors import GateError
from proofgate.executor import ProtectedExecutor, ReplayStore, verify_result
from proofgate.local import load_key
from proofgate.simulator import StatevectorSimulator


class CountingAdapter(StatevectorSimulator):
    def __init__(self):
        self.calls = 0

    def run(self, spec):
        self.calls += 1
        return super().run(spec)


def test_no_receipt_no_effect(cluster, tmp_path):
    root, trust, request, _ = cluster
    adapter = CountingAdapter()
    executor = ProtectedExecutor(
        trust, load_key(root, "executor"), ReplayStore(tmp_path / "replay.sqlite"), adapter
    )
    with pytest.raises(GateError):
        executor.execute(canonical(request), b"{}")
    assert adapter.calls == 0


def test_concurrent_process_replay(cluster):
    root, _, request, receipt = cluster
    write(root / "request.json", request)
    write(root / "receipt.json", receipt)

    def execute(_):
        return subprocess.run(
            [sys.executable, "-m", "proofgate", "--root", str(root), "execute"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(execute, range(6)))
    assert sum(p.returncode == 0 for p in outcomes) == 1
    assert [json.loads(p.stderr)["code"] for p in outcomes if p.returncode] == ["REPLAY"] * 5


def test_failed_adapter_burns_permit(cluster, tmp_path):
    root, trust, request, receipt = cluster

    class FailingAdapter(StatevectorSimulator):
        def run(self, spec):
            raise RuntimeError("private provider error must not leak")

    store = ReplayStore(tmp_path / "replay.sqlite")
    executor = ProtectedExecutor(trust, load_key(root, "executor"), store, FailingAdapter())
    with pytest.raises(GateError, match="EXECUTION_ERROR"):
        executor.execute(canonical(request), canonical(receipt))
    restarted = ProtectedExecutor(trust, load_key(root, "executor"), store)
    with pytest.raises(GateError, match="REPLAY"):
        restarted.execute(canonical(request), canonical(receipt))


def test_store_failure_has_no_effect(cluster, tmp_path):
    root, trust, request, receipt = cluster
    adapter = CountingAdapter()
    executor = ProtectedExecutor(
        trust,
        load_key(root, "executor"),
        ReplayStore(tmp_path / "absent" / "replay.sqlite"),
        adapter,
    )
    with pytest.raises(GateError, match="REPLAY_STORE_ERROR"):
        executor.execute(canonical(request), canonical(receipt))
    assert adapter.calls == 0


def test_expiration_during_reservation_has_no_effect(cluster, tmp_path):
    root, trust, request, receipt = cluster
    adapter = CountingAdapter()
    executor = ProtectedExecutor(
        trust, load_key(root, "executor"), ReplayStore(tmp_path / "replay.sqlite"), adapter
    )
    times = [time.time(), receipt.header.expires_at, receipt.header.expires_at]
    with patch("proofgate.executor.time.time", side_effect=times):
        with pytest.raises(GateError, match="RECEIPT_EXPIRED"):
            executor.execute(canonical(request), canonical(receipt))
    assert adapter.calls == 0


def test_caller_mutation_during_execution_does_not_change_frozen_snapshot(cluster, tmp_path):
    root, trust, request, receipt = cluster

    class MutatingStore(ReplayStore):
        def reserve(self, *args):
            request.intent.parameters.experiment.gates.clear()
            super().reserve(*args)

    before = canonical(request)
    executor = ProtectedExecutor(
        trust, load_key(root, "executor"), MutatingStore(tmp_path / "replay.sqlite")
    )
    result = executor.execute(before, canonical(receipt))
    assert result.body.counts == {"00": 546, "11": 478}
    verify_result(canonical(result), before, canonical(receipt), trust)


def test_historical_result_after_expiry_does_not_grant_execution(cluster, tmp_path):
    root, trust, request, receipt = cluster
    executor = ProtectedExecutor(
        trust, load_key(root, "executor"), ReplayStore(tmp_path / "r.sqlite")
    )
    result = executor.execute(canonical(request), canonical(receipt))
    with patch("proofgate.executor.time.time", return_value=request.intent.expires_at + 100):
        verify_result(canonical(result), canonical(request), canonical(receipt), trust)
        with pytest.raises(GateError, match="INTENT_EXPIRED"):
            executor.execute(canonical(request), canonical(receipt))
