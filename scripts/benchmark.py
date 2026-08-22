#!/usr/bin/env python3
"""Reproducible Nift/Hugo/Astro/VitePress clean-build benchmark.

Fixture generation and dependency installation are outside the timed region.
Every requested tool must exist and every run must succeed before results are
written. This prevents partial comparisons from being mistaken for evidence.
"""
import argparse, json, os, platform, shutil, statistics, subprocess, sys, tempfile, time
from pathlib import Path

def run(cmd,cwd,env=None):
    t=time.perf_counter()
    p=subprocess.run(cmd,cwd=cwd,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{p.stderr[-2000:]}")
    return time.perf_counter()-t

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
            samples=[]
            total=a.warmups+a.repetitions
            for i in range(total):
                if i < a.warmups:
                    label=f"warmup {i+1}/{a.warmups}"
                else:
                    label=f"measured run {i-a.warmups+1}/{a.repetitions}"
                print(f"[{name}] {label}", file=sys.stderr, flush=True)
                clean_outputs(cwd,outputs)
                elapsed=run(cmd,cwd)
                print(f"[{name}] {label} finished in {elapsed:.3f}s", file=sys.stderr, flush=True)
                if i>=a.warmups: samples.append(elapsed)
            results[name]={
                "seconds":samples,
                "median_seconds":statistics.median(samples),
                "min_seconds":min(samples),
                "max_seconds":max(samples),
            }

    out={
        "schema":2,
        "workload":"clean production build",
        "pages":a.pages,
        "fixture_note":"Equivalent small pages generated from tool-native source; dependency installation and fixture generation are outside timed runs.",
        "warmups":a.warmups,
        "repetitions":a.repetitions,
        "machine":machine_info(),
        "tools":tools,
        "results":results,
    }
    dest=Path(a.output); dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))

if __name__=="__main__":
    main()
