# Red-team reproductions

Baseline: 702d66bcbfd65fa0bb584b5a882eadf613cb7a2c

| Hypothesis | Classification | Observation |
|---|---|---|
| all_three_signers_lie_about_denied_target | CONFIRMED FAIL-CLOSED | EVIDENCE_MISMATCH |
| mix_valid_attestations_from_different_issuances | CONFIRMED FAIL-CLOSED | ATTESTATION_HEADER_MISMATCH |
| requester_resigns_changed_spec_with_old_receipt | CONFIRMED FAIL-CLOSED | ACTION_MISMATCH |
| share_only_pq_component_between_requester_and_verifier | CONFIRMED FAIL-CLOSED | TRUST_DUPLICATE_KEY |
| escaped_duplicate_security_field | CONFIRMED FAIL-CLOSED | DUPLICATE_JSON_KEY |
| numeric_truthy_predicate_substitution | CONFIRMED FAIL-CLOSED | SCHEMA_INVALID |
| dynamic_adapter_method_injection | CONFIRMED FAIL-CLOSED | SCHEMA_INVALID |
| two_valid_votes_plus_corrupt_surplus | CONFIRMED FAIL-CLOSED | SIGNATURE_INVALID |
| receipt_from_attacker_self_provisioned_cluster | CONFIRMED FAIL-CLOSED | SIGNATURE_INVALID |
| replace_request_signature_with_another_valid_signature | DESIGN LIMITATION | ALLOW |
| same_receipt_two_independent_replay_databases | ASSUMPTION VIOLATION | EXECUTED_TWICE |
| administrator_restores_preuse_database_snapshot | ASSUMPTION VIOLATION | EXECUTED_TWICE |
| edit_policy_file_after_executor_construction | DESIGN LIMITATION | OLD_SNAPSHOT_EXECUTES |
| trusted_adapter_lies_about_computation | ASSUMPTION VIOLATION | FALSE_COUNTS_HAVE_VALID_SIGNATURE |
| executor_key_forges_historical_result_without_running | ASSUMPTION VIOLATION | SELF_ASSERTED_EXECUTION_TIME_ACCEPTED |
| coordinator_extends_every_header_without_resigning | CONFIRMED FAIL-CLOSED | RECEIPT_TTL |
| truncated_transport_prefixes | CONFIRMED FAIL-CLOSED | 14_REJECTED |
| correlated_requester_resigned_mutation_bypass_search | NOT REPRODUCED | NO_BYPASS_IN_32_TRIALS |

All classifications are scoped to the stated boundary. An assumption-violation
reproduction is not evidence of a signature or receipt-verification bypass.
No formal verification or security proof follows from rejected attacks.
