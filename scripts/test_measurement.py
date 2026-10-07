import tempfile,sys,unittest,os
from pathlib import Path
from campaign_measure import measure,isolated_env,summary
class Checks(unittest.TestCase):
 def test_correct_exit_output_and_independent_rss(self):
  with tempfile.TemporaryDirectory() as td:
   env=isolated_env(td)
   r,o,e=measure(['/usr/bin/printf','oracle'],td,env)
   self.assertEqual((r['exit_code'],o),(0,b'oracle'))
   r2,o,e=measure(['/usr/bin/false'],td,env)
   self.assertNotEqual(r2['exit_code'],0)
   self.assertLess(r2['peak_rss_kib'],16000)
 def test_timeout(self):
  with tempfile.TemporaryDirectory() as td:
   r,_,_=measure(['/usr/bin/sleep','5'],td,isolated_env(td),timeout=.05)
   self.assertTrue(r['timeout']);self.assertIsNone(r['wall_ms'])
 def test_environment_contamination(self):
  with tempfile.TemporaryDirectory() as td:
   old=dict(os.environ)
   try:
    os.environ.update(BASH_ENV='/hostile',ENV='/hostile',ZDOTDIR='/hostile',LINODE_CLI_TOKEN='dummy',PYTHONPATH='/hostile',NODE_OPTIONS='--bad')
    env=isolated_env(td)
    for key in ('BASH_ENV','ENV','LINODE_CLI_TOKEN','PYTHONPATH','NODE_OPTIONS'):self.assertNotIn(key,env)
    self.assertEqual(env['ZDOTDIR'],td)
    r,o,e=measure(['/usr/bin/bash','--noprofile','--norc','-c','printf clean'],td,env)
    self.assertEqual(o,b'clean');self.assertEqual(r['exit_code'],0)
   finally: os.environ.clear();os.environ.update(old)
if __name__=='__main__':unittest.main()
