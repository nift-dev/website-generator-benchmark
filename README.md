# Website Generator Benchmark

Correctness-gated Linux measurements of **minimal generated-page throughput** in
Nift, Hugo, Astro and VitePress. This synthetic fixture is not a real-site
migration or a universal SSG ranking. The October campaign audits are in
[evidence/CAMPAIGN-AUDIT.md](evidence/CAMPAIGN-AUDIT.md).

## Frozen tools

Official campaign: Nift 4.7.2, Hugo 0.167.0, Astro 7.3.6, VitePress 1.6.4,
Node.js 24.21.0. The package lock freezes transitive dependencies; raw evidence
records binaries' versions/hashes and OS/compiler/runtime metadata. Ubuntu distro
packages are retained in the shared provisioning manifest.

```sh
NIFT_VERSION=4.7.2 ./scripts/setup-tools.sh
python3 scripts/test_measurement.py
python3 scripts/campaign.py --nift .benchmark-tools/nift \
  --hugo .benchmark-tools/hugo --node-project . --pages 10000 \
  --samples 5 --warmups 1 --timeout 1200 --output evidence/campaign-10000.json
python3 scripts/summarize.py --input evidence/campaign-10000.json \
  --output evidence/campaign-10000-summary.json
```

Repeat at 100 and 1000 pages for the scaling matrix. Run serially with one logical
CPU affinity (`taskset -c 0` on the official node). Nift build threads=1 and Hugo
GOMAXPROCS=1. Dependencies, toolchain compilation and fixture generation are
outside all timed intervals.

For the disposable Ubuntu node, the sibling shell-benchmark repository's
`scripts/provision-tools.sh` prepares all three suites under `/opt/campaign` with
checksum-verified releases. Never execute that host provisioning script against
a personal workstation.

## What is measured

Schema 5 separates **fresh fixture** (raw mode `application-cold`, whole fixture recreated) from **warm
full** (generated output/cache directories removed, other application state
retained). Prepared pinned node_modules/toolchains and generated dependency caches are shared across runs. Astro/Vite creates `node_modules/.vite`; `.astro` may also exist there. This is a fresh-project-directory boundary, not a reset of all application caches. The campaign retains their inventory.
Neither mode flushes OS caches or claims machine-cold execution.

Every build checks the complete route inventory, exact page title/heading and
expected body. Hugo explicitly allows raw HTML. Astro uses file routes.
VitePress uses a minimal custom theme; its hydration assets and one extra 404
page remain part of the build and are disclosed. The fixture measures each
system's natural build path to equivalent simple page content, not byte-identical
browser applications.

A compiled C supervisor measures fork/exec through wait4 completion, excluding
Python orchestration and supervisor launch. Linux wait4 high-water RSS is a
waited-child maximum, **not simultaneous aggregate process-tree RSS**. No
10 ms polling loop quantizes short builds. Raw warmup/measured samples are
retained, tool order rotates, and correctness/timeouts stop publication.

Nift-only no-op, one-leaf and shared-template incremental cases are separate.
Every incremental output set must agree byte-for-byte with a full rebuild of the
same mutated input. They are not comparisons against competitors' dev/HMR modes.

## Historical evidence

`evidence/results.json` and the original standalone site's numbers retain the
August schema-4 experiment. They used different fixture/theme/configuration,
three repetitions, stale CLI spellings and sampled aggregate process-group RSS.
New results cannot be called speedups against those medians. The legacy runner
is retired; use Git history for its old implementation and methodology.

New reports are published in the Nift Labs benchmark family. Local pilot outputs
are validation evidence, not official comparative results.

### Explicit-target scaling supplement

`python3 scripts/targeted_campaign.py --nift /absolute/path/to/nift --samples 5 --warmups 1 --output evidence/targeted-builds.json` measures 100, 1,000 and 10,000-page corpora. Run serially with `taskset -c 0`; Nift 4.7.2 and a C compiler are required. Each pair creates a fresh fixture and measures a full build, then changes one leaf and measures `nift build page-1`. Complete content/route checks, unchanged unrelated page bytes, and equality with an untimed full rebuild gate every target sample. Fixture creation and validation are outside timing; OS caches are uncontrolled.

This supplemental run uses a separate disposable node. Keep its raw samples and machine metadata separate from the original campaign, and use its own full-build reference when interpreting targeted timings. An explicit target is distinct from ordinary dependency-scanning incremental `nift build`.
