#!/usr/bin/env python3
"""Regenerate one campaign's summaries, refusing any invalid or incomplete run."""
import argparse,json
from pathlib import Path
from campaign_measure import summary

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
 d=json.loads(Path(a.input).read_text())
 if d.get('publishable') is not True or not d.get('jobs'):raise SystemExit('run not publishable')
 out={}
 for job in d['jobs']:
  if any(r.get('correct') is not True for r in job['samples']):raise SystemExit('incorrect sample')
  rows=[r for r in job['samples'] if not r['warmup']]
  expected=d['work_samples'] if job.get('work') else d['samples']
  if len(rows)!=expected:raise SystemExit('incomplete samples '+job['id'])
  value=summary(rows)
  if value!=job['summary']:raise SystemExit('retained summary disagrees with raw data')
  out[job['id']]=value
 Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
