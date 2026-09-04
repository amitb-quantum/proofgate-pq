import time
from pathlib import Path

from .canonical import canonical, decode, digest, write
from .errors import GateError, require
from .executor import ProtectedExecutor, ReplayStore, verify_result
from .local import (
    authorize_processes,
    bell_experiment,
    freeze,
    load_key,
    provision,
    sign_intent,
)
from .models import Suite


def quantum_demo(root: Path, suite: Suite = "ed25519-mldsa65-v1", quorum: int = 2) -> dict:
    trust = provision(root, suite, quorum)
    intent = freeze(bell_experiment(), trust)
    request = sign_intent(intent, load_key(root, "scientist"))
    write(root / "intent.json", intent)
    write(root / "request.json", request)
    receipt, nodes = authorize_processes(root, request)
    write(root / "receipt.json", receipt)
    executor = ProtectedExecutor(
        trust, load_key(root, "executor"), ReplayStore(root / "replay.sqlite")
    )
    altered = decode(canonical(request))
    altered["intent"]["parameters"]["experiment"]["shots"] += 1
    try:
        executor.execute(canonical(altered), canonical(receipt))
        raise AssertionError("Altered experiment was executed")
    except GateError as exc:
        mutation_code = exc.code
    result = executor.execute(canonical(request), canonical(receipt))
    write(root / "result.json", result)
    verify_result(canonical(result), canonical(request), canonical(receipt), trust)
    # New executor instance uses the same durable store to exercise restart persistence.
    restarted = ProtectedExecutor(
        trust, load_key(root, "executor"), ReplayStore(root / "replay.sqlite")
    )
    try:
        restarted.execute(canonical(request), canonical(receipt))
        raise AssertionError("Replay was executed")
    except GateError as exc:
        require(exc.code == "REPLAY", "DEMO_REPLAY_CHECK_FAILED")
        replay_code = exc.code
    require(set(result.body.counts) <= {"00", "11"}, "BELL_CORRELATION_FAILED")
    summary = {
        "suite": suite,
        "quorum": quorum,
        "nodes": nodes,
        "frozen_digest": intent.parameters.frozen_digest,
        "action_digest": digest("intent", intent),
        "disposition": receipt.disposition,
        "counts": result.body.counts,
        "altered_experiment": mutation_code,
        "replay_after_restart": replay_code,
        "result_attestation": "VALID",
        "completed_at": int(time.time()),
    }
    write(root / "summary.json", summary)
    return summary
