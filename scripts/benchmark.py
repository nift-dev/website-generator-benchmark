#!/usr/bin/env python3
"""Reproducible Nift/Hugo/Astro production-build benchmark harness.

The harness deliberately refuses to publish partial comparisons: all requested
competitors must be available, and every run must succeed.
"""
import argparse, json, os, platform, shutil, statistics, subprocess, tempfile, time
from pathlib import Path

def run(cmd,cwd):
    t=time.perf_counter(); p=subprocess.run(cmd,cwd=cwd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    if p.returncode: raise RuntimeError(f"{' '.join(cmd)} failed: {p.stderr[-1000:]}")
    return time.perf_counter()-t

def version(cmd):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    return p.stdout.splitlines()[0].strip() if p.stdout else 'unknown'

def nift_fixture(base,n,nift):
    p=base/'nift'; (p/'.nift').mkdir(parents=True); (p/'content').mkdir(); (p/'templates').mkdir()
    (p/'.nift/config.json').write_text('{"config":{"content-dir":"content/","content-ext":".html","output-dir":"public/","output-ext":".html","default-template":"templates/template.html","build-threads":-1,"incremental-mode":"modified"}}')
    tracked=[]
    for i in range(n):
        name='/' if i==0 else f'page-{i}'
        tracked.append({'name':name,'title':f'Page {i}','template':'templates/template.html'})
        (p/'content'/('index.html' if i==0 else f'page-{i}.html')).write_text(f'<h1>Page {i}</h1><p>Equivalent benchmark content.</p>')
    (p/'.nift/tracked.json').write_text(json.dumps({'tracked':tracked}))
    (p/'templates/template.html').write_text('<!doctype html><html><head><title>$[title]</title></head><body>@content</body></html>')
    return p,[nift,'build-all']

def hugo_fixture(base,n,hugo):
    p=base/'hugo'; (p/'content').mkdir(parents=True); (p/'layouts/_default').mkdir(parents=True)
    (p/'hugo.toml').write_text('disableKinds = ["taxonomy", "term", "RSS", "sitemap", "robotsTXT", "404"]\n')
    (p/'layouts/_default/single.html').write_text('<!doctype html><html><head><title>{{ .Title }}</title></head><body>{{ .Content }}</body></html>')
    for i in range(n):
        (p/'content'/f'page-{i}.md').write_text(f'---\ntitle: "Page {i}"\nurl: "/'+('' if i==0 else f'page-{i}.html')+'"\n---\n<h1>Page '+str(i)+'</h1><p>Equivalent benchmark content.</p>\n')
    return p,[hugo,'--quiet','--destination','public']

def astro_fixture(base,n,astro_project):
    p=base/'astro'; (p/'src/pages').mkdir(parents=True)
    # Reuse a pinned Astro installation supplied by --astro-project; no install occurs in timed runs.
    (p/'astro.config.mjs').write_text('export default { output: "static" };\n')
    for i in range(n):
        fn='index.astro' if i==0 else f'page-{i}.astro'
        (p/'src/pages'/fn).write_text(f'<!doctype html><html><head><title>Page {i}</title></head><body><h1>Page {i}</h1><p>Equivalent benchmark content.</p></body></html>')
    astro=Path(astro_project).resolve()/'node_modules/.bin/astro'
    if not astro.exists(): raise RuntimeError(f'Astro binary not found at {astro}; install the pinned version before benchmarking')
    return p,[str(astro),'build','--silent']

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--nift',required=True); ap.add_argument('--hugo',required=True); ap.add_argument('--astro-project',required=True); ap.add_argument('--pages',type=int,default=10000); ap.add_argument('--repetitions',type=int,default=7); ap.add_argument('--warmups',type=int,default=2); ap.add_argument('--output',default='evidence/results.json'); a=ap.parse_args()
    nift=str(Path(a.nift).resolve()); hugo=str(Path(a.hugo).resolve())
    for x in [nift,hugo]:
        if not Path(x).exists(): raise SystemExit(f'missing benchmark executable: {x}')
    tools={'Nift':version([nift,'--version']),'Hugo':version([hugo,'version']),'Astro':version([str(Path(a.astro_project).resolve()/'node_modules/.bin/astro'),'--version'])}
    results={}
    with tempfile.TemporaryDirectory(prefix='nift-comparative-') as td:
        base=Path(td)
        fixtures={'Nift':nift_fixture(base,a.pages,nift),'Hugo':hugo_fixture(base,a.pages,hugo),'Astro':astro_fixture(base,a.pages,a.astro_project)}
        for name,(cwd,cmd) in fixtures.items():
            samples=[]
            for i in range(a.warmups+a.repetitions):
                shutil.rmtree(cwd/'public',ignore_errors=True); shutil.rmtree(cwd/'dist',ignore_errors=True)
                elapsed=run(cmd,cwd)
                if i>=a.warmups: samples.append(elapsed)
            results[name]={'seconds':samples,'median_seconds':statistics.median(samples),'min_seconds':min(samples),'max_seconds':max(samples)}
    out={'schema':1,'workload':'clean production build','pages':a.pages,'warmups':a.warmups,'repetitions':a.repetitions,'machine':{'system':platform.system(),'release':platform.release(),'machine':platform.machine(),'processor':platform.processor(),'python':platform.python_version()},'tools':tools,'results':results}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
