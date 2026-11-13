"""Long-script/source-release negatives; no cognitive or investment success claim."""
from pathlib import Path
import json,tempfile,sys,unittest,hashlib,importlib.util
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from research.longitudinal_prepare import make_plan
from research.longitudinal_dialogue import release_fixture_files
from research.longitudinal_audit import source_manifest_for,document_hash_check
class LongFinanceTests(unittest.TestCase):
 def test_long_script_requires_explicit_bounded_optin(self):
  case={'id':'continuous','turns':['research']*30}
  with self.assertRaises(ValueError):make_plan({'cases':[case]})
  self.assertEqual(len(make_plan({'max_turns':30,'cases':[case]})),2)
  for value in [31,1,True,'30']:
   with self.assertRaises(ValueError):make_plan({'max_turns':value,'cases':[case]})
 def test_29_of_30_is_not_complete(self):
  from research.longitudinal_audit import turn_integrity
  self.assertIn('expected_turn_count_mismatch',turn_integrity(['r']*30,[],[],[],{'turns':30}))
 def fixture(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
  out=Path(temp.name);folder=out/'session';(folder/'adapter/sandbox').mkdir(parents=True)
  (out/'future.md').write_text('Version two.\n')
  case={'fixture_releases':[{'at_turn':3,'source':'future.md','target':'hyp/v2.md','metadata':{'kind':'SIM'}}]}
  return out,folder,case
 def test_future_source_not_available_before_its_turn(self):
  out,folder,case=self.fixture()
  release_fixture_files(out,case,folder,2)
  target=folder/'adapter/sandbox/hyp/v2.md'
  self.assertFalse(target.exists())
  release_fixture_files(out,case,folder,3)
  self.assertEqual(target.read_text(),'Version two.\n')
  event=json.loads((folder/'fixture-release-events.jsonl').read_text())
  self.assertEqual(event['kind'],'research_fixture_available_not_execution_observation')
 def test_release_never_overwrites_old_version(self):
  out,folder,case=self.fixture();release_fixture_files(out,case,folder,3)
  target=folder/'adapter/sandbox/hyp/v2.md';old=target.read_bytes()
  (out/'future.md').write_text('Different contents')
  with self.assertRaises(FileExistsError):release_fixture_files(out,case,folder,3)
  self.assertEqual(target.read_bytes(),old)
 def test_release_cannot_escape_sandbox(self):
  out,folder,case=self.fixture();case['fixture_releases'][0]['target']='../../escape.md'
  with self.assertRaises(ValueError):release_fixture_files(out,case,folder,3)
 def test_source_resolves_by_identity_not_by_a_matching_hash_elsewhere(self):
  out,folder,case=self.fixture();release_fixture_files(out,case,folder,3)
  p=folder/'adapter/sandbox/hyp/v2.md';sha=hashlib.sha256(p.read_bytes()).hexdigest()
  manifest={'path':str(folder/'adapter/sandbox/ledger.md'),'sha256':'catalog',
    'released_sources':[{'path':str(p),'sha256':sha,'at_turn':3}]}
  self.assertEqual(source_manifest_for({'resolved_path':str(p)},manifest)['sha256'],sha)
  self.assertIsNone(source_manifest_for({'resolved_path':str(out/'not-source.md'),'source_hash':sha},manifest))
  manifest['released_sources'].append(dict(manifest['released_sources'][0]))
  self.assertIsNone(source_manifest_for({'resolved_path':str(p)},manifest))
if __name__=='__main__':unittest.main()
