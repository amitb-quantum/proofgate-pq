"""One deterministic auditable predicate evaluator, shared by nodes and executors."""

from .canonical import digest
from .models import AerPolicy, Disposition, Intent, Policy


def evaluate(intent: Intent, policy: Policy | AerPolicy) -> tuple[Disposition, dict[str, bool]]:
    spec = intent.parameters.experiment
    gates_valid = all(
        len(g.qubits) == (2 if g.op == "CX" else 1)
        and len(set(g.qubits)) == len(g.qubits)
        and all(type(q) is int and 0 <= q < spec.qubits for q in g.qubits)
        for g in spec.gates
    )
    predicates = {
        "requester_allowed": intent.subject in policy.subjects,
        "target_allowed": intent.target == policy.target,
        "audience_matches": intent.audience == policy.audience,
        "context_allowed": (
            intent.context.environment == policy.environment
            and intent.context.project == policy.project
        ),
        "frozen_spec_matches": intent.parameters.frozen_digest == digest("experiment", spec),
        "resources_within_limits": spec.qubits <= policy.max_qubits
        and spec.shots <= policy.max_shots,
        "circuit_well_formed": gates_valid,
        "backend_supported": (
            spec.schema_version == policy.schema_version
            and spec.backend
            == (policy.backend if isinstance(policy, AerPolicy) else "builtin-statevector-v1")
        ),
        "automatic_review_limit": spec.shots <= policy.human_above_shots,
    }
    if not all(v for k, v in predicates.items() if k != "automatic_review_limit"):
        return "DENY", predicates
    if not predicates["automatic_review_limit"]:
        return "HUMAN_VERIFY", predicates
    return "ALLOW", predicates
