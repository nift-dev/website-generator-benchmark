#!/usr/bin/env python3
"""Reproducible Nift/Hugo/Astro/VitePress clean-build benchmark.

Fixture generation and dependency installation are outside the timed region.
Every requested tool must exist and every run must succeed before results are
written. This prevents partial comparisons from being mistaken for evidence.
"""
import argparse, json, os, platform, shutil, statistics, subprocess, sys, tempfile, time
from pathlib import Path

def _linux_process_group_rss_kib(pgid):
    """Return aggregate RSS KiB for all live processes in one Linux process group."""
    total=0
    proc=Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat_fields=(entry/"stat").read_text().split()
            if len(stat_fields) < 5 or int(stat_fields[4]) != pgid:
                continue
            for line in (entry/"status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total += int(line.split()[1])
                    break
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            continue
    return total

def run(cmd,cwd,env=None,measure_memory=True,poll_interval=0.01):
    """Run one build and return (elapsed_seconds, peak_aggregate_rss_kib).

    Memory is measured as aggregate RSS across the spawned process group on Linux,
    sampled every 10 ms. This captures Node child processes as well as the parent
    instead of reporting only the top-level CLI process.
    """
    if measure_memory and platform.system() != "Linux":
        raise RuntimeError("peak aggregate RSS measurement currently requires Linux")

    start=time.perf_counter()
    p=subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    peak_rss_kib=0

    while p.poll() is None:
        if measure_memory:
            try:
                peak_rss_kib=max(peak_rss_kib,_linux_process_group_rss_kib(p.pid))
            except FileNotFoundError:
                pass
        time.sleep(poll_interval)

    # Catch the final observable state if the process group still exists briefly.
    if measure_memory:
        try:
            peak_rss_kib=max(peak_rss_kib,_linux_process_group_rss_kib(p.pid))
        except FileNotFoundError:
            pass

    stderr=p.stderr.read() if p.stderr else ""
    elapsed=time.perf_counter()-start
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{stderr[-2000:]}")
    return elapsed,peak_rss_kib

def version(cmd,timeout=10):
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"version probe timed out after {timeout}s: {' '.join(cmd)}")
    if p.returncode:
        raise RuntimeError(f"version probe failed ({p.returncode}): {' '.join(cmd)}")
    return p.stdout.splitlines()[0].strip() if p.stdout else "unknown"

def package_version(project,name):
    path=Path(project).resolve()/"node_modules"/name/"package.json"
    try:
        return json.loads(path.read_text())["version"]
    except Exception as exc:
        raise RuntimeError(f"could not read installed {name} version from {path}: {exc}")

def link_node_modules(fixture,project):
    target=Path(project).resolve()/"node_modules"
    if not target.exists():
        raise RuntimeError(f"node_modules not found at {target}; run scripts/setup-tools.sh first")
    (fixture/"node_modules").symlink_to(target,target_is_directory=True)

def nift_fixture(base,n,nift):
    p=base/"nift"; (p/".nift").mkdir(parents=True); (p/"content").mkdir(); (p/"templates").mkdir()
    (p/".nift/config.json").write_text('{"config":{"content-dir":"content/","content-ext":".html","output-dir":"public/","output-ext":".html","default-template":"templates/template.html","build-threads":-1,"incremental-mode":"modified"}}')
    tracked=[]
    for i in range(n):
        name="/" if i==0 else f"page-{i}"
        tracked.append({"name":name,"title":f"Page {i}","template":"templates/template.html"})
        fn="index.html" if i==0 else f"page-{i}.html"
        (p/"content"/fn).write_text(f"<h1>Page {i}</h1><p>Equivalent benchmark content.</p>")
    (p/".nift/tracked.json").write_text(json.dumps({"tracked":tracked}))
    (p/"templates/template.html").write_text("<!doctype html><html><head><title>$[title]</title></head><body>@content</body></html>")
    return p,[nift,"build-all"],["public"]

def hugo_fixture(base,n,hugo):
    p=base/"hugo"; (p/"content").mkdir(parents=True); (p/"layouts/_default").mkdir(parents=True)
    (p/"hugo.toml").write_text('disableKinds = ["taxonomy", "term", "RSS", "sitemap", "robotsTXT", "404"]\n')
    (p/"layouts/_default/single.html").write_text("<!doctype html><html><head><title>{{ .Title }}</title></head><body>{{ .Content }}</body></html>")
    for i in range(n):
        url="/" if i==0 else f"/page-{i}.html"
        (p/"content"/f"page-{i}.md").write_text(f'---\ntitle: "Page {i}"\nurl: "{url}"\n---\n<h1>Page {i}</h1><p>Equivalent benchmark content.</p>\n')
    return p,[hugo,"--quiet","--destination","public"],["public","resources"]

