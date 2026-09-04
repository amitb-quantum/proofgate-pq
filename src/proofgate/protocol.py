"""Receipt verification uses public trust anchors; no coordinator authority."""

import secrets

from . import crypto
from .canonical import canonical, digest, parse
from .errors import require
from .models import (
    Attestation,
    AttestationBody,
    Disposition,
    Header,
    KeyFile,
    Receipt,
    SignedIntent,
    TrustBundle,
)
from .policy import evaluate


def trust_snapshot(trust: TrustBundle) -> TrustBundle:
    trust = parse(TrustBundle, canonical(trust))
    policy = trust.policy
    ids = policy.verifier_ids
    require(ids == sorted(set(ids)), "TRUST_VERIFIER_IDENTITIES")
    require(policy.quorum <= len(ids), "TRUST_QUORUM")
    require(set(trust.verifiers) == set(ids), "TRUST_VERIFIER_IDENTITIES")
    require(set(trust.requesters) == set(policy.subjects), "TRUST_REQUESTERS")
    require(policy.human_above_shots <= policy.max_shots, "TRUST_LIMITS")
    require(policy.receipt_ttl <= policy.max_intent_ttl, "TRUST_LIMITS")
    # A renamed shared signing key must never represent independent identities/roles.
    seen: set[tuple[str, str]] = set()
    for keys in [*trust.verifiers.values(), *trust.requesters.values(), trust.executor_keys]:
        crypto.check_public(policy.suite, keys)
        for algorithm, key in keys.items():
            require((algorithm, key) not in seen, "TRUST_DUPLICATE_KEY")
            seen.add((algorithm, key))
    return trust


def validate_request(request: SignedIntent, trust: TrustBundle, now: int) -> None:
    intent, policy = request.intent, trust.policy
    require(intent.required_suite == policy.suite, "SUITE_MISMATCH")
    require(intent.policy == policy.reference, "POLICY_MISMATCH")
    require(intent.audience == policy.audience, "AUDIENCE_MISMATCH")
    require(intent.created_at <= now, "INTENT_FUTURE")
    require(now < intent.expires_at, "INTENT_EXPIRED")
    require(0 < intent.expires_at - intent.created_at <= policy.max_intent_ttl, "INTENT_TTL")
    require(intent.subject in trust.requesters, "REQUESTER_UNKNOWN")
    crypto.verify(
        policy.suite,
        trust.requesters[intent.subject],
        request.signatures,
        crypto.message("intent", policy.suite, intent.subject, intent),
    )


def new_header(request: SignedIntent, trust: TrustBundle, now: int) -> Header:
    validate_request(request, trust, now)
    return Header(
        schema_version=1,
        action_digest=digest("intent", request.intent),
        policy=trust.policy.reference,
        policy_digest=digest("policy", trust.policy),
        suite=trust.policy.suite,
        audience=trust.policy.audience,
        verifier_set=trust.policy.verifier_ids.copy(),
        quorum=trust.policy.quorum,
        issued_at=now,
        expires_at=min(request.intent.expires_at, now + trust.policy.receipt_ttl),
        receipt_id=secrets.token_hex(16),
    )


def validate_header(header: Header, request: SignedIntent, trust: TrustBundle, now: int) -> None:
    validate_request(request, trust, now)
    policy = trust.policy
    require(header.suite == policy.suite, "SUITE_MISMATCH")
    require(header.policy == policy.reference, "POLICY_MISMATCH")
    require(header.policy_digest == digest("policy", policy), "POLICY_DIGEST_MISMATCH")
    require(header.action_digest == digest("intent", request.intent), "ACTION_MISMATCH")
    require(header.audience == policy.audience, "AUDIENCE_MISMATCH")
    require(header.verifier_set == policy.verifier_ids, "VERIFIER_SET_MISMATCH")
    require(header.quorum == policy.quorum, "QUORUM_MISMATCH")
    require(request.intent.created_at <= header.issued_at <= now, "RECEIPT_FUTURE")
    require(now < header.expires_at <= request.intent.expires_at, "RECEIPT_EXPIRED")
    require(0 < header.expires_at - header.issued_at <= policy.receipt_ttl, "RECEIPT_TTL")


