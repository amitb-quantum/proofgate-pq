# Crypto treasury authorization design spike

Date: 2026-09-05. Status: design only; no crypto execution support.
Code inspected: `de58962fb088e5579d3a304125fd7a1026059598`.
Competitor sources were accessed on 2026-09-05. Documented capabilities are not independently tested integrations.

**Decision:** crypto fits ProofGate's authorization model, but it is not an adapter-only addition to the present code. A bounded, versioned action/policy/result extension could preserve the signature, receipt-binding and verify-before-reserve principles. Different verifier roles with different evidence, live state predicates, and reliable remote signing require additional design; they cannot silently inherit the current protocol's guarantees. No core redesign or implementation is proposed in this spike.

**Commercial conclusion:** the strongest candidate for customer discovery is protocol administrative release authorization, with evidence reusable across custody providers. Routine transfer limits, approvals, simulation and even independently verifiable policy outcomes already exist elsewhere. No customer interviews or pricing research establish willingness to pay.

## 1. Problem and proposed contribution

**Requesting an action is not permission to execute it.** An authenticated user or agent can request a harmful transaction. The proposed gate requires evidence about the exact transaction before the existing signer produces authority that can move funds.

| Existing control | What it establishes | Proposed additional contribution |
| --- | --- | --- |
| Authentication | Identity or possession of a credential | Bind that request to separately evaluated action predicates |
| Ordinary wallet signature | Authorization under the chain's account rules | Preserve the policy content and check results that preceded signing |
| Multisig approval | A configured threshold approved a transaction | Record what each verifier checked, with reproducible inputs and explicit policy identity |
| Transaction policy engine | Conditions enforced by that engine | Export an evidence package another institution or signer can verify under its own pinned trust anchors |

These are complementary distinctions, not claims that existing wallets lack policy or cryptographic evidence. Section 9 identifies substantial overlap.

Large stablecoin transfers need exact recipients and base-unit amounts. Treasury rebalances and DeFi actions additionally need constrained routes, allowances, output floors and exposure. Bridges require separate source-chain and destination-chain outcomes. Upgrades, mint/burn operations and governance/admin calls require exact privileged methods and authority changes. An AI initiator needs the same gate; model confidence or a persuasive explanation is not approval. This design addresses authorization evidence, not custody, market execution, solvency, AML determinations or the correctness of arbitrary contracts.

## 2. Mapping and current implementation limits

| Existing ProofGate object | Crypto analogue | What carries over |
| --- | --- | --- |
| Experiment specification | Exact transaction specification | Freeze before verifier signatures |
| Frozen experiment digest | Frozen transaction manifest digest | Canonical, domain-separated content binding |
| Simulator backend | Chain profile plus account/signer target | Explicit target; no silent substitution |
| Verifier predicates | Treasury, semantics, simulation and evidence checks | Explicit outcomes; no implicit approval |
| Authorization receipt | Transaction authorization receipt | Intent, policy digest, audience, suite, verifier set and TTL |
| Protected executor | Protected signing boundary | Verify independently, reserve, then admit effect |
| Replay reservation | Single-use signing admission | Durable intent and receipt uniqueness |
| Result provenance | Signed transaction and subsequent observations | Link results to authorization; separate claims |

The code is narrower than the abstract model:

- [models.py](../src/proofgate/models.py) fixes `Intent.action_type` to `quantum.run`, parameters to experiments, policies to quantum resource limits and results to simulator counts.
- [policy.py](../src/proofgate/policy.py) implements one deterministic quantum evaluator.
- [protocol.py](../src/proofgate/protocol.py) requires each vote's entire predicate dictionary and disposition to equal the executor's own evaluation. The threshold is a count of identities, not a quorum by specialty.
- [executor.py](../src/proofgate/executor.py) assumes a synchronous simulator effect, local SQLite reservation and quantum result validation.
- [canonical.py](../src/proofgate/canonical.py) already supports bounded ASCII strings suitable for explicit large-integer encodings; it rejects JSON integers beyond `2**53 - 1`.

