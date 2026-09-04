import os

import pytest

from proofgate.canonical import canonical, parse
from proofgate.errors import GateError
from proofgate.models import AerExperiment, Experiment

gpu = pytest.mark.skipif(
    os.environ.get("PROOFGATE_GPU_TESTS") != "1", reason="Explicit GPU integration opt-in required"
)


def test_legacy_schema_cannot_select_gpu():
    from proofgate.local import bell_experiment

    data = bell_experiment().model_dump()
    data["backend"] = "aer-statevector-gpu-v1"
    with pytest.raises(GateError, match="SCHEMA_INVALID"):
        parse(Experiment, canonical(data))


def test_legacy_schema_cannot_add_nonclifford_gate():
    from proofgate.local import bell_experiment

    data = bell_experiment().model_dump()
    data["gates"][0]["op"] = "T"
    with pytest.raises(GateError, match="SCHEMA_INVALID"):
        parse(Experiment, canonical(data))


@gpu
@pytest.mark.parametrize("device", ["CPU", "GPU"])
def test_protected_accelerated_demo(tmp_path, device):
    from proofgate.accelerated import accelerated_demo

    report = accelerated_demo(tmp_path / device, qubits=8, layers=3, device=device)
    assert report["adapter"]["metadata"]["device"] == device
    assert report["mutation"] == "SIGNATURE_INVALID"
    assert report["replay"] == "REPLAY"
    assert report["total_counts"] == 1024
    assert report["result_attestation"] == "VALID"


@gpu
def test_cpu_gpu_complex_state_equivalence():
    import numpy as np

    from proofgate.accelerated import workload
    from proofgate.aer import AerAdapter, circuit_for

    circuit = circuit_for(workload(8, 3)).remove_final_measurements(inplace=False)
    circuit.save_statevector()
    states = [
        np.asarray(AerAdapter(device).backend.run(circuit).result().get_statevector())
        for device in ["CPU", "GPU"]
    ]
    assert np.allclose(*states, rtol=1e-12, atol=1e-12)


@gpu
def test_gpu_failure_never_calls_cpu_backend(monkeypatch):
    from proofgate.accelerated import workload
    from proofgate.aer import AerAdapter

    adapter = AerAdapter("GPU")
    calls = []

    def fail(*args, **kwargs):
        calls.append("GPU")
        raise RuntimeError("GPU unavailable")

    monkeypatch.setattr(adapter.backend, "run", fail)
    with pytest.raises(GateError, match="SIMULATOR_FAILED"):
        adapter.run(workload(2, 1))
    assert calls == ["GPU"]


@gpu
def test_provider_cpu_fallback_metadata_rejected(monkeypatch):
    from types import SimpleNamespace

    from proofgate.accelerated import workload
    from proofgate.aer import AerAdapter

    adapter = AerAdapter("GPU")
    result = SimpleNamespace(
        success=True, results=[SimpleNamespace(metadata={"device": "CPU", "method": "statevector"})]
    )
    monkeypatch.setattr(
        adapter.backend, "run", lambda *args, **kwargs: SimpleNamespace(result=lambda: result)
    )
    with pytest.raises(GateError, match="SIMULATOR_DEVICE_MISMATCH"):
        adapter.run(workload(2, 1))


def test_accelerated_resource_bound():
    data = {
        "schema_version": 2,
        "backend": "aer-statevector-gpu-v1",
        "qubits": 27,
        "gates": [{"op": "H", "qubits": [0]}],
        "shots": 1024,
        "seed": 1,
    }
    with pytest.raises(GateError, match="SCHEMA_INVALID"):
        parse(AerExperiment, canonical(data))
