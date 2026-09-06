# Adversarial review of the crypto administrative-action wedge

Reviewed 2026-09-05 against repository commit `b998a21dd974713f4152c444dc63f03227812011` and the [prior design spike](crypto-treasury-design.md). This is a document-only commercial and architecture assessment. No customer interviews, vendor-account experiments, contract inspection of a deployed customer system, or implementation were performed.

## Decision rationale

The proposed product has not earned an implementation experiment. Exact-action approval, pre-transaction simulation, custom approval logic, upgrade validation, on-chain access control and cryptographically verifiable policy decisions already have substantial substitutes. The remaining possibility is evidence interchange between independently operated reviewers and custody platforms. No reviewed source establishes that this combination is universally available; neither does that documentation gap establish a market.

The strongest negative evidence added to the prior spike is:

- Turnkey exposes per-policy evaluation outcomes in addition to signed policy proofs. It is not merely an opaque signing API with activity logs. [Evaluation API](https://docs.turnkey.com/api-reference/queries/get-policy-evaluations)
- Safe documents integrated simulation, external security signals, and a Hypernative Guard product that applies custom rules. “An independent security system before a Safe transaction” is already a product category. [Safe simulation](https://help.safe.global/articles/3902870017-safe-wallet-security-with-tenderly-blockaid), [Guardian](https://help.safe.global/articles/7610775969-understanding-safe-shield-guardian-by-hypernative)
- OpenZeppelin supplies upgrade checks and governance building blocks. Forta describes contract-level attestation gating. Repackaging these controls does not create a new prevention capability. [Upgrade validation](https://docs.openzeppelin.com/upgrades-plugins/api-core), [governance](https://docs.openzeppelin.com/contracts/5.x/api/governance), [Forta](https://docs.forta.network/en/latest/what-is-forta-firewall/)

An incumbent need not deliver the identical JSON format to be a commercial substitute. It needs to solve the buyer's actual failure or review burden adequately. The comparison therefore includes incumbent configuration and an existing-tool workflow, not just identical feature names.

## Evidence rules and comparison questions

All external sources below are primary vendor or standards documentation, accessed during this review or the immediately preceding design spike on 2026-09-05. Dates describe review currency, not proof of deployment availability. Documentation is evidence of a documented feature, not an independent security audit.

**D** means directly documented. **C** means conditional on configuration or a specified integration; it is not an out-of-box guarantee. **I** means inferred composition that requires customer engineering. **U** means not established by the sources reviewed, not a finding that the vendor lacks the feature.

The ten questions are kept explicit for each product:

1. Exact transaction/action binding.
2. Simulation before signing.
3. Policy before signing.
4. Different predicates attested by independent entities/providers.
5. Portable evidence outside custody.
6. Independent verification/recomputation of the authorization reason.
7. Retention of inputs and predicate outcomes.
8. Mandatory coverage of all signing paths.
9. Upgrade/admin-specific support.
10. Whether it already supplies essentially the proposed value.

A chain signature over bytes is not a freeze of every earlier application field. A human approval is not a typed predicate attestation. Verifying a signed outcome is not the same as re-running all evaluation inputs. These distinctions prevent over-crediting incumbents, but also apply to ProofGate.

## Turnkey / Turnkey Verified

| Question | Finding |
| --- | --- |
| 1. Exact binding | **D:** authenticated signing activity contains the raw unsigned transaction and signing identity, and returns signed bytes. [Signing API](https://docs.turnkey.com/api-reference/activities/sign-transaction) |
| 2. Pre-sign simulation | **U:** the signing/proof docs reviewed do not establish native full execution simulation. **I:** a caller can supply an external simulator; that is separate from enclave policy evaluation. |
| 3. Pre-sign policy | **D:** organization policy conditions and consensus govern activities. Root quorum is an explicit exception. [Policy rules](https://docs.turnkey.com/features/policies/overview) |
| 4. Independent predicate attesters | **D:** multiple user approvals. **U:** a native custody-neutral schema for independently issued predicate subsets. **I:** customer reviewers could be separate approval identities. |
| 5. Portable evidence | **D:** signed App Proofs and linked Boot Proofs have public verification tooling. This directly contradicts a claim that verifiable evidence cannot leave custody. [Verified](https://docs.turnkey.com/security/turnkey-verified) |
| 6. Independent reason verification | **D:** policy proof binds outcome, decision-context/organization digests and approvals. **U:** this page alone does not establish complete replay of every predicate from exported historical inputs. Proof verification is stronger than an ordinary log but different from full recomputation. [Verified](https://docs.turnkey.com/security/turnkey-verified) |
| 7. Retained inputs/outcomes | **D:** activity contains transaction intent/result/votes; evaluation API returns policy IDs and outcomes. **U:** complete historical policy/context preimages, intermediate results and retention guarantees for offline replay. [Activity](https://docs.turnkey.com/api-reference/activities/sign-transaction), [evaluations](https://docs.turnkey.com/api-reference/queries/get-policy-evaluations) |
| 8. All signing paths mandatory | **C:** constrain ordinary credentials; root quorum bypass remains documented. No arbitrary ProofGate-receipt validation hook is established here. [Policy rules](https://docs.turnkey.com/features/policies/overview) |
| 9. Upgrade/admin workflow | **D:** Ethereum transaction signing. **I:** privileged calls can use it. **U:** native storage-layout/build-artifact upgrade review is not established by these sources. |
| 10. Essentially the value? | **Yes for much of the evidence proposition.** Exact requests, policy approval and externally checkable outcome proofs already overlap. Cross-provider specialist evidence remains an unvalidated distinction. |

Do not characterize Turnkey's proofs as proof of economic correctness. Conversely, ProofGate cannot claim superiority simply because its trusted signers make more explicit assertions: it lacks Turnkey's documented enclave-to-proof binding. Verify actual context export availability before treating the remaining recomputation question as a sales advantage.

## Fireblocks

| Question | Finding |
| --- | --- |
| 1. Exact binding | **D/C:** opt-in raw transaction data is available at the signing callback; availability is not universal. [Callback fields](https://developers.fireblocks.com/reference/approve-transactions) |
| 2. Pre-sign simulation | **D:** Ethereum contract-call enrichment simulates projected vault effects before signer review. It is not a general proof of admin-call correctness. [Statuses/enrichment](https://developers.fireblocks.com/reference/statuses) |
| 3. Pre-sign policy | **D:** policy routes authorization and signing; a customer Callback Handler can reject before MPC starts. [Co-signer architecture](https://developers.fireblocks.com/docs/cosigner-architecture-overview) |
| 4. Independent predicate attesters | **D:** external business logic hook. **I:** multiple review services can feed it. **U:** a common signed predicate-coverage format is not established. |
| 5. Portable evidence | **D:** external authenticated callback exchanges and audit events. **U:** a complete standalone multi-verifier receipt is not established. [Raw validation](https://developers.fireblocks.com/reference/validate-eth-raw-transactions), [audit events](https://developers.fireblocks.com/reference/audit-log-events) |
| 6. Independent reason verification | **I:** customer can retain and re-run its callback inputs/code. **U:** portable full replay of Fireblocks' internal policy evaluation is not documented by these sources. |
| 7. Retained inputs/outcomes | **D:** transaction and policy-related audit events exist. **U:** every intermediate predicate and exact historical input snapshot is not established. [Audit events](https://developers.fireblocks.com/reference/audit-log-events) |
| 8. All signing paths mandatory | **C:** required co-signer plus callback on every relevant route. Co-signers without a callback automatically approve/sign for that API user; routing matters. [Architecture](https://developers.fireblocks.com/docs/cosigner-architecture-overview) |
| 9. Upgrade/admin workflow | **D:** EVM CONTRACT_CALL operations. **I:** bespoke upgrade checks in a callback. **U:** native upgrade-layout review is not established. [Operations](https://developers.fireblocks.com/reference/create-transactions) |
| 10. Essentially the value? | **Yes for external checks before signing.** A reusable evidence package could replace bespoke callback glue, but ProofGate is not required to enforce those checks. |

The raw-payload reference distinguishes signing from approval, documents an EU-cloud exception, and permits multiple payloads. A design based on one exact signing preimage must establish compatibility rather than assume a transaction ID means immutable final bytes. [Callback fields](https://developers.fireblocks.com/reference/approve-transactions)

## Safe, including its documented security integrations

| Question | Finding |
| --- | --- |
| 1. Exact binding | **D:** Safe owner signatures bind the inner Safe transaction parameters. The relayer's outer transaction is separate. [Concepts](https://docs.safe.global/advanced/smart-account-concepts) |
| 2. Pre-sign simulation | **D:** Safe Wallet integrates Tenderly simulation and security scanning. Separate-device hash/trace review is also documented. [Wallet security](https://help.safe.global/articles/3902870017-safe-wallet-security-with-tenderly-blockaid), [verification guide](https://help.safe.global/articles/4369997924-how-to-verify-safewallet-transactions-on-a-hardware-wallet) |
| 3. Pre-sign policy | **D:** Guardian documents policy checks in the workflow; a transaction guard supplies execution enforcement. Distinguish UI/pre-sign checks from what a contract can enforce. [Guardian](https://help.safe.global/articles/7610775969-understanding-safe-shield-guardian-by-hypernative) |
| 4. Independent predicate attesters | **D:** multiple owners and signals from several security providers. **U:** typed, independently signed predicate coverage is not established. [Copilot](https://help.safe.global/articles/6434169802-understanding-safe-shield-copilot) |
| 5. Portable evidence | **D:** signatures, transaction data and on-chain execution are independently inspectable. **U:** standardized export of the entire off-chain security-decision package. |
| 6. Independent reason verification | **D:** hashes/signatures and account authorization can be checked. **I:** replay disclosed guard logic. **U:** reproduce all proprietary provider judgments. [Concepts](https://docs.safe.global/advanced/smart-account-concepts), [verification guide](https://help.safe.global/articles/4369997924-how-to-verify-safewallet-transactions-on-a-hardware-wallet) |
| 7. Retained inputs/outcomes | **D:** transaction data and security findings are surfaced; Guardian advertises audit trails. **U:** durable full input/predicate export and retention terms. [Copilot](https://help.safe.global/articles/6434169802-understanding-safe-shield-copilot), [Guardian](https://help.safe.global/articles/7610775969-understanding-safe-shield-guardian-by-hypernative) |
| 8. All signing paths mandatory | **No blanket guarantee. C:** guards constrain covered execution paths, not owners' ability to generate signatures elsewhere. Modules and configuration changes need version-specific coverage. [Concepts](https://docs.safe.global/advanced/smart-account-concepts), [module guard](https://docs.safe.global/reference-smart-account/guards/setModuleGuard) |
| 9. Upgrade/admin workflow | **D:** arbitrary contract-call/batch preparation; configuration-change warnings. **I:** use Safe as a protocol admin. [Builder](https://help.safe.global/articles/4180673514-transaction-builder), [delegatecall warning](https://help.safe.global/articles/4308960633-why-do-i-see-an-unexpected-delegate-call-warning-in-my-transaction) |
| 10. Essentially the value? | **Yes for a large part of the practical workflow**, especially with a guard and independent review. A missing common evidence format does not negate this substitute. |

Guardian's documentation describes a 24-hour timelock for removal. That is evidence of governed removal, not immutable enforcement. Its broad protection claims do not establish coverage of every deployed Safe version/module; a customer-specific configuration must be inspected. [Guardian](https://help.safe.global/articles/7610775969-understanding-safe-shield-guardian-by-hypernative)

## Fordefi

| Question | Finding |
| --- | --- |
| 1. Exact binding | **D:** approvals operate on transaction payloads. **U:** immutable final nonce/fee/signing-byte identity throughout every approval path is not established here. [Custom approver](https://docs.fordefi.com/developers/transaction-types/build-custom-api-approver) |
| 2. Pre-sign simulation | **D:** expected transaction effects are available before execution; mined effects are separate. [Effects](https://docs.fordefi.com/developers/effects) |
| 3. Pre-sign policy | **D:** granular rules and approval groups precede signing. [Policies](https://docs.fordefi.com/user-guide/policies) |
| 4. Independent predicate attesters | **D:** external API approver can inspect payloads against business rules. **I:** separate organizations operate reviewers. **U:** standardized signed predicate receipts. [Custom approver](https://docs.fordefi.com/developers/transaction-types/build-custom-api-approver) |
| 5. Portable evidence | **D:** effect data is accessible through APIs. **U:** standalone cryptographically verifiable policy-reason export. [Effects](https://docs.fordefi.com/developers/effects) |
| 6. Independent reason verification | **I:** replay customer approver rules with archived inputs. **U:** independent replay of every internal decision/provider result. |
| 7. Retained inputs/outcomes | **D:** expected/mined results and transaction lifecycle statuses. **U:** complete historical policy/evidence retention. [Effects](https://docs.fordefi.com/developers/effects), [lifecycle](https://docs.fordefi.com/user-guide/manage-transactions/transaction-lifecycle) |
| 8. All signing paths mandatory | **C:** mandatory approver in matching rules. Its documented initiator/tacit-approval behavior creates a configuration constraint; approval is not itself a transaction signature. [Custom approver](https://docs.fordefi.com/developers/transaction-types/build-custom-api-approver) |
| 9. Upgrade/admin workflow | **D:** contract-call ABI parameter conditions. **I:** custom admin review. **U:** native storage-layout safety checks. [Rule conditions](https://docs.fordefi.com/user-guide/policies/policy-rules-conditions-and-actions) |
| 10. Essentially the value? | **Yes for programmable independent approval plus simulation.** Portable multi-issuer evidence could add packaging, not a unique ability to reject bad calls. |

A missing simulation may lead to partial-data/default-rule evaluation, rather than an obligatory veto. This is not a discovered exploit or proof of unavoidable fail-open behavior; strict policies can constrain it. [Simulation handling](https://docs.fordefi.com/user-guide/manage-transactions/override-simulation)

## OpenZeppelin Defender and current successor tooling

The Defender landing page announces a July 1, 2026 shutdown, a date already past at review time; other retained pages still say maintenance mode. This review did not test service reachability. Do not recommend new reliance on hosted Defender. The documented migration targets are self-hosted OpenZeppelin Relayer and Monitor; they are not advertised as a complete replacement for every Defender module. [Defender notice](https://docs.openzeppelin.com/defender), [migration](https://docs.openzeppelin.com/defender/migration)

The relevant current substitute is a toolchain: Upgrades validation, Safe/governance controls, Relayer and Monitor.

| Question | Finding |
| --- | --- |
| 1. Exact binding | **D:** governance operations can bind calls; **C:** relay preparation/signing is separate. An application request must not be equated with final fee/nonce bytes. [Governance](https://docs.openzeppelin.com/contracts/5.x/api/governance), [EVM relayer](https://docs.openzeppelin.com/relayer/1.5.x/evm) |
| 2. Pre-sign simulation | **D:** upgrade validation; **I:** external EVM simulation in the release pipeline. Static layout validation is not full transaction simulation. [Upgrades CLI](https://docs.openzeppelin.com/upgrades-plugins/api-core) |
| 3. Pre-sign policy | **D:** relayer configuration has policy controls. Governance contracts enforce access/delay at execution, not necessarily signature creation. [Relayer config](https://docs.openzeppelin.com/relayer/configuration), [access control](https://docs.openzeppelin.com/contracts/5.x/access-control) |
| 4. Independent predicate attesters | **I:** independent release reviewers and signers can compose reports. **U:** a native multi-provider predicate receipt standard. |
| 5. Portable evidence | **D:** local build inputs, validation reports and on-chain governance records; self-hosted infrastructure. **U:** automatic signed evidence package linking all of them. [Upgrades CLI](https://docs.openzeppelin.com/upgrades-plugins/api-core), [migration](https://docs.openzeppelin.com/defender/migration) |
| 6. Independent reason verification | **D/C:** retained build/reference inputs support re-running upgrade checks; public contract logic supports governance verification. Custom business judgment remains external. |
| 7. Retained inputs/outcomes | **C:** customer owns CI artifacts and self-hosted records; retention must be configured. No complete built-in signed predicate archive is established. |
| 8. All signing paths mandatory | **C:** on-chain sole authority and self-administered timelock can constrain privileged execution. Local/KMS signer administration remains separate. [Access control](https://docs.openzeppelin.com/contracts/5.x/access-control), [signers](https://docs.openzeppelin.com/relayer/1.5.x/configuration/signers) |
| 9. Upgrade/admin workflow | **D:** upgrade safety/storage-layout checks and role/delay management are explicit core purposes. [Upgrades CLI](https://docs.openzeppelin.com/upgrades-plugins/api-core), [access control](https://docs.openzeppelin.com/contracts/5.x/access-control) |
| 10. Essentially the value? | **Strong practical substitute when composed with a custody platform.** ProofGate would mostly connect and retain existing checks; evaluate that as integration work, not new security technology. |

A reference layout must be supplied to obtain meaningful compatibility checks; available override/skip options matter. Signing “validation passed” without retaining the actual reference, flags and build is weak evidence. ProofGate would inherit this configuration problem. [Validation options](https://docs.openzeppelin.com/upgrades-plugins/api-core)

## Material adjacent competitor: Forta Firewall

Forta is included because requiring a security attestation at a contract is closer to the claimed mandatory control point than a wallet UI. Tenderly/Blockaid and Hypernative are covered as documented Safe integrations above; this is not a claim to have evaluated their full standalone offerings.

| Question | Finding |
| --- | --- |
| 1. Exact binding | **D:** specified transactions require security attestations. **U:** the overview alone does not establish every digest field, scope and replay property. [Protocol integration](https://docs.forta.network/en/latest/what-is-forta-firewall/) |
| 2. Pre-sign simulation | **D:** simulation-based pre-inclusion screening. This can occur after signing, so it is not necessarily pre-sign. [Overview](https://docs.forta.network/en/latest/forta-firewall-overview/) |
| 3. Pre-sign policy | **D:** pre-execution filtering; **U:** a general HSM/wallet pre-sign policy hook. |
| 4. Independent predicate attesters | **U:** independent role-specific predicate coverage/quorum is not established by these overviews. |
| 5. Portable evidence | **D:** contract-consumed attestations. **U:** customer-controlled complete decision-input/predicate export. [Protocol integration](https://docs.forta.network/en/latest/what-is-forta-firewall/) |
| 6. Independent reason verification | **C:** contract validation can be inspected. **U:** reproducing the entire model's security judgment from its attestation. |
| 7. Retained inputs/outcomes | **D:** monitoring/governance signals documented. **U:** complete retained replay package and retention terms. [Monitoring](https://docs.forta.network/en/latest/forta-firewall-monitoring/) |
| 8. All signing paths mandatory | **C:** protected contract execution can require an attestation regardless of signing channel. Removal, coverage and delayed-access behavior remain material. [Protocol integration](https://docs.forta.network/en/latest/what-is-forta-firewall/) |
| 9. Upgrade/admin workflow | **D:** governance, oracle, bridge and multisig-change monitoring. **U:** dedicated release/build compatibility review. [Monitoring](https://docs.forta.network/en/latest/forta-firewall-monitoring/) |
| 10. Essentially the value? | **Substantial overlap with evidence-gated execution.** Not the same evidence semantics, but it defeats a novelty claim for requiring a prior security attestation on-chain. |

Forta's docs also describe delaying flagged activity for censorship resistance. Do not infer a permanent-denial or every-path guarantee from a high-level “blocks attacks” statement. Its full threat-model and deployed code were not audited in this review. [Overview](https://docs.forta.network/en/latest/forta-firewall-overview/)

## Attack on the seven administrative use cases

The cases below are architecture thought experiments, not newly reproduced exploits. “Prevent” means the gate actually blocks an action on a mandatory path. Evidence archived after a signature is generated is not prevention. Incumbent configurations and conventional controls are the comparison baseline.

| Case and concrete failure | Existing adequate control or substitute | Incremental ProofGate claim under attack | Judgment |
| --- | --- | --- | --- |
| Proxy implementation upgrade: an approved release is replaced with another implementation; initializer calldata or layout reference is wrong | Bind Safe/custodian approval to exact call; independently compare deployed code/build; OpenZeppelin validates layout with a reference; timelock permits review. | Require separately signed artifact, code and layout evidence for that call. | Could enforce completion of a review that a team currently skips. A callback or mandatory reviewer can do the same. No convincing unique prevention mechanism. Incorrect reference artifacts or malicious but layout-compatible logic still pass. |
| Protocol parameter change: correct method, wrong units or dangerous interaction with another parameter | ABI parameter rules, independent decoded review, fork simulation, contract range constraints, governance delay. | Multiple predicates prove the new configuration is acceptable. | The hard asset is the protocol-specific economic model, not the receipt. A shared wrong model yields multiple valid signatures. No demonstrated gap in incumbents' ability to enforce supplied checks. |
| Mint/burn authority: grant unlimited minter rights or mint to a wrong beneficiary | Separate roles, amount/destination policies, issuance caps, contract-level limits and multisig approval for role changes. | Require issuance evidence and an independently approved amount. | Custom approvals already accept business evidence. A one-time role grant may authorize unlimited future effects; per-transaction admission cannot govern later mints by a different authorized key. |
| Oracle replacement: valid new address has wrong decimals, stale values or attacker-controlled governance | Exact address/method approval, feed review, fork tests, sanity/staleness checks and delayed activation. | Attest the feed is correct at approval. | A snapshot cannot establish future honesty. Incumbents can require the same checks; continued bounds belong in protocol logic/monitoring. No convincing exclusive prevention claim. |
| Bridge validator/admin change: weaken a threshold or replace validators while cross-chain messages are pending | Role-controlled configuration, threshold checks, independent operational review, staged activation and bridge-specific monitoring. | Bind approved validator set and attest safe transition. | Receipt adds attribution, not cross-chain consistency. The bridge-specific transition analysis is required with any signer; a same-chain signature does not govern remote authority or pending messages. |
| Treasury ownership/admin change: an innocuous-looking call changes owners, threshold, module or implementation | Safe configuration/delegatecall warnings, independent hash review, guard enforcement and delayed ownership transfer. | Reject hidden authority changes using an expected post-state. | Existing warnings/guards address this category. A precise custom predicate could improve a weak configuration but is not ProofGate-specific. Uncovered modules or other admin keys defeat it. |
| Emergency pause/unpause: delay an urgent pause, or unpause before remediation is safe | Narrow pause-only authority; stronger review/delay for unpause; incident procedures and existing monitoring. | Require full independent evidence for every privileged action. | Potential negative value: unavailable reviewers can prolong an exploit. A bypass restores availability but falsifies universal gating. Separate emergency authority must be acknowledged; signatures do not prove remediation completeness. |

The supporting existing controls are documented in [OpenZeppelin access control](https://docs.openzeppelin.com/contracts/5.x/access-control), [upgrade validation](https://docs.openzeppelin.com/upgrades-plugins/api-core), [Fordefi ABI rules](https://docs.fordefi.com/user-guide/policies/policy-rules-conditions-and-actions), and [Safe configuration warnings](https://help.safe.global/articles/4308960633-why-do-i-see-an-unexpected-delegate-call-warning-in-my-transaction). The more specialized protocol checks in the table are proposed comparison practices, not claims that those vendors automatically implement every economic test.

Across all seven cases, the plausible gain is disciplined execution and portable attribution of checks someone must author and operate anyway. That might be useful, but the review found no well-supported failure class that requires ProofGate rather than a configured incumbent. Rare actions also favor careful human review and reduce opportunities to amortize a new platform.

## Mandatory-control-point objection

There are two different objectives:

- **No signature without a receipt:** the receipt check must be a required part of every usable signing path.
- **No privileged effect without a receipt:** the account/target must reject the effect even when someone has already obtained a signature elsewhere.

A smart-contract guard can achieve the second within its scope. It cannot stop an EOA from producing signature bytes. Conflating these objectives overstates an on-chain integration.

| Integration model | What would actually be required | Adversarial conclusion |
| --- | --- | --- |
| Optional application or approval bot | All callers voluntarily use it | Fails: alternate SDK, console, raw-sign or direct-key path bypasses it. Logging the bypass is not prevention. |
| Custodian/MPC mandatory callback | Final preimage visible; receipt checked on every signing route; gate identity is indispensable; no auto-approval alternative; policy changes and recovery governed; remote idempotency bound to payload | Can enforce signature admission within explicitly trusted platform/admin assumptions. Existing callbacks already provide the control point; ProofGate adds rule/evidence packaging. |
| HSM behind exclusive gateway | Only gateway can invoke the relevant key; unexportable key; no alternate admin capability can sign, clone or change enforcement outside the stated trust model | Key isolation alone is insufficient. A compromised allowed gateway can approve arbitrary digests unless trusted enforcement is at/below it. “Non-custodial” does not make this component low risk. |
| Safe guard/module guard | Correct deployed-version coverage; all execution paths checked; owners/modules/fallback/upgrade and removal routes reviewed; unauthorized guard removal blocked | Can enforce covered effects. A normal transaction guard is not proof of module coverage. A sufficient owner quorum outside the gateway still generates signatures. |
| Smart-account validation or sole contract-level authority | Every privileged entry path checks bound authorization and relevant live predicates; no alternate role, delegatecall or upgrade path can remove that requirement unnoticed | Strongest model for effect enforcement. Requires suitable existing contracts or contract/account changes, audit and governance choices. Not a free off-chain adapter. |
| Direct EOA admin key retained elsewhere | Another holder can sign or call the privileged target | Cannot guarantee the gate. Moving only routine workflows into ProofGate changes convenience, not authority. |
| Break-glass path | Explicit scope, independent authority, monitoring and stated exceptions | An unconditional emergency bypass disproves universal gating. Requiring the same unavailable gate can defeat emergency recovery. Neither tradeoff disappears in a receipt format. |

The comparison uses documented [Fireblocks routing/callback behavior](https://developers.fireblocks.com/docs/cosigner-architecture-overview), [Turnkey root override](https://docs.turnkey.com/features/policies/overview), [Safe module authorization](https://docs.safe.global/advanced/smart-account-concepts), and [module guard interface](https://docs.safe.global/reference-smart-account/guards/setModuleGuard). These are architectural constraints, not allegations of vulnerabilities.

For the literal sequence `receipt -> mandatory signer policy -> signature`, the credible model is a signer-level required policy/hook, with final-byte binding and all alternative credentials and policy administration covered by the threat model. For effects despite compromised signing paths, sole contract/account enforcement is stronger. Neither gives an absolute guarantee against its own trusted administrators, arbitrary implementation bugs or later governance changes.

A further problem is recursive authority: who can change the required gate, verifier keys, policy digest or emergency role? If the same authority can silently disable the condition, “mandatory” is configuration-contingent. Governance can make this visible or delayed; it cannot turn all governance actors into untrusted parties without changing the system's control model.

ProofGate's present local replay reservation also does not provide atomic commitment with a remote signer. Timeouts can strand admission; retrying can duplicate remote work unless the provider gives durable payload-bound idempotency. The product would inherit operational responsibility for that integration.

## State change and TOCTOU

An off-chain receipt can remain meaningful as historical evidence: named verifiers checked specified inputs under policy at a stated observation. It cannot remain an unconditional certificate that inclusion will have the same effects.

| Change after verification | What breaks | Consequence for the proposed wedge |
| --- | --- | --- |
| State changes after simulation | Balances, permissions or dependency state differ | Recheck signing-time conditions; only execution-time conditions can close the final gap |
| Mempool delay | Snapshot/freshness assumptions expire | Receipt expiry prevents new signing, not later submission of already signed bytes |
| Fee bump | EOA signing preimage changes | Exact-byte profile needs fresh authorization; a Safe outer relayer fee change may leave the inner admin action unchanged, but is a different scope |
| Transaction replacement | Same nonce can now authorize different effects | Require new review and link alternatives; the earlier signed transaction may still win |
| Proxy/contract state change | Identical calldata resolves to different code/roles | Code hash of a proxy alone is insufficient; recheck implementation state and use execution-time protection where needed |
| Reorg | Observation block and prior inclusion may leave the canonical chain | Retain contradictory observations; do not unspend authorization or call an orphaned receipt final |
| Oracle update | A correct signing-time quote/reading changes | Pin reference evidence but enforce live ranges/staleness where material |
| MEV/order manipulation | Transaction is sandwiched or preceded by a state-changing call | Simulation and honest signatures do not control ordering; economic bounds must survive execution |
| Nonce race | Another legitimate signer consumes or competes for the nonce | Shared account coordination and business-operation identity are needed beyond ProofGate's receipt nonce |

The distinction between signing and chain execution follows the [Ethereum transaction model](https://ethereum.org/developers/docs/transactions/); exact fee-field binding follows [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559). Proxy dependency resolution is explicit in [ERC-1967](https://eips.ethereum.org/EIPS/eip-1967). The failure analysis above is inference from these semantics, not a measured attack result.

No off-chain receipt solves TOCTOU alone. Rechecking at signing narrows the window, while contract-enforced preconditions can reject unacceptable inclusion state. Some predicates are not enforceable on-chain or cannot be made predictive: future oracle integrity, economic desirability, or the safety of every possible new implementation behavior. Those require narrower claims regardless of custody provider.

Private submission may reduce some exposure but is not a proof of ordering or inclusion-state equivalence. Exactly-once financial effects, signature revocation by local expiry, and guaranteed bridge finality are outside the capability of this gate.

## Buyer/value test

The least-disproved use case is **reconstructible upgrade-release evidence for a protocol using more than one custody/approval organization**. This is narrower than a generic transaction security product and is not yet validated.

| Buyer question | Adversarial answer |
| --- | --- |
| Buyer | Protocol foundation's security/engineering lead, with an accountable release owner; finance or a security council may approve procurement. No actual buyer was interviewed. |
| Loss to reduce | Wrong implementation/initializer/authority accepted during a privileged release; also review and post-incident reconstruction effort. No loss reduction or frequency was measured. |
| Existing workflow | A plausible baseline is build artifacts plus upgrade checks, independent calldata/hash review and simulation, then Safe/custodian approvals and a timelock. This is a documented-tool composition, not a claim every protocol uses it. |
| Why existing products insufficient | **Not established.** A gap would require a reviewer unable to reconstruct necessary decisions from current proofs, API exports and retained CI artifacts without material recurring work. |
| Integration burden | Separate trust domains, pinned artifacts and evidence retention; multiple signer/account profiles; mandatory policy routing; state/nonce handling; incident recovery; possible account/contract audit. This is a security product integration, not attaching a PDF. |
| Procurement objection | Another small vendor in the critical release path, more outage/liability exposure, unclear responsibility when all checks pass a harmful action, and overlap with paid custody/security providers. |
| Why pay rather than configure incumbents? | Only a demonstrated reduction in cross-organization review/reconstruction effort or a specific enforceable missed check that current tooling cannot deliver economically. There is no validated evidence for either today. |

The no-product baseline is serious: retain signed release manifests and existing vendor proofs alongside CI outputs, with independent reviewers checking the exact transaction. Even where this needs glue, the buyer may prefer one small integration to adopting a new protocol. A custom integration project is not automatically a repeatable product.

Reviewers outside the custody platform must still agree on policy meaning, evidence quality, confidentiality, verifier identities and responsibility. A common syntax cannot create that agreement. Nor does a signature prove that a human/organization did competent work. PQ signatures may protect evidence authentication under their assumptions, but do not establish an immediate budget, prevent chain-signature compromise, or differentiate the core operational control from incumbents.

## Surviving differentiation

These are **unvalidated hypotheses**, not proven product advantages:

1. A custody-neutral evidence package that exposes named predicates and retains sufficient inputs for third-party replay across independently operated approval organizations.
2. Reusable links between exact privileged-call bytes and separately managed release/build/semantic reviews, reducing repeated integration work across signer vendors.

Both can potentially be assembled with existing tools. Neither establishes unique prevention, willingness to pay, or a reason to modify ProofGate today. The current implementation also requires every verifier's full predicate dictionary to agree with the same evaluator; heterogeneous specialty attestations are not an existing feature. See the [prior core assessment](crypto-treasury-design.md#11-core-change-assessment).

## Strongest competitor

**Turnkey / Turnkey Verified.** It most directly counters the claimed evidence differentiator: signed policy outcomes and public proof verification already exist, with a separate API for policy-level results. Its full offline input-replay coverage remains to be established, but calling it an opaque approval log would be inaccurate. [Proof format](https://docs.turnkey.com/security/turnkey-verified), [evaluation results](https://docs.turnkey.com/api-reference/queries/get-policy-evaluations)

Safe plus existing upgrade/governance/security tooling is the strongest practical workflow substitute; this does not change the selection of Turnkey as the strongest direct competitor to the receipt proposition.

## Strongest technical objection

The receipt must govern an indispensable signing capability or the sole privileged execution path, including changes to that governance itself. Otherwise it is optional evidence. Making it indispensable requires custody-specific policy integration or audited account/contract controls, introduces a trusted enforcement component, and conflicts with some emergency recovery paths. Even perfect enforcement of the approved bytes does not ensure approved effects after state changes. ProofGate currently supplies neither the required remote-signing lifecycle nor heterogeneous predicate evaluation, so the market hypothesis relies on unbuilt security-critical functionality.

## Strongest commercial objection

The buyer already needs custody policy, secure release engineering, simulation, governance and incident procedures. Incumbents and open-source tooling provide much of each. ProofGate would ask that buyer to add another critical dependency to standardize evidence without a demonstrated incremental failure prevented or measured reduction in work. The residual opportunity could be bespoke integration/assurance services rather than a scalable product, and rare actions may not generate enough repeated pain to justify ongoing operation. Willingness to pay is entirely unvalidated; this review supplies no pricing estimate.

## What not to build

- A new wallet, MPC service, HSM wrapper, token or custody platform.
- Generic amount/recipient/ABI approval rules or another simulation dashboard.
- A replacement upgrade-layout checker, governor, timelock or emergency pauser.
- A new on-chain guard/firewall solely to rescue the claim that the existing gate is mandatory.
- Heterogeneous-verifier protocol extensions before proving a customer needs them.
- Broad chain/account support, bridge settlement orchestration or automatic fee-replacement machinery.
- AI risk scoring or an AML product.
- PQ branding that implies quantum-safe assets or compensates for missing buyer value.
- A portable evidence schema standard before comparing real exports and reviewer requirements.

## Single next experiment

Run **one buyer-assisted existing-tool substitution exercise on one completed, redacted protocol upgrade**. No new code, live signing, keys, chain transactions or ProofGate prototype.

With one accountable release owner and one reviewer outside the signing organization, assemble the already retained build/reference artifacts, calldata, simulation results, approvals and vendor exports. Include a representative Turnkey Policy Outcome Proof/context/evaluation export when accessible, or obtain a vendor-supported demonstration as part of this same exercise. Attempt to reconstruct exactly which required checks authorized the release using current tools. In the same case review, enumerate actual signer/admin/recovery routes and obtain the platform-specific explanation of how a required external review could be enforced.

The exercise changes confidence only if it identifies a **specific necessary evidence/review gap**, shows that normal incumbent configuration/export cannot adequately close it, confirms a mandatory integration point under acceptable assumptions, and obtains a named buyer's commitment to sponsor evaluation of that exact gap. Record observed reviewer effort and missing inputs; do not invent savings or infer willingness to pay from enthusiasm.

If the existing artifacts suffice, the purported gap reduces to documentation hygiene, or the buyer will not accept mandatory integration, abandon this wedge. If artifacts or a responsible buyer cannot be obtained, keep implementation blocked rather than build a demo to manufacture interest. This experiment has not been performed and no outreach is authorized by this document.

### HOLD

Potential evidence-interchange differentiation remains, but the competitor evidence defeats the broad novelty claim and no unique prevention or commercial value is established. Mandatory enforcement, realistic input retention and buyer demand are unresolved. **Implementation should not begin.** The single next experiment is the existing-tool substitution exercise above.
