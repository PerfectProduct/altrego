# C0 external-source review

Reading-only research under ADR-054. No external research code was installed or
executed. Dates below refer to this session (2026-10-15, Europe/Moscow).
This note records ideas for the experiment, not promotion into Altrego canon.

| Candidate | Primary material read | C0 disposition |
|---|---|---|
| NB-27 | Saved analysis in ADR-054 annotation 14 | Apply frozen manifest, complete attempt accounting, protected evaluation and symmetric pair exclusion. No new Ouroboros implementation study. |
| NB-50 | [Scaffold effects, v1](https://arxiv.org/html/2607.22585v1), main methods/results/limitations | Compare complete configurations under equal external constraints; preserve all costs and failures. Do not equate idle-time proxies with owner active minutes or attribute a difference to one process component. Small samples remain descriptive. |
| NB-51 | [Harness-Bench, v1](https://arxiv.org/html/2605.27922v1), sections 3–4.1 | Separate setup, execution and evaluation. Retain final artifacts, tool traces, usage and validator output. Report outcomes and process diagnostics separately; do not adopt its multiplicative composite or paid judge. |
| NB-52a | [BenchJack, v1](https://arxiv.org/html/2605.12673v1), sections 3–4.1 and appendix C | Audit evaluator trust boundaries before runs: builder cannot reach tests or score files; service stdout cannot become the score; use independent test execution and negative controls. Scope network and host access. No BenchJack installation or exploit execution. |
| NB-52b | [Protocol validity, v1](https://arxiv.org/html/2607.22368v1), sections 3–4 and evidence schema | Distinguish reachable information, observed use and demonstrated scoring effect. Keep exact evidence pointers and uncertainty. C0 still applies the owner's conservative symmetric exclusion rule; an exclusion is not automatically proof of reward hacking. |

The four articles were available as primary arXiv HTML. Their publication claims
and reported experiments were not independently reproduced. Reading these
methods closes the preliminary study step; implementing and validating the
resulting controls remains an outstanding prerequisite to measured execution.

RepoGenesis is the external source of requirements and tests. Public availability,
possible training contamination and a shared operator limit independence. The
upstream historical baseline cannot substitute for this campaign's control arm.

Official source metadata was fetched from `microsoft/DKI_LLM`, pinned at
`c090b7d57e3996c8900e86fecd16085b27e07f29`. The root MIT license was read.
Embedded-task provenance and terms still need inspection; root MIT alone does
not establish all nested rights. The source tree contains 30 task directories
and an evaluator specification of 22 Python and 8 Java tasks. This pilot samples
only the Python stratum, as declared before requirement reading.

Initial evaluator inspection found two matters requiring explicit treatment:
`test_spec.py` defaults to dataset directories absent from this checkout, and
`grading.py` derives scores from text logs. The campaign must use the actual
published task paths and prevent generated service output from impersonating
trusted test results. An adaptation must be documented and smoke-tested; it
cannot be called an unmodified upstream harness.
