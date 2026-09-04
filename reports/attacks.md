# Adversarial corpus

Suite: `ed25519-mldsa65-v1`. 44/44 passed.

| Case | Expected | Observed | Result |
|---|---|---|---|
| valid_authorization | ALLOW | ALLOW | PASS |
| modified_action_payload | SIGNATURE_INVALID | SIGNATURE_INVALID | PASS |
| modified_target | SIGNATURE_INVALID | SIGNATURE_INVALID | PASS |
| modified_receipt_nonce | ATTESTATION_HEADER_MISMATCH | ATTESTATION_HEADER_MISMATCH | PASS |
| wrong_public_key | SIGNATURE_INVALID | SIGNATURE_INVALID | PASS |
| missing_required_signature | SIGNATURE_COMPONENTS | SIGNATURE_COMPONENTS | PASS |
| algorithm_downgrade | SUITE_MISMATCH | SUITE_MISMATCH | PASS |
| expired_receipt | RECEIPT_EXPIRED | RECEIPT_EXPIRED | PASS |
| future_receipt | RECEIPT_FUTURE | RECEIPT_FUTURE | PASS |
| future_intent | INTENT_FUTURE | INTENT_FUTURE | PASS |
| receipt_replay | REPLAY | REPLAY | PASS |
| insufficient_quorum | DISPOSITION_MISMATCH | DISPOSITION_MISMATCH | PASS |
| duplicate_verifier | VERIFIER_DUPLICATE | VERIFIER_DUPLICATE | PASS |
| unknown_verifier | VERIFIER_UNKNOWN | VERIFIER_UNKNOWN | PASS |
| incorrect_policy_version | POLICY_MISMATCH | POLICY_MISMATCH | PASS |
| altered_frozen_experiment | SIGNATURE_INVALID | SIGNATURE_INVALID | PASS |
| malformed_duplicate_json | DUPLICATE_JSON_KEY | DUPLICATE_JSON_KEY | PASS |
| signature_substitution | SIGNATURE_INVALID | SIGNATURE_INVALID | PASS |
| one_malicious_verifier | EVIDENCE_MISMATCH | EVIDENCE_MISMATCH | PASS |
| malicious_only_no_quorum | DISPOSITION_MISMATCH | DISPOSITION_MISMATCH | PASS |
| two_honest_verifiers | ALLOW | ALLOW | PASS |
| policy_changed_same_version | POLICY_DIGEST_MISMATCH | POLICY_DIGEST_MISMATCH | PASS |
| receipt_threshold_downgrade | QUORUM_MISMATCH | QUORUM_MISMATCH | PASS |
| receipt_suite_downgrade | SUITE_MISMATCH | SUITE_MISMATCH | PASS |
| evidence_mutation | SIGNATURE_INVALID | SIGNATURE_INVALID | PASS |
| missing_evidence | SIGNATURE_INVALID | SIGNATURE_INVALID | PASS |
| outer_disposition_mutation | DISPOSITION_MISMATCH | DISPOSITION_MISMATCH | PASS |
| human_verify_not_approval | NOT_ALLOW | NOT_ALLOW | PASS |
| deny_not_approval | NOT_ALLOW | NOT_ALLOW | PASS |
| unknown_not_approval | NOT_ALLOW | NOT_ALLOW | PASS |
| error_not_approval | DECISION_MISMATCH | DECISION_MISMATCH | PASS |
| shared_identity_key | TRUST_DUPLICATE_KEY | TRUST_DUPLICATE_KEY | PASS |
| extra_signature_algorithm | SIGNATURE_COMPONENTS | SIGNATURE_COMPONENTS | PASS |
| request_signature_missing | SIGNATURE_COMPONENTS | SIGNATURE_COMPONENTS | PASS |
| cross_domain_signature | SIGNATURE_INVALID | SIGNATURE_INVALID | PASS |
| audience_swap | AUDIENCE_MISMATCH | AUDIENCE_MISMATCH | PASS |
| extra_intent_field | SCHEMA_INVALID | SCHEMA_INVALID | PASS |
| float_canonical_input | CANONICAL_NUMBER | CANONICAL_NUMBER | PASS |
| boolean_schema_version | SCHEMA_INVALID | SCHEMA_INVALID | PASS |
| result_tampering | SIGNATURE_INVALID | SIGNATURE_INVALID | PASS |
| reissued_intent_replay | REPLAY | REPLAY | PASS |
| noncanonical_base64 | BASE64_INVALID | BASE64_INVALID | PASS |
| expired_intent | INTENT_EXPIRED | INTENT_EXPIRED | PASS |
| signed_stale_freeze | NOT_ALLOW | NOT_ALLOW | PASS |