def attest(
    request: SignedIntent, header: Header, trust: TrustBundle, key: KeyFile, now: int
) -> Attestation:
    validate_header(header, request, trust, now)
    require(key.suite == trust.policy.suite, "SUITE_MISMATCH")
    require(key.identity in trust.verifiers, "VERIFIER_UNKNOWN")
    disposition, predicates = evaluate(request.intent, trust.policy)
    body = AttestationBody(
        header=header, verifier_id=key.identity, disposition=disposition, predicates=predicates
    )
    signatures = crypto.sign(
        key.suite, key.private_keys, crypto.message("attestation", key.suite, key.identity, body)
    )
    # Detect misprovisioned private keys before emitting apparently authenticated evidence.
    crypto.verify(
        key.suite,
        trust.verifiers[key.identity],
        signatures,
        crypto.message("attestation", key.suite, key.identity, body),
    )
    return Attestation(body=body, signatures=signatures)


def summarize(attestations: list[Attestation], quorum: int) -> Disposition:
    decisions = [a.body.disposition for a in attestations]
    if decisions.count("ALLOW") >= quorum:
        return "ALLOW"
    if "DENY" in decisions:
        return "DENY"
    if "HUMAN_VERIFY" in decisions:
        return "HUMAN_VERIFY"
    if "ERROR" in decisions:
        return "ERROR"
    return "UNKNOWN"


def inspect_receipt(
    request: SignedIntent, receipt: Receipt, trust: TrustBundle, now: int
) -> Disposition:
    """Validate evidence, including negative decisions; does not consume replay state."""
    validate_header(receipt.header, request, trust, now)
    expected_disposition, expected_predicates = evaluate(request.intent, trust.policy)
    seen: set[str] = set()
    for attestation in receipt.attestations:
        body = attestation.body
        require(body.verifier_id not in seen, "VERIFIER_DUPLICATE")
        seen.add(body.verifier_id)
        require(body.verifier_id in trust.verifiers, "VERIFIER_UNKNOWN")
        require(body.header == receipt.header, "ATTESTATION_HEADER_MISMATCH")
        crypto.verify(
            trust.policy.suite,
            trust.verifiers[body.verifier_id],
            attestation.signatures,
            crypto.message("attestation", trust.policy.suite, body.verifier_id, body),
        )
        require(body.predicates == expected_predicates, "EVIDENCE_MISMATCH")
        require(body.disposition == expected_disposition, "DECISION_MISMATCH")
    calculated = summarize(receipt.attestations, trust.policy.quorum)
    require(receipt.disposition == calculated, "DISPOSITION_MISMATCH")
    return calculated


def verify_receipt(
    request_data: bytes, receipt_data: bytes, trust: TrustBundle, now: int
) -> tuple[SignedIntent, Receipt]:
    """Public authorization boundary. Strict fresh snapshots; success means ALLOW only."""
    trusted = trust_snapshot(trust)
    request = parse(SignedIntent, request_data)
    receipt = parse(Receipt, receipt_data)
    disposition = inspect_receipt(request, receipt, trusted, now)
    require(disposition == "ALLOW", "NOT_ALLOW")
    require(evaluate(request.intent, trusted.policy)[0] == "ALLOW", "POLICY_NOT_ALLOW")
    return request, receipt


def assemble(
    request: SignedIntent,
    header: Header,
    attestations: list[Attestation],
    trust: TrustBundle,
    now: int,
) -> Receipt:
    receipt = Receipt(
        header=header,
        disposition=summarize(attestations, trust.policy.quorum),
        attestations=sorted(attestations, key=lambda a: a.body.verifier_id),
    )
    inspect_receipt(request, receipt, trust, now)
    return receipt
