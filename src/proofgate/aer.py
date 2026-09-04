"""Optional maintained Aer backend. Device selection is part of the signed revision."""

import time
from typing import Any, Final, Literal, cast

from .errors import GateError, require
from .models import AerExperiment, Experiment

AER_CPU: Final = "aer-statevector-cpu-v1"
AER_GPU: Final = "aer-statevector-gpu-v1"
THREADS = 8


def make_backend(device: Literal["CPU", "GPU"]) -> Any:
    try:
        from qiskit_aer import AerSimulator

        backend = AerSimulator(
            method="statevector",
            device=device,
            precision="double",
            max_parallel_threads=THREADS,
            max_parallel_experiments=1,
            fusion_enable=True,
            enable_truncation=False,
        )
        require(device in backend.available_devices(), "GPU_UNAVAILABLE")
        return backend
    except GateError:
        raise
    except Exception as exc:
        raise GateError("SIMULATOR_PROVIDER_UNAVAILABLE") from exc


def circuit_for(spec: AerExperiment) -> Any:
    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(spec.qubits)
    for gate in spec.gates:
        getattr(circuit, gate.op.lower())(*gate.qubits)
    circuit.measure_all()
    return circuit


class AerAdapter:
    def __init__(self, device: Literal["CPU", "GPU"]) -> None:
        self.device = device
        self.revision = AER_GPU if device == "GPU" else AER_CPU
        self.backend = make_backend(device)
        self.last_metrics: dict[str, Any] = {}

    def run(self, spec: Experiment | AerExperiment) -> dict[str, int]:
        require(isinstance(spec, AerExperiment), "BACKEND_MISMATCH")
        require(spec.backend == self.revision, "BACKEND_MISMATCH")
        try:
            start = time.perf_counter_ns()
            circuit = circuit_for(cast(AerExperiment, spec))
            built = time.perf_counter_ns()
            result = self.backend.run(circuit, shots=spec.shots, seed_simulator=spec.seed).result()
            completed = time.perf_counter_ns()
            require(result.success and len(result.results) == 1, "SIMULATOR_FAILED")
            metadata = result.results[0].metadata
            require(metadata.get("device") == self.device, "SIMULATOR_DEVICE_MISMATCH")
            require(metadata.get("method") == "statevector", "SIMULATOR_METHOD_MISMATCH")
            self.last_metrics = {
                "circuit_build_ms": (built - start) / 1e6,
                "execution_ms": (completed - built) / 1e6,
                "total_ms": (completed - start) / 1e6,
                "metadata": metadata,
            }
            return {str(k): int(v) for k, v in sorted(result.get_counts().items())}
        except GateError:
            raise
        except Exception as exc:
            raise GateError("SIMULATOR_FAILED") from exc