def astro_fixture(base,n,project):
    p=base/"astro"; (p/"src/pages").mkdir(parents=True); link_node_modules(p,project)
    (p/"astro.config.mjs").write_text('import { defineConfig } from "astro/config"; export default defineConfig({ output: "static" });\n')
    for i in range(n):
        fn="index.astro" if i==0 else f"page-{i}.astro"
        (p/"src/pages"/fn).write_text(f"<!doctype html><html><head><title>Page {i}</title></head><body><h1>Page {i}</h1><p>Equivalent benchmark content.</p></body></html>")
    astro=Path(project).resolve()/"node_modules/.bin/astro"
    return p,[str(astro),"build","--silent"],["dist",".astro"]


def vitepress_fixture(base,n,project):
    p=base/"vitepress"; docs=p/"docs"; cfg=docs/".vitepress"; cfg.mkdir(parents=True); link_node_modules(p,project)
    (cfg/"config.mjs").write_text('export default { title: "Benchmark", cleanUrls: false, themeConfig: { nav: [], sidebar: [] } };\n')
    for i in range(n):
        fn="index.md" if i==0 else f"page-{i}.md"
        (docs/fn).write_text(f"# Page {i}\n\nEquivalent benchmark content.\n")
    vp=Path(project).resolve()/"node_modules/.bin/vitepress"
    return p,[str(vp),"build","docs"],["docs/.vitepress/dist","docs/.vitepress/cache"]

def clean_outputs(cwd,paths):
    for rel in paths:
        p=cwd/rel
        if p.is_symlink() or p.is_file(): p.unlink(missing_ok=True)
        else: shutil.rmtree(p,ignore_errors=True)

def sample_summary(time_samples,rss_samples):
    return {
        "seconds":time_samples,
        "median_seconds":statistics.median(time_samples),
        "min_seconds":min(time_samples),
        "max_seconds":max(time_samples),
        "peak_rss_mib":rss_samples,
        "median_peak_rss_mib":statistics.median(rss_samples),
        "min_peak_rss_mib":min(rss_samples),
        "max_peak_rss_mib":max(rss_samples),
    }

def force_mtime_change(path,sequence):
    """Make modified-mode tests deterministic even on coarse timestamp filesystems."""
    base=int(time.time()) + 10 + sequence
    os.utime(path, (base,base))

def nift_incremental_benchmark(cwd,nift,warmups,repetitions):
    """Measure Nift's development-loop behavior on the already-built 10k fixture."""
    results={}
    cmd=[nift,"build-updated"]

    def measure_case(name,mutate=None):
        time_samples=[]
        rss_samples=[]
        total=warmups+repetitions
        for i in range(total):
            if mutate is not None:
                mutate(i)
            label=(f"warmup {i+1}/{warmups}" if i < warmups
                   else f"measured run {i-warmups+1}/{repetitions}")
            print(f"[Nift incremental: {name}] {label}", file=sys.stderr, flush=True)
            elapsed,peak_rss_kib=run(cmd,cwd)
            peak_rss_mib=peak_rss_kib/1024.0
            print(
                f"[Nift incremental: {name}] {label} finished in {elapsed:.3f}s; "
                f"peak aggregate RSS {peak_rss_mib:.1f} MiB",
                file=sys.stderr,
                flush=True,
            )
            if i >= warmups:
                time_samples.append(elapsed)
                rss_samples.append(peak_rss_mib)
        results[name]=sample_summary(time_samples,rss_samples)

    # Baseline must be fully up to date before incremental measurements begin.
    print("[Nift incremental] preparing fully built baseline", file=sys.stderr, flush=True)
    elapsed,_=run([nift,"build-all"],cwd)
    print(f"[Nift incremental] baseline ready in {elapsed:.3f}s", file=sys.stderr, flush=True)

    measure_case("no_op")

    leaf=cwd/"content/page-1.html"
    original_leaf=leaf.read_text()
    def mutate_leaf(i):
        leaf.write_text(
            f"<h1>Page 1</h1><p>Equivalent benchmark content.</p>"
            f"<!-- incremental-leaf-{i} -->"
        )
        force_mtime_change(leaf,i)
    measure_case("one_page_changed",mutate_leaf)
    leaf.write_text(original_leaf)
    force_mtime_change(leaf,1000)
    run(cmd,cwd)

    template=cwd/"templates/template.html"
    original_template=template.read_text()
    def mutate_template(i):
        template.write_text(
            original_template + f"<!-- shared-template-change-{i} -->"
        )
        force_mtime_change(template,2000+i)
    measure_case("shared_template_changed",mutate_template)
    template.write_text(original_template)
    force_mtime_change(template,4000)
    run(cmd,cwd)

    return results

