# Website generator benchmark

A standalone, evidence-first benchmark site for Nift comparisons.

The primary workload is a **10,000-page clean production build** using Nift, Hugo, Astro and VitePress, recording both wall-clock time and peak aggregate process-tree RSS. Fixture generation and dependency installation are outside timed runs. The harness performs warmups followed by repeated measured builds and refuses to write a partial comparison.

## Pinned competitors

- Hugo 0.164.0
- Astro 7.2.4
- VitePress 1.6.4

Nift is supplied explicitly with `--nift`, so the result records the exact binary version actually measured.

## Setup

```sh
./scripts/setup-tools.sh
```

That downloads the pinned Hugo binary for the current Linux/macOS host and installs the pinned Node dependencies locally.

## Run

From this repository, with a built Nift binary:

```sh
python3 -u scripts/benchmark.py \
  --nift /path/to/nift \
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
