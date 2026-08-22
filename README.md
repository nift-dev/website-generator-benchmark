# Website generator benchmark

A standalone, evidence-first benchmark site for Nift comparisons.

The benchmark harness intentionally requires all compared tools before producing a result. It does not silently publish a partial comparison. The initial target is a 10,000-page clean production build using pinned Nift, Hugo and Astro versions, with warmups and seven measured repetitions.

See `scripts/benchmark.py`. Raw results belong in `evidence/results.json` and should be committed alongside the page that interprets them.
