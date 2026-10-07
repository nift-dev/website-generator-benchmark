#!/usr/bin/env python3
"""Schema-5 correctness-gated build campaign. Historical evidence is untouched."""
import argparse,html,json,re,shutil,tempfile
from pathlib import Path
import benchmark as legacy
from campaign_measure import measure,isolated_env,metadata,identity,summary
ROOT=Path(__file__).resolve().parents[1]


def fixtures(base,n,nift,hugo,project):
    fs={'Nift':legacy.nift_fixture(base,n,nift),'Hugo':legacy.hugo_fixture(base,n,hugo),
        'Astro':legacy.astro_fixture(base,n,project),'VitePress':legacy.vitepress_fixture(base,n,project)}
    fs['Nift']=(fs['Nift'][0],[nift,'build','--all'],fs['Nift'][2])
    p=fs['Nift'][0]/'.nift/config.json'
    c=json.loads(p.read_text()); c['config']['build-threads']=1; p.write_text(json.dumps(c))
    p=fs['Astro'][0]/'astro.config.mjs'
    p.write_text('import { defineConfig } from "astro/config"; export default defineConfig({ output: "static", build: { format: "file" } });\n')
    p=fs['Hugo'][0]
    with (p/'hugo.toml').open('a') as f:
        f.write('\n[markup.goldmark.renderer]\nunsafe = true\n')
    # Disable automatic home: page zero is the regular page explicitly at /.
    s=(p/'hugo.toml').read_text().replace('["taxonomy"','["home", "taxonomy"')
    (p/'hugo.toml').write_text(s)
    p=fs['VitePress'][0]/'docs/.vitepress/theme'; p.mkdir()
    (p/'index.js').write_text('import { h } from "vue"; import { Content } from "vitepress"; export default { Layout: { render() { return h("main", [h(Content)]); } } };\n')
    return fs


def output_root(name,cwd):
    return cwd/({'Nift':'public','Hugo':'public','Astro':'dist','VitePress':'docs/.vitepress/dist'}[name])


def validate(name,cwd,n,leaf_marker=None,template_marker=None):
    out=output_root(name,cwd)
    expected={'index.html'}|{f'page-{i}.html' for i in range(1,n)}
    actual={str(p.relative_to(out)) for p in out.rglob('*.html')}
    if name=='VitePress': expected.add('404.html')
    if actual!=expected: raise RuntimeError(f'{name} routes differ: missing={sorted(expected-actual)[:5]}, extra={sorted(actual-expected)[:5]}')
    for i in range(n):
        p=out/('index.html' if i==0 else f'page-{i}.html'); text=p.read_text()
        title=re.search(r'<title>(.*?)</title>',text,re.S)
        heading=re.search(r'<h1\b[^>]*>(.*?)</h1>',text,re.S)
        strip=lambda v: html.unescape(re.sub(r'<[^>]+>','',v)).strip().replace('\u200b','')
        heading_text=strip(re.sub(r'<a\b[^>]*class="header-anchor"[^>]*>.*?</a>','',heading.group(1),flags=re.S)) if heading else None
        if not title or title.group(1) not in (f'Page {i}',f'Page {i} | Benchmark') or heading_text!=f'Page {i}' or 'Equivalent benchmark content.' not in text:
            raise RuntimeError(f'{name} content oracle failed on page {i}')
        if leaf_marker and i==1 and leaf_marker not in text: raise RuntimeError('incremental leaf stale')
        if template_marker and template_marker not in text: raise RuntimeError('incremental shared template stale')
    return dict(routes=n,content_checked=n)


