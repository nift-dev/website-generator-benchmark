# October 2026 campaign audit — before implementation

Reviewed fixture constructors, runner, tool setup, package lock, retained schema-4
results and documentation.

Keep: preparation outside timing, clean output before full builds, pinned Node
packages/Hugo, raw samples, Nift-only incremental section, complete comparisons.

Improve (publication blockers):
- Exit success is the only correctness check. Validate exact expected route set,
  page titles/headings/body content after every full build; validate incremental
  outputs against the intended mutation and a clean rebuild.
- VitePress uses its full default documentation theme whereas other fixtures are
  bare HTML. Use a minimal custom VitePress theme; disclose its client hydration
  assets. Hugo must explicitly permit raw HTML rather than silently omitting it.
  This is a small generated-page throughput test, not a substantial real website.
- Nift tracked/dependency state survives output cleaning. Recreate entire fixture
  for application-cold samples; distinguish warm full builds preserving state
  from incremental builds. No OS cache flushing or machine-cold claims.
- Current timing loop scans all /proc entries and sleeps 10ms before detecting
  completion, materially quantizing short Nift builds. Measure elapsed time with
  direct wait; collect sampled aggregate group RSS in separate diagnostic runs.
  Sampling may miss short peaks and shared pages can be counted repeatedly.
- stderr pipe can block a verbose child; add timeout and process-group cleanup.
- Increase production repetitions to at least five; interleave/rotate tools;
  retain exact commands, revisions, versions, CPU affinity and host metadata.
- Require explicit Nift pin, use npm ci, record acquired binaries' hashes.

Remove: universal SSG-ranking claims from this synthetic workload, implication
that three samples establish stable distributions, and inference that sampled
RSS is exact memory consumption.

Add: warm/application-cold full-build matrix; 100/1000/10000-page scaling runs;
correctness-gate checks; machine inventory; independent memory samples. Retain
Nift-only changed-input cases because the competitors' incremental semantics
need a separately designed comparable server-mode experiment.

Comparability: correcting VitePress theme, Hugo content, cache state and timing
measurement changes the workload/measurement substantially. New numbers cannot
be presented as speedups against schema-4 evidence. Preserve old results.

Freshness check before official website timing: upgrade Hugo 0.164.0 → 0.167.0
and Astro 7.2.4 → 7.3.6 (current stable release metadata); VitePress remains 1.6.4.
Original pilot used the earlier pins; a new-version pilot must pass before timing.
