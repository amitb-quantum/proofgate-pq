"""Small scientific adapter. It has no network, credentials, or paid provider support."""

import math
import random
from collections import Counter
from typing import Protocol

from .models import AerExperiment, Experiment


class SimulatorAdapter(Protocol):
    revision: str

    def run(self, spec: Experiment | AerExperiment) -> dict[str, int]: ...


class StatevectorSimulator:
    revision = "builtin-statevector-v1"

    def run(self, spec: Experiment | AerExperiment) -> dict[str, int]:
        from .errors import require

        require(isinstance(spec, Experiment), "BACKEND_MISMATCH")
        # Little endian qubit indices; output strings are |q[n-1] ... q[0]>.
        state = [0.0] * (1 << spec.qubits)
        state[0] = 1.0
        for gate in spec.gates:
            bit = 1 << gate.qubits[0]
            if gate.op == "CX":
                target = 1 << gate.qubits[1]
                for index in range(len(state)):
                    if index & bit and not index & target:
                        other = index | target
                        state[index], state[other] = state[other], state[index]
            else:
                for index in range(len(state)):
                    if index & bit:
                        continue
                    other = index | bit
                    a, b = state[index], state[other]
                    if gate.op == "H":
                        state[index], state[other] = (a + b) / math.sqrt(2), (a - b) / math.sqrt(2)
                    elif gate.op == "X":
                        state[index], state[other] = b, a
                    elif gate.op == "Z":
                        state[other] = -b
        rng = random.Random(spec.seed)  # Reproducible simulation sampling, NOT cryptographic RNG.
        samples = rng.choices(range(len(state)), weights=[a * a for a in state], k=spec.shots)
        return dict(sorted(Counter(format(i, f"0{spec.qubits}b") for i in samples).items()))
