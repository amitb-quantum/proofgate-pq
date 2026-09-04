import pytest

from proofgate.local import bell_experiment
from proofgate.models import Gate
from proofgate.simulator import StatevectorSimulator


@pytest.mark.parametrize(
    "gates,expected",
    [
        ([Gate(op="X", qubits=[0])], {"01": 1024}),
        ([Gate(op="H", qubits=[0]), Gate(op="H", qubits=[0])], {"00": 1024}),
        (
            [Gate(op="H", qubits=[0]), Gate(op="Z", qubits=[0]), Gate(op="H", qubits=[0])],
            {"01": 1024},
        ),
        ([Gate(op="X", qubits=[0]), Gate(op="CX", qubits=[0, 1])], {"11": 1024}),
    ],
)
def test_known_circuits(gates, expected):
    spec = bell_experiment().model_copy(update={"gates": gates})
    assert StatevectorSimulator().run(spec) == expected


def test_bell_normalization_and_repeatability():
    simulator = StatevectorSimulator()
    first = simulator.run(bell_experiment())
    assert first == simulator.run(bell_experiment())
    assert sum(first.values()) == 1024
    assert set(first) == {"00", "11"}