def snapshot(cwd):
    out=cwd/'public'
    return {str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*.html')}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--nift',required=True); ap.add_argument('--hugo',required=True)
    ap.add_argument('--node-project',required=True); ap.add_argument('--pages',type=int,default=10000)
    ap.add_argument('--samples',type=int,default=5); ap.add_argument('--warmups',type=int,default=1)
    ap.add_argument('--timeout',type=int,default=900); ap.add_argument('--output',required=True)
    a=ap.parse_args()
    if a.samples<5 or a.pages<2: ap.error('minimum five samples and two pages')
    nift=str(Path(a.nift).resolve()); hugo=str(Path(a.hugo).resolve()); project=Path(a.node_project).resolve()
    result=dict(schema=5,publishable=False,machine=metadata(ROOT),pages=a.pages,
        workload='minimal generated HTML page throughput; not a real-site migration',
        notes=['Tool-native sources; VitePress custom minimal theme still hydrates client assets.',
               'One CPU affinity recommended; Nift build threads=1; GOMAXPROCS=1.',
               'Cold means entire fresh fixture; warm-full cleans output and retains internal build state.',
               'VitePress also generates one 404 page; validated and disclosed, excluded from corpus count.',
               'wait4 RSS not aggregate tree RSS; see measurement policy.'],
        tools={'Nift':identity(nift,['--version']),'Hugo':identity(hugo,['version']),
               'Astro':legacy.package_version(project,'astro'),'VitePress':legacy.package_version(project,'vitepress')},
        jobs=[],samples=a.samples,warmups=a.warmups)
    if not result['tools']['Hugo']['version'].startswith('hugo v0.167.0'):
        raise SystemExit('Hugo pin mismatch: require 0.167.0')
    declared=json.loads((project/'package.json').read_text())['dependencies']
    for pkg,label in (('astro','Astro'),('vitepress','VitePress')):
        if result['tools'][label]!=declared[pkg]: raise SystemExit(label+' pin mismatch')
    dest=Path(a.output); dest.parent.mkdir(parents=True,exist_ok=True)
    def save(): dest.write_text(json.dumps(result,indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='website-campaign-') as td:
        base=Path(td); env=isolated_env(base/'home'); env['GOMAXPROCS']='1'; env['CI']='1'
        warm=fixtures(base/'warm',a.pages,nift,hugo,project)
        for mode in ('application-cold','warm-full'):
            jobs={name:dict(id=f'{name}/{mode}',samples=[],command=cmd) for name,(_,cmd,_) in warm.items()}
            result['jobs'].extend(jobs.values())
            for rnd in range(a.warmups+a.samples):
                names=list(jobs); names=names[rnd%4:]+names[:rnd%4]
                for name in names:
                    if mode=='application-cold':
                        cold=base/'cold'; shutil.rmtree(cold,ignore_errors=True)
                        fs=fixtures(cold,a.pages,nift,hugo,project)
                    else: fs=warm
                    cwd,cmd,outputs=fs[name]; legacy.clean_outputs(cwd,outputs)
                    rec,out,err=measure(cmd,cwd,env,a.timeout)
                    rec.update(round=rnd,warmup=rnd<a.warmups,correct=False,command=cmd)
                    jobs[name]['samples'].append(rec); save()
                    if rec['exit_code'] or rec['timeout']: raise RuntimeError(name+' failed: '+err.decode(errors='replace')[-1000:])
                    rec['validation']=validate(name,cwd,a.pages); rec['correct']=True; save()
                    print(name,mode,rnd,round(rec['wall_ms'],2),'ms',flush=True)
            for job in jobs.values(): job['summary']=summary([r for r in job['samples'] if not r['warmup']])
        cwd=warm['Nift'][0]
        baseline,_,_=measure([nift,'build','--all'],cwd,env,a.timeout)
        if baseline['exit_code']: raise RuntimeError('incremental baseline failed')
        for case in ('no-op','one-page','shared-template'):
            job=dict(id='Nift/incremental/'+case,samples=[],command=[nift,'build']); result['jobs'].append(job)
            for rnd in range(a.warmups+a.samples):
                leaf=None; shared=None
                if case=='one-page':
                    leaf=f'leaf-{rnd}'; p=cwd/'content/page-1.html'
                    p.write_text(f'<h1>Page 1</h1><p>Equivalent benchmark content.</p><!--{leaf}-->')
                    legacy.force_mtime_change(p,rnd)
                if case=='shared-template':
                    shared=f'template-{rnd}'; p=cwd/'templates/template.html'
                    p.write_text('<!doctype html><html><head><title>$[title]</title></head><body>@content</body></html><!--'+shared+'-->')
                    legacy.force_mtime_change(p,2000+rnd)
                rec,out,err=measure(job['command'],cwd,env,a.timeout)
                rec.update(round=rnd,warmup=rnd<a.warmups,correct=False)
                job['samples'].append(rec); save()
                if rec['exit_code'] or rec['timeout']: raise RuntimeError('incremental failed')
                validate('Nift',cwd,a.pages,leaf,shared)
                # Validate incremental bytes against a full rebuild, outside timing.
                before=snapshot(cwd); full,_,_=measure([nift,'build','--all'],cwd,env,a.timeout)
                if full['exit_code'] or before!=snapshot(cwd): raise RuntimeError('incremental differs from full rebuild')
                rec['correct']=True; save()
            job['summary']=summary([r for r in job['samples'] if not r['warmup']])
    result['publishable']=True; save()
if __name__=='__main__': main()
