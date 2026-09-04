from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=96, pattern=r"^[a-zA-Z0-9_.:-]+$")]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{96}$")]
Nonce = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
Time = Annotated[int, Field(ge=0, le=2**53 - 1)]
Suite = Literal["ed25519-v1", "mldsa65-v1", "ed25519-mldsa65-v1"]
Disposition = Literal["ALLOW", "DENY", "HUMAN_VERIFY", "UNKNOWN", "ERROR"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    @model_validator(mode="before")
    @classmethod
    def exact_schema_version(cls, value: Any) -> Any:
        # Python's True == 1 would otherwise pass pydantic's Literal[1] check.
        if isinstance(value, dict) and "schema_version" in value:
            if type(value["schema_version"]) is not int:
                raise ValueError("schema_version must be an integer")
        return value


class Gate(Model):
    op: Literal["H", "X", "Z", "CX"]
    qubits: Annotated[list[int], Field(min_length=1, max_length=2)]


class Experiment(Model):
    schema_version: Literal[1]
    backend: Literal["builtin-statevector-v1"]
    qubits: Annotated[int, Field(ge=1, le=8)]
    gates: Annotated[list[Gate], Field(min_length=1, max_length=256)]
    shots: Annotated[int, Field(ge=1, le=4096)]
    seed: Annotated[int, Field(ge=0, le=2**32 - 1)]


class AerGate(Model):
    op: Literal["H", "X", "Z", "CX", "T"]
    qubits: Annotated[list[int], Field(min_length=1, max_length=2)]


class AerExperiment(Model):
    schema_version: Literal[2]
    backend: Literal["aer-statevector-cpu-v1", "aer-statevector-gpu-v1"]
    qubits: Annotated[int, Field(ge=1, le=26)]
    gates: Annotated[list[AerGate], Field(min_length=1, max_length=2048)]
    shots: Annotated[int, Field(ge=1, le=4096)]
    seed: Annotated[int, Field(ge=0, le=2**32 - 1)]


class Parameters(Model):
    experiment: Annotated[Experiment | AerExperiment, Field(discriminator="schema_version")]
    frozen_digest: Hash


class Context(Model):
    environment: Identifier
    project: Identifier


class PolicyRef(Model):
    id: Identifier
    version: Annotated[int, Field(ge=1)]


class Intent(Model):
    schema_version: Literal[1]
    action_type: Literal["quantum.run"]
    subject: Identifier
    target: Identifier
    audience: Identifier
    parameters: Parameters
    context: Context
    nonce: Nonce
    created_at: Time
    expires_at: Time
    policy: PolicyRef
    required_suite: Suite


class SignedIntent(Model):
    intent: Intent
    signatures: dict[str, str]


class PolicyFields(Model):
    reference: PolicyRef
    suite: Suite
    audience: Identifier
    target: Identifier
    environment: Identifier
    project: Identifier
    subjects: Annotated[list[Identifier], Field(min_length=1, max_length=32)]
    verifier_ids: Annotated[list[Identifier], Field(min_length=1, max_length=16)]
    quorum: Annotated[int, Field(ge=1, le=16)]
    max_qubits: Annotated[int, Field(ge=1, le=8)]
    max_shots: Annotated[int, Field(ge=1, le=4096)]
    human_above_shots: Annotated[int, Field(ge=1, le=4096)]
    max_intent_ttl: Annotated[int, Field(ge=1, le=3600)]
    receipt_ttl: Annotated[int, Field(ge=1, le=600)]


class Policy(PolicyFields):
    schema_version: Literal[1]


class AerPolicy(PolicyFields):
    schema_version: Literal[2]
    max_qubits: Annotated[int, Field(ge=1, le=26)]
    backend: Literal["aer-statevector-cpu-v1", "aer-statevector-gpu-v1"]


class TrustBundle(Model):
    schema_version: Literal[1]
    policy: Annotated[Policy | AerPolicy, Field(discriminator="schema_version")]
    verifiers: dict[str, dict[str, str]]
    requesters: dict[str, dict[str, str]]
    executor_id: Identifier
    executor_keys: dict[str, str]


class KeyFile(Model):
    schema_version: Literal[1]
    identity: Identifier
    suite: Suite
    private_keys: dict[str, str]


class Header(Model):
    schema_version: Literal[1]
    action_digest: Hash
    policy: PolicyRef
    policy_digest: Hash
    suite: Suite
    audience: Identifier
    verifier_set: Annotated[list[Identifier], Field(min_length=1, max_length=16)]
    quorum: Annotated[int, Field(ge=1, le=16)]
    issued_at: Time
    expires_at: Time
    receipt_id: Nonce


class AttestationBody(Model):
    header: Header
    verifier_id: Identifier
    disposition: Disposition
    predicates: dict[str, bool]


class Attestation(Model):
    body: AttestationBody
    signatures: dict[str, str]


class Receipt(Model):
    header: Header
    disposition: Disposition
    attestations: Annotated[list[Attestation], Field(max_length=16)]


class ResultBody(Model):
    schema_version: Literal[1]
    executor_id: Identifier
    suite: Suite
    audience: Identifier
    action_digest: Hash
    frozen_digest: Hash
    receipt_digest: Hash
    receipt_id: Nonce
    backend: Literal["builtin-statevector-v1", "aer-statevector-cpu-v1", "aer-statevector-gpu-v1"]
    executed_at: Time
    counts: dict[str, int]


class ResultRecord(Model):
    body: ResultBody
    signatures: dict[str, str]


class NodeRequest(Model):
    request: SignedIntent
    header: Header
