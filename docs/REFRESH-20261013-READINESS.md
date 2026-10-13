# Near-release refresh readiness

Candidate: `7f7e487c47a87e871dfef53345e2b71288008bff`. This plan is additive; older evidence remains immutable.

The adjacent JSON freezes the established workload/sample plan and commands. Provision from a fresh detached core clone, never the local diagnostics workspace. Use `NIFT_BINARY` for a source-built executable when invoking tool setup; leave it unset only to reproduce the historical release installer default.

Existing comparator pins remain reasonable baseline versions, but the coordinator must verify current releases and finalize comparator identities before accepting timings. Apt runtime versions are not pinned by the historical installer: capture exact package versions, executables, linked libraries and hashes, then freeze installation; do not imply latest versions without verification. Framework version changes require a disclosed new participant cohort.

Each result must be a new immutable series. Run full correctness pilots before official measurement; preserve rejected evidence. No performance run has been executed by this preparation.
