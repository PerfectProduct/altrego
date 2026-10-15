# C0 evaluator and preflight record

Status: preparation; zero measured attempts. The campaign manifest is not sealed.

The selected source revision and file hashes are in `source-inventory-v1.json`.
The root Microsoft MIT grant covers the published RepoGenesis subtree; no nested
license files were found there. Independent provenance of embedded requirement
text remains unknown. No third-party implementation was copied into the repo.
Local source retains its upstream license. Runtime dependencies have their own
licenses, recorded in `reports/c0-recovery/wheel-review.json`.

The isolated runtime has 35 pinned wheels in `runtime-lock.txt`. Wheels were
statically inspected, checked against primary PyPI release hashes and installed
offline without dependency resolution or source builds. This is a bounded
provenance/execution review, not a comprehensive dependency security audit.

`evaluate.py` is a declared adaptation of upstream execution, not an unmodified
RepoGenesis runner. It keeps the original test assertions and uses the actual
published test paths. A trusted supervisor starts the candidate service and test
runner in separate filesystem/PID sandboxes sharing only private loopback. Tests
are read-only; the service cannot see tests or score files. The scorer reads
trusted JUnit or RBAC result objects, never service stdout. Evaluation has no
external network or credentials. Each child gets two CPUs and a 4 GiB address
space limit; startup and test deadlines are explicit command arguments.

Expected test counts were collected before any candidate existed:

| Task | Expected checks | Collection |
|---|---:|---|
| TaskManagement | 44 | pytest |
| WebPan | 22 | pytest |
| simple-rbac-service | 9 | original custom runner, `rbac_adapter.py` |
| Chatroom | 9 | pytest |
| Multilingual | 33 | pytest |

`oracle-collection-v1.json` records full pytest identifiers. RBAC intentionally
returns pytest collection exit 5: its custom runner is not pytest-collectable.
The adapter retains its original check order and records unexecuted dependent
checks as skipped in the fixed denominator. Success requires every expected
check to pass, a successful test exit, and no timeout. Missing reports, omitted
checks and skips cannot produce full success.

All imported external test files, conftest files and pytest configurations were
read completely before collection. Review and exact source hashes are in
`reports/c0-recovery/oracle-execution-review.json`. The first request to collect
was rejected by automatic approval review because the earlier AST-only review
was insufficient; collection was approved after full reading. An earlier
package-install rejection was likewise resolved by wheel inspection and hash
verification before offline installation. Neither refusal was bypassed.

Observed limitations of the external oracle, without changing its assertions:

- WebPan's multiple-upload test has a faulty cleanup expression after tuple
  unpacking (`file_obj[1][1]`); this appears capable of failing independently of
  service correctness. Its session fixture also requires a health endpoint not
  specified in its brief. Preserve raw outcomes and identify such failures.
- Several Multilingual assertions test nonempty output rather than translation
  or locale semantics. Passing them does not establish a working translator.
- Fixtures may skip when a service is unavailable; skips remain nonpasses.
- Several HTTP requests lack per-request deadlines; the outer deadline bounds
  total runtime, and partial evidence must not shrink the expected denominator.
- Public tests may have appeared in training. Access isolation does not remove
  that possibility. A shared operator knows the tests and must limit builder
  handoffs/reviews to original requirements and process, with no test hints.

Synthetic evaluator checks under `/tmp/c0-eval-smoke` (also archived in local
reports) include positive 3/3, negative 2/3, service stdout spoofing, mutual
filesystem invisibility, omitted RBAC checks (1/9), and a denominator mismatch
(3 passing tests against expected 4: not full success). An initial localhost DNS
failure and its static-hosts correction are retained. None uses a selected task
solution. CLI runner smoke is separate; details and failures are archived under
`reports/c0-recovery/runner-smoke/`. Planning writes were denied by a Linux
read-only mount, then the same context successfully resumed with workspace
writes. Runtime mutation, client credentials, repo/source and proc-root source
reads were denied. Tool inventory contained eight native tools and no apps/MCP.
Direct `http.client` localhost requests passed; proxy-aware clients returned 502
even with NO_PROXY. Common builder instructions disclose this limitation.
All of this is preflight evidence, not a benchmark result.
