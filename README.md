# Website generator benchmark

A standalone, evidence-first benchmark site for Nift comparisons.

The primary workload is a **10,000-page clean production build** using pinned Nift, Hugo, Astro and VitePress versions. Fixture generation and dependency installation are outside timed runs. The harness performs warmups followed by repeated measured builds and refuses to write a partial comparison.

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
  --warmups 2 \
  --repetitions 7 \
  --output evidence/results.json
```

Raw results belong in `evidence/results.json` and should be committed alongside the website revision that interprets them.

Progress is printed live to stderr before and after every warmup/measured run, so a long generator cannot look like a hung process.

## Evidence rule

Do not publish a comparative result unless all requested tools complete the same retained run. Do not substitute historical numbers for a failed or incomplete run.
