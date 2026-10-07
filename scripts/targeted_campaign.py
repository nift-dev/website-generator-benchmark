#!/usr/bin/env python3
"""Supplemental explicit-target scaling; never pooled with another node's run."""
import argparse,json,tempfile,shutil
from pathlib import Path
import benchmark as legacy
from campaign import validate,snapshot
from campaign_measure import measure,isolated_env,metadata,identity,summary
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--nift',required=True);ap.add_argument('--output',required=True);ap.add_argument('--samples',type=int,default=5);ap.add_argument('--warmups',type=int,default=1);a=ap.parse_args()
 if a.samples<5:ap.error('at least five samples')
 nift=str(Path(a.nift).resolve());dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 result=dict(schema=5,publishable=False,machine=metadata(ROOT),tools={'Nift':identity(nift,['--version'])},samples=a.samples,warmups=a.warmups,jobs=[],notes=['Separate supplemental node; do not pool with original campaign.','Explicit target builds one changed leaf; other pages must remain byte-identical and complete output match full rebuild.','Fresh full reference collected on this node for context; one CPU, one build thread, uncontrolled OS caches.'])
 if not result['tools']['Nift']['version'].startswith('Nift v4.7.2'):raise RuntimeError('Nift pin mismatch')
 def save():dest.write_text(json.dumps(result,indent=2)+'\n')
 with tempfile.TemporaryDirectory(prefix='targeted-campaign-') as td:
  base=Path(td);env=isolated_env(base/'home')
  for pages in (100,1000,10000):
   cwd,_,_=legacy.nift_fixture(base/str(pages),pages,nift);p=cwd/'.nift/config.json';c=json.loads(p.read_text());c['config']['build-threads']=1;p.write_text(json.dumps(c))
   full=[nift,'build','--all'];target=[nift,'build','page-1']
   ref=dict(id=f'Nift/{pages}/fresh-full',pages=pages,command=full,samples=[]);job=dict(id=f'Nift/{pages}/targeted-one-page',pages=pages,command=target,samples=[]);result['jobs'] += [ref,job]
   for rnd in range(a.samples+a.warmups):
    cwd,_,_=legacy.nift_fixture(base/str(pages)/str(rnd),pages,nift);p=cwd/'.nift/config.json';c=json.loads(p.read_text());c['config']['build-threads']=1;p.write_text(json.dumps(c))
    shutil.rmtree(cwd/'public',ignore_errors=True);shutil.rmtree(cwd/'.nift/public',ignore_errors=True)
    rec,out,err=measure(full,cwd,env,120);rec.update(round=rnd,warmup=rnd<a.warmups,correct=False);ref['samples'].append(rec);save()
    if rec['exit_code'] or rec['timeout']:raise RuntimeError('full failed')
    validate('Nift',cwd,pages);rec['correct']=True
    before=snapshot(cwd);marker=f'target-{rnd}';leaf=cwd/'content/page-1.html';leaf.write_text(f'<h1>Page 1</h1><p>Equivalent benchmark content.</p><!--{marker}-->');legacy.force_mtime_change(leaf,rnd)
    rec,out,err=measure(target,cwd,env,120);rec.update(round=rnd,warmup=rnd<a.warmups,correct=False);job['samples'].append(rec);save()
    if rec['exit_code'] or rec['timeout']:raise RuntimeError('target failed')
    validate('Nift',cwd,pages,leaf_marker=marker);after=snapshot(cwd)
    if any(after[k]!=v for k,v in before.items() if k!='page-1.html'):raise RuntimeError('target altered unrelated page')
    fullrec,_,_=measure(full,cwd,env,120)
    if fullrec['exit_code'] or snapshot(cwd)!=after:raise RuntimeError('target output differs from full rebuild')
    rec['correct']=True;save();print(pages,rnd,'target ms',round(rec['wall_ms'],3),flush=True)
   for j in (ref,job):j['summary']=summary([r for r in j['samples'] if not r['warmup']])
 result['publishable']=True;save()
if __name__=='__main__':main()
