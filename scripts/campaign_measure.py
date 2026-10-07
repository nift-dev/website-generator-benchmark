"""Linux direct-process latency and wait4 high-water RSS, with bounded execution.

RSS is the kernel's waited-child high-water value (maximum, not simultaneous
aggregate tree RSS). Preparation and output validation are outside latency.
"""
import hashlib
import json
import os
import platform
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path


_HELPER = None
_HELPER_DIR = None


def helper():
    global _HELPER, _HELPER_DIR
    if _HELPER is None:
        _HELPER_DIR = tempfile.TemporaryDirectory(prefix='campaign-measure-')
        _HELPER = str(Path(_HELPER_DIR.name)/'measure')
        subprocess.run(['cc','-O2','-Wall','-Wextra',str(Path(__file__).with_name('measure.c')),'-o',_HELPER],check=True)
    return _HELPER


def measure(cmd, cwd, env, timeout=120, stdin=None):
    exe=helper()  # compilation outside all measured regions
    with tempfile.TemporaryDirectory(prefix='sample-') as td, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err, tempfile.TemporaryFile() as inp:
        report=str(Path(td)/'sample.json')
        if stdin is not None:
            inp.write(stdin); inp.seek(0)
        proc=subprocess.Popen([exe,report,*cmd],cwd=cwd,env=env,stdin=inp,
                              stdout=out,stderr=err,start_new_session=True)
        expired=False
        try: proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired=True
            os.killpg(proc.pid,signal.SIGKILL); proc.wait()
        out.seek(0); err.seek(0)
        stdout,stderr=out.read(),err.read()
        if expired:
            rec=dict(wall_ms=None,peak_rss_kib=None,cpu_ms=None,exit_code=proc.returncode)
        else:
            rec=json.loads(Path(report).read_text())
        rec.update(timeout=expired,stdout_sha256=hashlib.sha256(stdout).hexdigest(),
                   stderr_sha256=hashlib.sha256(stderr).hexdigest())
        return rec,stdout,stderr


def isolated_env(home):
    home = Path(home)
    for rel in ('', 'config', 'cache', 'data', 'state'):
        (home/rel).mkdir(parents=True, exist_ok=True)
    return dict(PATH='/usr/local/bin:/usr/bin:/bin', HOME=str(home),
                XDG_CONFIG_HOME=str(home/'config'), XDG_CACHE_HOME=str(home/'cache'),
                XDG_DATA_HOME=str(home/'data'), XDG_STATE_HOME=str(home/'state'),
                ZDOTDIR=str(home), LANG='C.UTF-8', LC_ALL='C.UTF-8', TERM='xterm-256color')


def metadata(root):
    def read(path):
        p=Path(path); return p.read_text() if p.exists() else None
    def git(*args):
        p=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True)
        return p.stdout.strip()
    return dict(kernel=platform.release(), os_release=read('/etc/os-release'),
                cpuinfo=read('/proc/cpuinfo'), meminfo=read('/proc/meminfo'),
                cpu_affinity=sorted(os.sched_getaffinity(0)), python=platform.python_version(),
                revision=git('rev-parse','HEAD'), dirty=bool(git('status','--porcelain')),
                cache_policy='OS caches uncontrolled; no machine-cold claim',
                rss_policy='Linux wait4 waited-child high-water RSS; not aggregate process-tree RSS')


def identity(executable, version_args):
    p=subprocess.run([executable,*version_args],capture_output=True,text=True,timeout=15)
    if p.returncode: raise RuntimeError('version probe failed: '+executable)
    return dict(version=(p.stdout or p.stderr).strip(),
                sha256=hashlib.sha256(Path(executable).read_bytes()).hexdigest())


def summary(rows):
    import statistics
    xs=sorted(r['wall_ms'] for r in rows)
    def pct(p):
        k=(len(xs)-1)*p; lo=int(k); hi=min(lo+1,len(xs)-1)
        return xs[lo]+(xs[hi]-xs[lo])*(k-lo)
    return dict(samples=len(xs), median_ms=statistics.median(xs), min_ms=min(xs),
                max_ms=max(xs), p90_ms=pct(.9), p95_ms=pct(.95), p99_ms=pct(.99),
                median_peak_rss_kib=statistics.median(r['peak_rss_kib'] for r in rows if r['peak_rss_kib'] is not None) if any(r['peak_rss_kib'] is not None for r in rows) else None)
