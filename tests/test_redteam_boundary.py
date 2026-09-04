import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from proofgate.attacks import issue
from proofgate.canonical import canonical, digest, parse, read, write
from proofgate.errors import GateError
from proofgate.executor import ProtectedExecutor, ReplayStore, verify_result
from proofgate.local import freeze, load_key, load_trust, sign_intent
from proofgate.models import Intent
from proofgate.protocol import verify_receipt
from proofgate.simulator import StatevectorSimulator


def test_concurrent_distinct_receipts_cannot_evade_intent_replay(cluster):
    root, trust, request, _ = cluster
    write(root / "request.json", request)
    paths = []
    for n in range(6):
        path = root / f"receipt-{n}.json"
        write(path, issue(root, trust, request))
        paths.append(path)
    child = (
        "import sys,json; from pathlib import Path; "
        "from proofgate.local import load_trust,load_key; "
        "from proofgate.canonical import read; "
        "from proofgate.executor import ProtectedExecutor,ReplayStore; "
        "from proofgate.errors import GateError; "
        "r=Path(sys.argv[1]); "
        "e=ProtectedExecutor(load_trust(r),load_key(r,'executor'),ReplayStore(r/'race.sqlite')); "
        "\ntry: e.execute(read(r/'request.json'),read(Path(sys.argv[2]))); print('EXECUTED')"
        "\nexcept GateError as x: print(x.code)"
    )

    def call(path):
        p = subprocess.run(
            [sys.executable, "-c", child, str(root), str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return p.stdout.strip()

    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(call, paths))
    assert sorted(outcomes) == sorted(["EXECUTED"] + ["REPLAY"] * 5)


def test_gpu_receipt_cannot_select_cpu_adapter(tmp_path):
    from proofgate.accelerated import provision_accelerated, workload

    root = tmp_path / "gpu"
    trust = provision_accelerated(root)
    request = sign_intent(freeze(workload(8, 2), trust), load_key(root, "scientist"))
    receipt = issue(root, trust, request)
    database = root / "replay.sqlite"
    executor = ProtectedExecutor(
        trust, load_key(root, "executor"), ReplayStore(database), StatevectorSimulator()
    )
    with pytest.raises(GateError, match="BACKEND_MISMATCH"):
        executor.execute(canonical(request), canonical(receipt))
    assert not database.exists()


def test_requester_resigned_device_swap_cannot_reuse_receipt(tmp_path):
    from proofgate.accelerated import provision_accelerated, workload

    root = tmp_path / "gpu"
    trust = provision_accelerated(root)
    request = sign_intent(freeze(workload(8, 2), trust), load_key(root, "scientist"))
    receipt = issue(root, trust, request)
    raw = request.intent.model_dump()
    raw["parameters"]["experiment"]["backend"] = "aer-statevector-cpu-v1"
    raw["parameters"]["frozen_digest"] = digest("experiment", raw["parameters"]["experiment"])
    changed = sign_intent(parse(Intent, canonical(raw)), load_key(root, "scientist"))
    with pytest.raises(GateError, match="ACTION_MISMATCH"):
        verify_receipt(canonical(changed), canonical(receipt), trust, int(time.time()))


def test_historical_v1_provenance_survives_v2_extension():
    root = Path(__file__).parents[1] / "reports" / "quantum"
    verify_result(
        read(root / "result.json"),
        read(root / "request.json"),
        read(root / "receipt.json"),
        load_trust(root),
    )


@pytest.mark.parametrize("change", ["extra_receipt_field", "too_many_votes", "boolean_shots"])
def test_additional_schema_confusion(cluster, change):
    _, trust, request, receipt = cluster
    q, r = request.model_dump(), receipt.model_dump()
    if change == "extra_receipt_field":
        r["skip_signature_verification"] = True
    elif change == "too_many_votes":
        r["attestations"] = r["attestations"] * 6
    else:
        q["intent"]["parameters"]["experiment"]["shots"] = True
    with pytest.raises(GateError, match="SCHEMA_INVALID"):
        verify_receipt(canonical(q), canonical(r), trust, int(time.time()))