Unchanged principles: authenticated requests alone do not authorize; all required signature components must verify; intent and policy content must match; only ALLOW admits execution; duplicate identities do not increase quorum; target/audience and validity are checked; reservation precedes the side effect. Their continued correctness would need regression validation for a new action version.

Unchanged assumptions: pinned and correctly provisioned keys/configuration, trusted clock and executor, trusted adapter, and one shared durable replay store that is neither rolled back nor bypassed. Separate processes on one host do not imply independent organizations. Historical provenance does not authorize a fresh action.

## 3. Exact transaction manifest: proposed profile, not a schema

Use Ethereum as a concrete case, not a commitment to a final chain. Start with **one type-2 transaction from an explicitly supported, undelegated EOA account** to an allowlisted contract or recipient. Exclude contract creation, raw message signing, permits, account-abstraction operations, delegation authorizations and batches until each has an explicit signing profile. A contract account such as Safe requires its own inner-operation profile; its address is not an EOA signer.

All fields below are frozen before authorization. Absence/null rules are fixed by the version; omitted fields cannot acquire wallet defaults later.

| Manifest area | Required frozen content and interpretation |
| --- | --- |
| Version and operation | Manifest version, action such as proposed `crypto.tx.sign`, exact account/signing/encoding profile and adapter revision |
| Network | Chain ID, network/genesis or trusted checkpoint identity, chain rules/fork profile; never a mutable RPC alias alone |
| Authority | Sender address, tenant/account/key reference, target signer service and expected signing key/address binding |
| Transaction bytes | Type, chain ID, account nonce, destination, native value in wei, exact calldata, gas limit, max fee and priority fee per gas, complete ordered access list |
| Semantic projection | Operation name, ABI/decoder revision and digest, token address, recipient, amount in token base units; these must round-trip to the exact calldata |
| Economic constraints | Native/token outflow caps, explicit units, allowed spender, output minimum, recipient and deadline for swaps; no floating-point prices or slippage percentages |
| Code dependencies | Expected contract set, call/delegatecall permissions, proxy address and runtime code hash, resolved implementation/beacon addresses and code hashes, resolution method and storage observations |
| State/evidence | Reference block number/hash/state root; pinned simulation engine/configuration; evidence bundle digest; predicate IDs/versions, operands and expected comparisons; evidence sources and maximum age |
| Governance/context | Subject, project, environment, ProofGate audience, policy ID/version/content digest, eligible verifier identities and configured quorum in the pinned policy |
| Validity/replay | Intent created/expiry timestamps, separate random ProofGate replay nonce, signer idempotency identifier bound to the action, optional predecessor authorization for replacements |
| Lifecycle constraints | Sign-only versus controlled sign-and-broadcast, broadcast window, observation/finality policy and explicit replacement/retry prohibition or procedure |

For this profile, freeze exact fee fields as well as policy ceilings. The wallet cannot choose any value within a range after approval. Even a lower fee or changed access-list ordering changes the payload and requires fresh authorization. Allowing a family of signing preimages would be a different authorization contract.

The type-2 signing preimage is `0x02 || RLP([chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas, gas_limit, destination, amount, data, access_list])`; Ethereum signs its Keccak-256 hash. Freeze the hex preimage and require independent reconstruction from fields. The sender is bound by ProofGate and checked against the signing key; it is not another RLP field. The signed envelope adds the chain signature. [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559)

Proposed canonical conventions preserve PGJ-1: uint256 quantities use ASCII decimal strings with grammar `0|[1-9][0-9]*`, checked against field-specific bounds. Use no signs, exponent notation, unit suffixes or leading zeros. Addresses are exactly 20 bytes rendered as lowercase `0x` hex; binary values use even-length lowercase hex, with fixed widths for hashes. Resolve human names before freezing. Reject ambiguous inputs rather than silently correcting them at the signing boundary. Arrays preserve order where execution order matters; conceptual sets must be sorted and duplicate-free. Bound manifest/evidence size within the existing document limits; no unrestricted fetches from caller-provided URLs.

