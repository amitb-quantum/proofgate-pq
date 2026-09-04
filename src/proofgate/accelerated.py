"""Versioned, protected non-Clifford quantum workloads; no cloud/provider credentials."""

import json
import random
import time
from pathlib import Path
from typing import Any, Literal

from .aer import AER_CPU, AER_GPU, AerAdapter
from .canonical import canonical, parse, write
from .errors import GateError, require
from .executor import ProtectedExecutor, ReplayStore, verify_result
from .local import authorize_processes, freeze, load_key, provision, sign_intent
from .models import AerExperiment, AerGate, AerPolicy, PolicyRef, TrustBundle


def workload(
    qubits: int = 24, layers: int = 8, device: Literal["CPU", "GPU"] = "GPU"
) -> AerExperiment:
    require(2 <= qubits <= 26 and 1 <= layers <= 20, "WORKLOAD_LIMIT")
    rng = random.Random(731)
    gates = []
    for _ in range(layers):
        for q in range(qubits):
            gates.extend([AerGate(op="H", qubits=[q]), AerGate(op="T", qubits=[q])])
        order = list(range(qubits))
        rng.shuffle(order)
        for q in range(qubits - 1):
            gates.append(AerGate(op="CX", qubits=[order[q], order[q + 1]]))
    return AerExperiment(
        schema_version=2,
        backend=AER_GPU if device == "GPU" else AER_CPU,
        qubits=qubits,
        gates=gates,
        shots=1024,
        seed=7,
    )


def provision_accelerated(
    root: Path, device: Literal["CPU", "GPU"] = "GPU", quorum: int = 3
) -> TrustBundle:
    legacy = provision(root, quorum=quorum)
    fields = legacy.policy.model_dump()
    fields.update(
        schema_version=2,
        reference=PolicyRef(id="quantum-aer", version=2).model_dump(),
        backend=AER_GPU if device == "GPU" else AER_CPU,
        max_qubits=26,
    )
    policy = parse(AerPolicy, canonical(fields))
    trust = TrustBundle(
        schema_version=1,
        policy=policy,
        verifiers=legacy.verifiers,
        requesters=legacy.requesters,
        executor_id=legacy.executor_id,
        executor_keys=legacy.executor_keys,
    )
    write(root / "trust.json", trust)
    return trust


def accelerated_demo(
    root: Path, qubits: int = 24, layers: int = 8, device: Literal["CPU", "GPU"] = "GPU"
) -> dict[str, Any]:
    adapter = AerAdapter(device)  # Availability preflight; never fall back.
    trust = provision_accelerated(root, device)
    spec = workload(qubits, layers, device)
    request = sign_intent(freeze(spec, trust), load_key(root, "scientist"))
    write(root / "experiment.json", spec)
    write(root / "intent.json", request.intent)
    write(root / "request.json", request)
    receipt, nodes = authorize_processes(root, request)
    write(root / "receipt.json", receipt)
    executor = ProtectedExecutor(
        trust, load_key(root, "executor"), ReplayStore(root / "replay.sqlite"), adapter
    )
    changed = request.model_dump()
    changed["intent"]["parameters"]["experiment"]["gates"][0]["op"] = "X"
    try:
        executor.execute(canonical(changed), canonical(receipt))
        raise AssertionError("Changed circuit executed")
    except GateError as exc:
        mutation = exc.code
    start = time.perf_counter_ns()
    record = executor.execute(canonical(request), canonical(receipt))
    elapsed = (time.perf_counter_ns() - start) / 1e6
    write(root / "result.json", record)
    verify_result(canonical(record), canonical(request), canonical(receipt), trust)
    try:
        executor.execute(canonical(request), canonical(receipt))
        raise AssertionError("Replayed receipt executed")
    except GateError as exc:
        require(exc.code == "REPLAY", "DEMO_REPLAY_CHECK_FAILED")
    summary = {
        "device": device,
        "qubits": qubits,
        "layers": layers,
        "gates": len(spec.gates),
        "shots": spec.shots,
        "nodes": nodes,
        "disposition": receipt.disposition,
        "mutation": mutation,
        "replay": "REPLAY",
        "result_attestation": "VALID",
        "observed_outcomes": len(record.body.counts),
        "total_counts": sum(record.body.counts.values()),
        "protected_execution_ms": elapsed,
        "adapter": adapter.last_metrics,
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