def machine_info():
    info={
        "system":platform.system(),"release":platform.release(),"machine":platform.machine(),
        "processor":platform.processor(),"python":platform.python_version(),
    }
    try:
        info["cpu_count"]=os.cpu_count()
        info["node"]=version(["node","--version"])
    except Exception:
        pass
    return info

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--nift",required=True)
    ap.add_argument("--hugo",required=True)
    ap.add_argument("--node-project",required=True,help="Project containing pinned Astro/VitePress node_modules")
    ap.add_argument("--pages",type=int,default=10000)
    ap.add_argument("--repetitions",type=int,default=3)
    ap.add_argument("--warmups",type=int,default=1)
    ap.add_argument("--output",default="evidence/results.json")
    a=ap.parse_args()

    print("[setup] starting benchmark", file=sys.stderr, flush=True)
    nift=str(Path(a.nift).resolve()); hugo=str(Path(a.hugo).resolve()); project=Path(a.node_project).resolve()

    dependencies=[nift,hugo,project/"node_modules/.bin/astro",project/"node_modules/.bin/vitepress"]
    print("[setup] checking dependencies", file=sys.stderr, flush=True)
    for x in dependencies:
        if not Path(x).exists():
            raise SystemExit(f"missing benchmark dependency: {x}")
    print("[setup] dependencies found", file=sys.stderr, flush=True)

    print("[setup] reading tool versions", file=sys.stderr, flush=True)
    tools={
        "Nift":version([nift,"--version"]),
        "Hugo":version([hugo,"version"]),
        "Astro":"Astro "+package_version(project,"astro"),
        "VitePress":"VitePress "+package_version(project,"vitepress"),
    }
    for name,value in tools.items():
        print(f"[setup] {name}: {value}", file=sys.stderr, flush=True)

    results={}
    with tempfile.TemporaryDirectory(prefix="nift-comparative-") as td:
        base=Path(td)
        print(f"[setup] generating {a.pages:,}-page fixtures", file=sys.stderr, flush=True)
        fixtures={}
        print("[fixture] Nift", file=sys.stderr, flush=True)
        fixtures["Nift"]=nift_fixture(base,a.pages,nift)
        print("[fixture] Hugo", file=sys.stderr, flush=True)
        fixtures["Hugo"]=hugo_fixture(base,a.pages,hugo)
        print("[fixture] Astro", file=sys.stderr, flush=True)
        fixtures["Astro"]=astro_fixture(base,a.pages,project)
        print("[fixture] VitePress", file=sys.stderr, flush=True)
        fixtures["VitePress"]=vitepress_fixture(base,a.pages,project)
        print("[setup] fixtures ready; timed runs begin", file=sys.stderr, flush=True)
        for name,(cwd,cmd,outputs) in fixtures.items():
            time_samples=[]
            rss_samples=[]
            total=a.warmups+a.repetitions
            for i in range(total):
                if i < a.warmups:
                    label=f"warmup {i+1}/{a.warmups}"
                else:
                    label=f"measured run {i-a.warmups+1}/{a.repetitions}"
                print(f"[{name}] {label}", file=sys.stderr, flush=True)
                clean_outputs(cwd,outputs)
                elapsed,peak_rss_kib=run(cmd,cwd)
                peak_rss_mib=peak_rss_kib/1024.0
                print(
                    f"[{name}] {label} finished in {elapsed:.3f}s; "
                    f"peak aggregate RSS {peak_rss_mib:.1f} MiB",
                    file=sys.stderr,
                    flush=True,
                )
                if i>=a.warmups:
                    time_samples.append(elapsed)
                    rss_samples.append(peak_rss_mib)
            results[name]=sample_summary(time_samples,rss_samples)

        print("[Nift incremental] starting development-loop measurements", file=sys.stderr, flush=True)
        nift_incremental=nift_incremental_benchmark(
            fixtures["Nift"][0],
            nift,
            a.warmups,
            a.repetitions,
        )

    out={
        "schema":4,
        "workload":"clean production build",
        "pages":a.pages,
        "fixture_note":"Equivalent small pages generated from tool-native source; dependency installation and fixture generation are outside timed runs.",
        "memory_measurement":"Linux peak aggregate RSS across the spawned process group, sampled every 10 ms during each build.",
        "warmups":a.warmups,
        "repetitions":a.repetitions,
        "machine":machine_info(),
        "tools":tools,
        "results":results,
        "nift_incremental": {
            "note": "Nift-only development-loop measurements on the same 10,000-page fixture; not cross-generator comparisons.",
            "command": "nift build-updated",
            "cases": {
                "no_op": "No source or template changed.",
                "one_page_changed": "One independent content page changed before each run.",
                "shared_template_changed": "The common template changed before each run, legitimately invalidating all 10,000 pages."
            },
            "results": nift_incremental,
        },
    }
    dest=Path(a.output); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))

if __name__=="__main__":
    main()