Keep three distinct identities: the SHA-384 ProofGate manifest/intent digests, the chain signing hash of the unsigned payload, and the transaction hash of the final signed envelope. Version and domain-label each; never compare differently defined hashes because their names sound similar. The new manifest digest needs a transaction-specific domain; do not disguise transactions as experiments.

For an ERC-20 transfer, the outer destination is the token contract; the beneficiary and token amount are calldata arguments. Require exact decode/re-encode agreement, not a matching symbol or four-byte selector. Token decimals are display metadata. A token can return false without the transaction reverting, so a successful outer receipt alone cannot establish a transfer. [ERC-20](https://eips.ethereum.org/EIPS/eip-20)

Expected contracts touched are constraints evaluated at a specified state, not an oracle for every future execution path. Proxy runtime bytes alone do not pin its logic: standard proxy schemes can resolve implementation or beacon state separately. Unsupported resolution schemes fail closed. [ERC-1967](https://eips.ethereum.org/EIPS/eip-1967)

Freeze the policy digest in the proposed crypto intent as well as the receipt, avoiding implicit acceptance of a different policy with the same ID/version. The present intent has only a policy reference; this is a versioned model extension, not an existing feature.

## 4. Independent verifier roles and evidence

| Role | Deterministic checks on frozen inputs | External dependence |
| --- | --- | --- |
| Treasury policy | Exact account, asset, beneficiary, per-action amount and fee limits; required approval evidence | Beneficiary ownership, aggregate available budget and price observations |
| Contract semantics | Byte/ABI agreement, allowed method, privileges, allowance and upgrade parameters | Trusted ABI/code provenance, proxy resolution and current storage |
| Execution simulation | Replay under pinned engine, rules and state; expected outflow/output/storage predicates | Authentic state snapshot, complete dependencies and future ordering |
| Optional risk/counterparty | Report signature, subject binding, issuer, expiry and threshold checks | Report accuracy, coverage and timeliness; not independent proof of compliance |

Missing or stale required evidence yields UNKNOWN; execution/provider failure yields ERROR; violated conditions yield DENY; a required unresolved human review yields HUMAN_VERIFY. None counts as an approval. Human review must produce separately bound evidence followed by a new evaluation, not change a negative receipt's label.

**Compatibility-preserving option:** roles prepare a single bounded evidence bundle before freezing. Every approval signer and the executor validate the complete same bundle and run the complete same deterministic evaluator. Start with all three configured verifier identities required (`quorum=3`), not two specialties substituting for a missing third. Specialist evidence producers are not automatically quorum signers. They can sign reports; those reports and issuer keys must be covered by the policy and frozen bundle. This preserves unanimous predicate agreement, although trusting a report is weaker than independently establishing its factual truth.

**Different protocol option, deferred:** treasury, semantics and simulation sign different predicate subsets. The present verifier rejects that. Supporting it requires role-specific coverage, required-role quorum rules, report schemas and disagreement semantics, plus a changed executor verification rule. Do not label it adapter-only or weaken `EVIDENCE_MISMATCH` into “enough signatures.”

Independent RPC endpoints may share an upstream node; separate signers may share buggy decoding code. Independence needs operational evidence. Simulation reproducibility on an authenticated snapshot does not prove that the snapshot will still describe the inclusion state. If validating the required state witness is infeasible, explicitly trust named providers or return UNKNOWN.

Aggregate spend limits require atomic budget reservations across competing intents; a copied balance or daily-total report is insufficient. This is a new domain ledger coordinated with admission, not something the existing nonce replay table provides.

## 5. Signing boundary and mutation

Intended path:

```text
frozen request + evidence -> verifier receipt -> enforcing signing gateway
    -> wallet / custodian / MPC / HSM -> optional broadcaster -> blockchain
```

ProofGate holds authorization/provenance keys, not treasury private keys or MPC shares. The existing custodian retains them. However, the gateway is security-critical: a receipt stored next to a transaction is ineffective if an alternate API can still sign freely.

Proposed sequence:

1. Obtain final unsigned bytes from the signer preparation flow; independently parse and freeze them before approval.
2. At the final signing hook, validate pinned trust, the complete receipt, expiry, policy and exact manifest/preimage equality. Recheck configured state freshness and code assumptions; differences require fresh evidence and authorization.
3. Durably reserve admission and the correlated domain nonce/job record before issuing one authenticated signing request. The signer must bind the job ID to this exact payload and enforce idempotency.
4. Verify returned chain signature/sender and exact serialized fields, calculate the signed transaction hash locally and durably record the result.
5. If broadcasting is controlled, send only these recorded signed bytes and record each observation. Any changed signing preimage starts a new authorization.

An HSM that accepts arbitrary digests cannot itself understand a JSON receipt. Either the exclusive gateway enforces it, or the signing platform provides an obligatory approval callback with final payload binding. The former trusts the gateway host; neither solution is supplied by this repository today.

| Mutation after authorization | Required response |
| --- | --- |
| Destination, sender, chain, token, amount or calldata changed | Reject byte/manifest mismatch before signing |
| Slippage, route, output recipient or encoded deadline changed | Reject changed calldata; a UI-only limit is not sufficient |
| Gas, fee caps or access list changed | New exact payload and authorization, including fee bumps |
| Proxy implementation changed with identical transaction bytes | Reject observed state/code mismatch at the gate; bytes alone cannot detect it |
| Policy, signer target or audience changed | Reject binding mismatch; explicitly provision new trusted policy if intended |

The hardest limit is **state change after the last check and before inclusion**. A proxy upgrade, price movement or adversarial ordering can change effects without changing transaction bytes. Off-chain approval cannot eliminate that gap. For predicates that must hold during execution, use existing contract-enforced deadlines, output floors or guards that actually read the required state. If the target lacks them, decline the stronger guarantee or restrict the action. No guard/contract is implemented here.

A raw EOA transaction has no ProofGate expiry field enforced by Ethereum. Once signed bytes escape, anyone holding them may submit them later while chain-valid. Receipt expiry limits signing admission, not the lifetime of a signature. Controlled broadcast does not revoke a leaked signature. [Ethereum transactions](https://ethereum.org/developers/docs/transactions/)

Safe needs a separately frozen inner Safe transaction hash/domain, nonce, operation, gas/refund fields and account configuration; an outer relayer transaction is distinct. Owner, module, recovery and policy-admin paths must be considered when determining whether the gate is obligatory. Guards and module guards have version-specific coverage; one gated owner is not necessarily required by every valid threshold. [Safe concepts](https://docs.safe.global/advanced/smart-account-concepts), [module guards](https://docs.safe.global/reference-smart-account/guards/setModuleGuard)

## 6. Replay and lifecycle semantics

Retain current at-most-once **admission** per protected replay store. The ProofGate replay nonce is distinct from the chain account nonce and from the remote signing job ID. Fresh receipt IDs over one intent remain spent. Fresh intent nonces can still request the same economic action: a treasury business-operation ID and a shared `(network, account, chain nonce)` ledger must detect that separately.

Proposed domain state machine, not implemented:

```text
FROZEN -> AUTHORIZED -> RESERVED -> SIGN_REQUESTED
                                  -> SIGNED or SIGNING_OUTCOME_UNKNOWN
SIGNED -> BROADCAST_ATTEMPTED -> PENDING -> INCLUDED_SUCCESS or INCLUDED_REVERT
                                       -> UNKNOWN / DROPPED_OBSERVED
INCLUDED_* -> FINALIZED_OBSERVED
INCLUDED_* -> REORGED -> PENDING / UNKNOWN / different inclusion
```

Expiry or denial before reservation prevents admission. Failure after reservation never automatically refunds the permit. A crash between reservation and signer response may strand authorization. “Unknown” is an operational state, never approval.

| Situation | Proposed behavior |
| --- | --- |
| Concurrent account nonce use | Coordinate all authorized senders through one domain ledger; outsiders using the same key violate the integration assumption |
| Dropped transaction | Absence from one mempool is not cancellation. Retain signed bytes and unresolved nonce; do not release funds or issue an unrelated retry automatically |
| Replacement/cancellation | New exact transaction, new intent/receipt, same chain nonce, linked predecessor and coordinated ledger transition; earlier signed bytes may win the race |
| Fee bump | Replacement authorization even if destination/amount stay identical; disable wallet auto-bumping that bypasses the gate |
| Signing timeout | Query the durable signer job. Do not blindly resubmit if the signer cannot establish idempotency or reconcile the outcome |
| Retrying transport | Retrieve the same recorded signing result or rebroadcast identical signed bytes under the job's broadcast policy; do not re-enter signing with a spent receipt |
| Revert/failure | Record failure and costs. On canonical inclusion the chain nonce is consumed even though application changes revert; a new attempt requires new authorization |
| Sign without broadcast | Record SIGNED; it is already a valuable capability. Do not call it executed or cancelable by receipt expiry |
| Broadcast without confirmation | Record provider acknowledgement separately from inclusion; neither proves finality |
| Reorg | Append a new observation withdrawing the old inclusion claim; never erase prior evidence or unspend the ProofGate reservation |

The local SQLite transaction cannot atomically commit with an external HSM/MPC service or blockchain. At-most-once local admission may be retained by refusing uncertain retries, at the cost of availability. Durable remote idempotency is required for useful recovery; it is not present in the current executor.

Ethereum finality is a consensus property, distinct from a chosen count of confirmations. A client/provider report must be evaluated under a pinned network-specific observation policy. L2 settlement and bridge destination finality need separate profiles. [Ethereum PoS](https://ethereum.org/developers/docs/consensus-mechanisms/pos/)

## 7. Provenance: four separate claims

Propose versioned, signed, append-only observation records binding: intent/manifest/receipt/policy/evidence digests; sender/network; unsigned signing hash; actual signed envelope hash; signer job ID and signature identity; broadcast provider response/hash; block hash/number and transaction index; execution status, gas and logs; relevant state witnesses and evaluated transition predicates; observation time, observer identity and finality-policy version. A locally calculated transaction hash must agree with a returned broadcast hash. Record replacements as separate linked transactions.

| Claim | What evidence can support it | What it does not establish |
| --- | --- | --- |
| Authorization provenance | Verifier receipt plus reproducible inputs and trusted public keys | That the signer actually acted |
| Signing/broadcast provenance | Chain signature and gateway/provider records | That the network included it |
| Inclusion | Receipt/header evidence against an authenticated canonical-chain view | Economic correctness or irreversible finality |
| Semantic/economic outcome | Specified balance, allowance, ownership or implementation transitions with state evidence | Unspecified business goals, fair pricing or absence of all loss |
| Finality | Chain-specific consensus evidence under named assumptions | Destination bridge completion or correctness of another chain |

A transaction hash is an identifier, not a self-contained inclusion proof. Provider statements remain provider assertions unless verified against an authenticated chain view. Logs and outer success status are not enough for every semantic predicate; simulation is a prediction at its snapshot. Never collapse authorization, inclusion, economic correctness and finality into one `success` flag.

The present signed result is already a trusted-executor assertion, not a proof of computation or trustworthy wall time. Crypto observations need a new result type and lifecycle journal; reusing simulator counts would misrepresent their meaning. Evidence portability also requires retaining the actual policy, decoder and evidence inputs: a digest of unavailable data cannot explain a decision. Use customer-controlled retention/access; public verification does not require public disclosure of treasury plans.

## 8. PQC relevance

ML-DSA provides post-quantum signature authentication under its security assumptions; NIST standardizes it in FIPS 204. This is relevant to long-lived authorization archives and future verification of who approved which frozen inputs. It does not make a faulty predicate true. [NIST FIPS 204](https://csrc.nist.gov/pubs/fips/204/final)

The existing hybrid mode requires both Ed25519 and ML-DSA components. Keep algorithm pinning, trusted key distribution and domain separation; do not claim quantum-resistant authorization if fallback accepts the classical component alone. A future deployment also needs trustworthy historical key/configuration records and timestamps; adding an ML-DSA wrapper to a classical external report does not retroactively establish its truth or age.

| Layer | Meaning |
| --- | --- |
| ProofGate evidence | Can use current ML-DSA or both-required hybrid signatures without holding blockchain keys |
| Current-chain transaction | The selected Ethereum type-2 profile still uses the chain's secp256k1 signature; ProofGate does not change that |
| Future PQ-capable account/chain | Requires a separately supported and reviewed account/chain signature profile, wallet support and verification rules |

An attacker who can forge the chain's signature can bypass an off-chain receipt gateway. Thus this proposal does **not** make Ethereum, wallet assets or a smart account quantum-safe. It also does not provide hardware attestation equivalent to a TEE. No key-establishment requirement is introduced, so there is no reason to add ML-KEM. No cryptographic changes are made.

## 9. Competitive differentiation: hypothesis substantially narrowed

Sources below describe current public capabilities, not commercial-plan availability guarantees. “Not established in reviewed docs” means exactly that; it is not proof of absence.

| System | Overlap already documented | Remaining possible contribution and integration question |
| --- | --- | --- |
| Safe | Threshold authorization over transaction parameters, extensible modules and pre/post execution guards. This already binds approval to an action. [Concepts](https://docs.safe.global/advanced/smart-account-concepts) | A common off-chain predicate/evidence package across signers could complement it. Existing extensions could implement similar checks; no uniqueness claim. Determine mandatory guard/module coverage for the deployed version. |
| Fireblocks | Customer logic can approve/deny at the API Co-signer callback before signing. [Architecture](https://developers.fireblocks.com/docs/cosigner-architecture-overview) It supports raw Ethereum validation and authenticated callback exchanges. [Raw validation](https://developers.fireblocks.com/reference/validate-eth-raw-transactions) | A customer-hosted ProofGate evaluator could occupy that hook; “external verification before signing” is already provided. Value would be a reusable multi-issuer evidence contract rather than bespoke callback logic. |
| Turnkey | Policy Outcome App Proofs already bind outcome, decision-context and organization-data digests and request approvals. P-256 enclave App Proofs link to Boot Proofs; public verification tooling is documented. [Turnkey Verified](https://docs.turnkey.com/security/turnkey-verified) | Direct counterexample to claiming independent verifiability or policy evidence as novel. A potential distinction is custody-neutral, customer-chosen verifier/evidence identities and explicit predicate replay, with optional PQ authorization signatures. ProofGate has no comparable enclave execution attestation. |
| Fordefi | Granular transaction rules and configurable approval groups already govern signing. [Policies](https://docs.fordefi.com/user-guide/policies) Expected/mined effects support reconciliation and programmatic approvals. [Effects](https://docs.fordefi.com/developers/effects) Custom API approvers add independent business logic. [API approver](https://docs.fordefi.com/developers/transaction-types/build-custom-api-approver) | A portable receipt could preserve evidence across platform changes; approval hooks and simulated effects themselves are not a differentiator. Confirm exact final-byte binding after approval and fee/nonce preparation. |

Important qualifications:

- Fireblocks documents audit events for policy and screening decisions; ordinary auditability is not a gap. [Audit events](https://developers.fireblocks.com/reference/audit-log-events) Its raw signing payload is opt-in, appears at signing rather than approval, and the docs identify an EU-cloud availability exception. Multiple raw payloads can occur in one request; reject anything outside the single-payload profile. Do not promise universal integration. [Approval callback reference](https://developers.fireblocks.com/reference/approve-transactions)
- Turnkey's December 2025 announcement describes released verifiable policy decisions, not just a roadmap. [Announcement](https://www.turnkey.com/blog/introducing-verifiable-policy-decisions) Its policy docs also explicitly give root quorum an override. A gated non-root credential cannot cover root access; this is an integration assumption to expose, not a newly discovered exploit. [Policy evaluation](https://docs.turnkey.com/features/policies/overview)
- Fordefi's custom approver is an approval identity, not the transaction signer. Its docs warn not to use it as transaction initiator because initiators supply tacit approval. [Custom approver](https://docs.fordefi.com/developers/transaction-types/build-custom-api-approver) Missing simulation evidence can lead to partial-data/default-rule handling; the proposed ProofGate profile would instead require UNKNOWN for a missing mandatory predicate. This is a stricter configuration choice, not a claim Fordefi cannot fail closed. [Simulation handling](https://docs.fordefi.com/user-guide/manage-transactions/override-simulation)

**Rejected broad hypothesis:** “Other systems sign without independently verifiable authorization evidence.” Turnkey is a concrete counterexample, while Safe, Fireblocks and Fordefi already provide substantial enforcement and extensibility.

**Narrow surviving hypothesis:** a customer-controlled, custody-neutral evidence format binding exact signing bytes, policy content, named predicates, retained inputs and multiple independently managed verifier identities could reduce duplicated integration and review work across custody systems. ML-DSA authorization is an optional archive/security property, not the main economic benefit.

The reviewed sources do not establish a single shared format with that entire combination across these vendors. They also do not establish that customers want another layer, that the combination is unique, or that a competitor cannot supply it. ProofGate's current booleans explain deterministic checks via the evaluator and policy; rich evidence objects, heterogeneous reviewers and cross-vendor portability are proposed work, not delivered features. Compare a real Turnkey proof plus its available context exports against the proposed receipt before claiming an evidence gap.

## 10. Commercial wedge and pre-code decisions

The following buyer/pain assessment is inference from the documented capabilities and integration constraints, not validated market demand.

| Candidate | Buyer and pain hypothesis | Integration point | Increment beyond incumbents / adoption assessment |
| --- | --- | --- | --- |
| Institutional treasury transfers | Treasury controller or security lead managing several custodians; inconsistent review records and duplicated controls | Mandatory final-signing callback plus treasury operation/nonce ledger | Routine amount/recipient/quorum controls are well served. Adoption plausible only if independent reviewers need reusable evidence across providers; switching and availability costs are substantial. Weak initial general-purpose wedge. |
| Protocol administrative actions | Protocol foundation/security council or engineering security lead; review of upgrade calldata, implementation artifacts and authority changes is spread across people and systems | Existing admin signing/release workflow, then an obligatory custodian hook or supported account gate | Strongest candidate: package release-specific checks and independent review for rare, high-consequence changes. Custom callbacks/guards remain substitutes. More plausible paid integration plus supported evidence tooling than a new signing platform; willingness to pay unproven. |
| AI-agent financial actions | Agent-platform or fintech engineering/security lead; scoped delegation and unattended actions | Agent request enters gate before an existing policy-constrained signer | Native policy engines already address much of this. Useful only where external task evidence must survive across providers; adds latency and trust complexity. “AI” alone is not a wedge. |

**Select protocol-admin release evidence as the strongest discovery wedge, conditionally.** Start conceptually with one supported privileged contract call, an exact implementation/ABI/build-artifact review package, and clearly specified expected authority/storage changes. A Safe-based customer would require the separate account profile described above; the easier EOA example does not establish Safe compatibility. Bridges and trading strategies are poor first targets because multi-stage settlement and moving-state dependencies overwhelm the bounded authorization problem.

Before any code, test these questions:

1. Can a design partner supply a real redacted admin review whose evidence cannot be reproduced adequately using its current vendor exports, especially Turnkey Policy Outcome Proofs?
2. Will the buyer pay for independent evidence review, retention and vendor portability, and who owns the budget? Measure actual review effort and incident-reconstruction pain before setting prices.
3. Can the chosen signer expose final bytes and require the gate on every relevant path, including recovery/admin override and automatic fee replacement? Obtain a precise version/plan-specific contract.
4. Can the signer correlate timeouts and return a durable idempotent result without signing a second request? Who operates the shared nonce and budget ledger?
5. Which predicates can be reproduced from authenticated retained inputs, and which are merely trusted expert/provider statements? Will all verifiers and the executor run the full evaluator?
6. Which effects require an on-chain precondition, and does the existing target enforce it at execution time? If not, will the customer accept a narrower snapshot-based claim?
7. Are independent reviewer operations, evidence confidentiality and retention affordable? Can evidence still be checked after a vendor or key configuration changes?

**Biggest unresolved risk:** the end-to-end enforcement contract. If the signer can bypass or mutate the approved payload, or if an assumed state condition changes before inclusion without an on-chain check, a valid receipt does not guarantee the intended transaction effect.

## 11. Core-change assessment

**Answer:** preserve the authorization architecture, but do not advertise crypto as a drop-in adapter for the current repository. A restricted exact-transaction profile needs bounded, security-reviewed versioned core integration and a substantial signer/lifecycle adapter. The broader proposal with heterogeneous verifier roles requires genuine protocol changes. This spike leaves the core unchanged and recommends validating the buyer and signer contracts before choosing either path.

Here “core change” includes edits to current typed models and acceptance/result dispatch, even when the cryptographic architecture remains intact. “Domain adapter only” includes external orchestration, not merely substituting the existing simulator object. No row authorizes implementation.

| Requirement | Existing core handles it | Domain adapter only | Core change required |
| --- | --- | --- | --- |
| Canonical bounded ASCII and domain-separated SHA-384 | Yes | Decimal/hex field validation | No canonicalizer redesign |
| Request signatures, fixed suites, both-required hybrid | Yes | Provision independent trust anchors | No cryptographic change |
| Crypto action, manifest and policy types | No; quantum literals/types | Define domain semantics | Yes: versioned models and fail-closed action/policy dispatch |
| Intent-level policy content digest | Receipt has it; intent lacks it | Define binding | Yes: crypto intent version |
| Exact transaction preimage/ABI/chain binding | No | Transaction decoder, encoder and signer profile | Domain evaluator must be reached through versioned core dispatch |
| Same complete predicates checked by every signer and executor | Yes, as a principle | New deterministic evaluator over frozen inputs | Preserve comparison semantics; extend evaluator dispatch |
| Specialist signers voting on different subsets | No | Cannot solve with a simulator adapter | Yes: evidence/coverage/quorum semantics; deferred |
| Authenticated external evidence and pinned simulation | No generic evidence model | Acquisition, validation and bounded witnesses | Versioned domain input/evaluation integration; no signature redesign |
| ALLOW-only admission and fixed receipt/header binding | Yes | Choose required evidence and all-three policy | Preserve rejection semantics |
| Admission replay in one protected durable store | Yes | Retain storage assumptions | No exactly-once extension |
| Account nonce, business-operation deduplication and aggregate budgets | No | Shared domain ledger and signer coordination | Integration with admission required; current table alone is insufficient |
| Remote signing, timeout recovery and broadcast tracking | No | Durable jobs, idempotency and reconciliation | Versioned execution/result contract; synchronous counts interface is insufficient |
| Replacements, reorgs and finality observations | No | Linked lifecycle records and chain evidence | New result representation; do not change admission into settlement |
| Mandatory wallet/custodian/account enforcement | No | Provider-specific hook and account configuration | No ProofGate core change can remove an external bypass |
| Guarantee unchanged state through inclusion | No | Only supported on-chain preconditions or restricted claims | A core redesign cannot supply this guarantee |
| Crypto result/provenance format | No; backend/counts constrained | Domain checks and observation verification | Yes: versioned result and verifier dispatch |
| Quantum-safe blockchain/assets | No | Requires chain/account migration | Outside this proposal; PQ receipts do not provide it |
