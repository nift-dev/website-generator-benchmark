# Website generator benchmark

A standalone, evidence-first benchmark site for Nift comparisons.

The primary workload is a **10,000-page clean production build** using Nift, Hugo, Astro and VitePress, recording both wall-clock time and peak aggregate process-tree RSS. Fixture generation and dependency installation are outside timed runs. The harness performs warmups followed by repeated measured builds and refuses to write a partial comparison.

## Pinned competitors

- Hugo 0.164.0
- Astro 7.2.4
- VitePress 1.6.4

Nift is installed by `setup-tools.sh` from the official installer
(`curl -fsSL https://nift.dev/install | sh`) into `.benchmark-tools/`, so the
result records the exact binary version actually measured. To reproduce a
specific Nift release, set `NIFT_VERSION` before running setup (the installer
honours it).

## Setup

```sh
./scripts/setup-tools.sh
```

That installs the latest official Nift release, downloads the pinned Hugo
binary for the current Linux/macOS host, and installs the pinned Node
dependencies locally.

## Run

From this repository, with the tools installed by setup:

```sh
python3 -u scripts/benchmark.py \
  --nift .benchmark-tools/nift \
  --hugo .benchmark-tools/hugo \
  --node-project . \
  --pages 10000 \
  --warmups 1 \
  --repetitions 3 \
  --output evidence/results.json
```

Raw results belong in `evidence/results.json` and should be committed alongside the website revision that interprets them. Each measured run records elapsed seconds and peak aggregate RSS in MiB.

Progress is printed live to stderr from startup onward: dependency checks, version detection, fixture generation, and every warmup/measured run. A slow phase should never look like a hung process.

## Evidence rule

Do not publish a comparative result unless all requested tools complete the same retained run. Do not substitute historical numbers for a failed or incomplete run.

## Published evidence

The current retained run is published at https://nift.dev/website-generator-benchmark/ and its raw JSON is retained verbatim as `evidence/results.json` and published byte-for-byte as `public/evidence/results.json`.

## Memory measurement

RAM is measured on Linux as **peak aggregate RSS across the spawned process group**, sampled every 10 ms while the build runs. This deliberately includes child processes used by Node-based generators instead of reporting only the parent CLI process.

Because the memory sampler runs during the same build, the retained timing and RAM samples describe the same measured repetitions. The harness currently refuses RAM benchmarking on non-Linux hosts rather than silently switching to a non-equivalent metric.

## Nift incremental measurements

The same run also records a separate **Nift-only development-loop benchmark** on the 10,000-page fixture. These numbers are intentionally not presented as cross-generator comparisons.

Three `nift build-updated` cases are retained with the same wall-clock + peak aggregate RSS measurements:

1. **No-op** — nothing changed.
2. **One page changed** — one independent content page is changed before each run.
3. **Shared template changed** — the common template is changed before each run, so all 10,000 outputs legitimately need rebuilding.

The one-page and shared-template cases mutate the fixture before every warmup/measured run and force a distinct filesystem timestamp so the modified-mode dependency check is deterministic even on filesystems with coarse timestamp resolution.

The resulting JSON uses schema 4 and stores these separately under `nift_incremental`. They should be interpreted as Nift iteration evidence, not compared directly with the clean production-build timings of Hugo, Astro or VitePress.

## Current retained result

The schema-4 run in `evidence/results.json` records, for 10,000-page clean builds:

- Nift: 0.165 s median, 10.0 MiB median peak aggregate RSS
- Hugo: 0.467 s, 237 MiB
- VitePress: 58.49 s, 3,687 MiB
- Astro: 124.79 s, 3,218 MiB

The same run records Nift `build-updated` medians of 0.100 s (no-op), 0.119 s (one page changed), and 0.176 s (shared template invalidating all 10,000 pages), with median peak RAM between 9.6 and 11.3 MiB.

## October campaign (new measurement protocol)

Use `scripts/campaign.py --nift PATH --hugo PATH --node-project . --pages 10000
--samples 5 --warmups 1 --output evidence/campaign-10000.json` for schema-5
measurements. `scripts/summarize.py --input FILE --output SUMMARY` verifies every
sample and retained summary. The old schema-4 evidence remains historical.

Schema 5 validates route/title/heading/body for every build, uses a minimal
VitePress theme (which still hydrates and generates a 404 page), enables Hugo raw
HTML and Astro file routes. It separates fresh-fixture application-cold and
warm full builds. Nift incremental output must agree byte-for-byte with a full
rebuild of the same mutated input. Direct C-supervised fork/exec latency excludes
Python orchestration; kernel wait4 child high-water RSS replaces sampled
aggregate RSS. These memory metrics are **not interchangeable**. Source/tool
preparation is outside timing. OS caches remain uncontrolled; this small-page
fixture measures generated-page throughput, not complete real-site equivalence.
