# C0 protocol: pending final seal

This document is not the immutable campaign manifest. No measured attempt may
start until preflight is complete and the full manifest plus hash seal exists.

The unit is a task pair, five selected Python tasks, ten main attempts, in the
order already committed in `selection-v1.json`. Each arm receives an exact copy
of the same original README and starts a fresh CLI context. No other task's
solution, trace or evaluation feedback enters a builder context. The current
controller never implements either arm's solution.

Common configuration: Codex CLI 0.160.0, gpt-6-astra, medium reasoning, existing
ChatGPT subscription, disabled apps/plugins/browser/web/MCP, clean CODEX_HOME,
explicit workspace, reviewed Python runtime, localhost-only command network.
No package downloads or external service calls during building/evaluation.
These offline constraints limit generalization, particularly for requirements
that could naturally use a translation provider. They apply equally to both
arms and are stated to builders before work starts. Runtime wheel versions and
hashes are fixed, not selected from observed task success.

Proposed equal limits: 1,800 active CLI wall-clock seconds per attempt, at most
eight stages in the same context, two available CPUs by affinity. Thirty minutes
allows implementation and local tests of one small service plus process work,
while bounding stalls and subscription use. The process overhead consumes the
same budget. Owner waiting is excluded from active CLI runtime and separately
recorded. There is no claimed hard token cap or total-memory quota for the CLI;
tokens are observed from actual usage events. CLI 0.160.0 emits cumulative
context totals on resume (verified against raw token_count events); use the
last total per attempt, and differences for stages, never sum cumulative totals.
Partial/absent usage after failure remains explicitly incomplete. Evaluation children separately
have a 4 GiB virtual-address limit, 15 seconds startup, 300 seconds tests. No
additional money may be spent; subscription counters unavailable to the CLI
are “not measured”, not zero.

Control receives the original brief plus common runtime/submission instructions
and implements it normally. It has no Altrego instructions, memories or tools.
Altrego receives the same brief and resources plus the applicable frozen process:

1. Actual owner signature of the unchanged brief. Passive intake scores remain
   observational in C0 and neither rewrite nor remove tasks.
2. Spec and bounded implementation plan in enforced read-only mode. The builder
   drafts the requirement/architecture/validation documentation and docs spine;
   the controller only transports its text, without authoring a solution.
3. Orchestrator scope/process review against the brief and cited sources. No
   hidden-test feedback or implementation hints. Narrow process corrections
   return to the same builder context and count against its limits.
4. Actual owner acceptance of documentation and execution go-ahead, with the
   exact signed artifact hash and reply retained. Neither is synthesized.
5. Build in the same context with workspace writes enabled; original scope,
   executable self-tests, evidence-backed report and documented deferrals.
6. Review/report against signed intent and process. Owner acceptance is explicit
   when provided; pending acceptance is not represented as completed.

The generic delivery roles, priority, phase lock, plan review, decision authority,
provenance, safe writes, executable validation and two constitutional signatures
apply. TheyGrow-specific product architecture, release/deployment surfaces and
M1 work do not become requirements of unrelated benchmark services. This is an
application map of the existing process, not a canonical amendment. Any further
mandatory gate found in source review must be reflected before the seal.

No measured retry or fresh-context reset after failure. Subscription exhaustion
preserves the same context and evidence; a later continuation is allowed only
if recorded as such, without changing model/configuration or discarding costs.
A substantive completed build is sealed before evaluation; no oracle feedback
is returned for repair. Infrastructure failures, timeout, missing submission and
owner-gate waiting remain distinct statuses. All ten planned entries remain in
the ledger. A blocked or unexecuted attempt is not a test success.

Primary outcome: all fixed expected external tests pass, nonempty trusted report,
exit zero, no skipped/omitted tests or timeout. Report partial pass counts with
the original expected denominator as well. Preserve oracle defects and separate
interpretation from raw results. No adjustment to assertions after outcomes.

The append-only journal records planning, actual starts/stops, prompts, context
IDs, hashes, owner gates, costs, artifact seals, failures and evaluations. Every
trace is reviewed for reference/test access and evaluation tampering; exposure,
use and demonstrated score effects are distinguished. Contamination of either
arm excludes both members from the clean comparison while retaining them in
the full five-pair/ten-attempt denominator.

Owner workload: self-reported active minutes, plus actual handoffs, repeated
explanations and interventions. Never infer active minutes from message gaps.
Keep study preparation separate from measured per-arm workload. Process review
records K1–K7 with evidence and uncertainty; mechanical linter coverage and
findings are a separate measure, with not_measured/infra/calibration results.

The external source is independent of Altrego's local corpus; public exposure,
possible training contamination and the common operator limit that independence.
Five pairs support descriptive findings only. No universal superiority, autonomy,
D2/D3 claim or M1 execution follows from these results.
